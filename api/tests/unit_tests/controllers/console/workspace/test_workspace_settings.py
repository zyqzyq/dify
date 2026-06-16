from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask
from pydantic import ValidationError


@pytest.fixture
def app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def workspace_module(monkeypatch: pytest.MonkeyPatch):
    """Reload workspace controller with lightweight decorators for direct API method tests."""

    from controllers.console import console_ns, wraps
    from libs import login

    def _noop(func):
        return func

    monkeypatch.setattr(login, "login_required", _noop)
    monkeypatch.setattr(wraps, "setup_required", _noop)
    monkeypatch.setattr(wraps, "account_initialization_required", _noop)
    monkeypatch.setattr(wraps, "is_admin_or_owner_required", _noop)

    def _noop_route(*args, **kwargs):  # type: ignore[override]
        def _decorator(cls):
            return cls

        return _decorator

    monkeypatch.setattr(console_ns, "route", _noop_route)
    monkeypatch.setattr(console_ns, "expect", lambda *args, **kwargs: _noop)
    monkeypatch.setattr(console_ns, "schema_model", lambda *args, **kwargs: None)

    module_name = "controllers.console.workspace.workspace"
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def _prepare_tenant(module, monkeypatch: pytest.MonkeyPatch, max_active_requests: int | None = None):
    tenant = SimpleNamespace(
        id="tenant-1",
        name="Old Workspace",
        plan="basic",
        status="normal",
        custom_config=None,
        created_at=None,
        max_active_requests=max_active_requests,
    )
    monkeypatch.setattr(module, "current_account_with_tenant", lambda: (SimpleNamespace(), tenant.id))
    monkeypatch.setattr(module.db, "get_or_404", lambda model, tenant_id: tenant)
    commit = MagicMock()
    monkeypatch.setattr(module.db.session, "commit", commit)
    monkeypatch.setattr(
        module.WorkspaceService,
        "get_tenant_info",
        lambda tenant_model: {
            "id": tenant_model.id,
            "name": tenant_model.name,
            "plan": tenant_model.plan,
            "status": tenant_model.status,
            "created_at": tenant_model.created_at,
            "role": "owner",
            "max_active_requests": tenant_model.max_active_requests or 0,
        },
    )
    return tenant


def test_workspace_settings_updates_name_and_max_active_requests(
    app: Flask, workspace_module, monkeypatch: pytest.MonkeyPatch
):
    tenant = _prepare_tenant(workspace_module, monkeypatch)

    with app.test_request_context(
        "/workspaces/current/settings",
        method="POST",
        json={"name": "New Workspace", "max_active_requests": 12},
    ):
        response = workspace_module.WorkspaceSettingsApi().post()

    assert response["result"] == "success"
    assert response["tenant"]["max_active_requests"] == 12
    assert tenant.name == "New Workspace"
    assert tenant.max_active_requests == 12
    workspace_module.db.session.commit.assert_called_once()


def test_workspace_info_keeps_legacy_behavior(app: Flask, workspace_module, monkeypatch: pytest.MonkeyPatch):
    tenant = _prepare_tenant(workspace_module, monkeypatch, max_active_requests=7)

    with app.test_request_context(
        "/workspaces/info",
        method="POST",
        json={"name": "Renamed Workspace", "max_active_requests": 99},
    ):
        response = workspace_module.WorkspaceInfoApi().post()

    assert response["result"] == "success"
    assert tenant.name == "Renamed Workspace"
    assert tenant.max_active_requests == 7
    workspace_module.db.session.commit.assert_called_once()


def test_workspace_settings_rejects_negative_max_active_requests(workspace_module):
    with pytest.raises(ValidationError):
        workspace_module.WorkspaceSettingsPayload.model_validate(
            {"name": "New Workspace", "max_active_requests": -1}
        )
