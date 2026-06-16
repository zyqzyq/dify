import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from werkzeug.exceptions import BadRequest, NotFound

from controllers.service_api.workspace.model_providers import (
    UserWorkspacesApi,
    WorkspaceModelProviderCredentialsApi,
    _resolve_account,
)


def unwrap(func):
    while hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    return func


def test_resolve_account_by_user_id():
    user_id = str(uuid.uuid4())
    account = SimpleNamespace(id=user_id)

    with patch(
        "controllers.service_api.workspace.model_providers.db.session.scalar",
        return_value=account,
    ) as scalar:
        result = _resolve_account(user_id=user_id, email=None)

    assert result is account
    scalar.assert_called_once()


def test_resolve_account_by_email():
    account = SimpleNamespace(id="user-1")

    with patch(
        "controllers.service_api.workspace.model_providers.AccountService.get_account_by_email_with_case_fallback",
        return_value=account,
    ) as get_account:
        result = _resolve_account(user_id=None, email="User@Example.com")

    assert result is account
    get_account.assert_called_once_with("User@Example.com")


def test_user_workspaces_rejects_user_id_and_email_together(app):
    api = UserWorkspacesApi()
    method = unwrap(api.get)

    with (
        app.test_request_context("/workspaces?user_id=user-1&email=user@example.com"),
        pytest.raises(BadRequest, match="Only one of user_id or email"),
    ):
        method(api, "authenticated-workspace")


def test_user_workspaces_returns_workspace_details(app):
    api = UserWorkspacesApi()
    method = unwrap(api.get)
    account = SimpleNamespace(id="user-1")
    workspaces = [
        SimpleNamespace(id="workspace-1", name="Workspace One", status="normal"),
        SimpleNamespace(id="workspace-2", name="Workspace Two", status="archive"),
    ]

    with (
        app.test_request_context("/workspaces?email=user@example.com"),
        patch(
            "controllers.service_api.workspace.model_providers._resolve_account",
            return_value=account,
        ) as resolve_account,
        patch(
            "controllers.service_api.workspace.model_providers._get_account_workspaces",
            return_value=workspaces,
        ),
    ):
        result = method(api, "authenticated-workspace")

    resolve_account.assert_called_once_with(user_id=None, email="user@example.com")
    assert result == {
        "data": [
            {"id": "workspace-1", "name": "Workspace One", "status": "normal"},
            {"id": "workspace-2", "name": "Workspace Two", "status": "archive"},
        ]
    }


def test_workspace_credentials_passes_model_name_filter(app):
    api = WorkspaceModelProviderCredentialsApi()
    method = unwrap(api.get)
    workspace = SimpleNamespace(id="workspace-1")

    with (
        app.test_request_context("/workspaces/workspace-1/model-providers/credentials?model_name=gpt-4o-mini"),
        patch(
            "controllers.service_api.workspace.model_providers._get_workspace",
            return_value=workspace,
        ),
        patch(
            "controllers.service_api.workspace.model_providers.ModelProviderService.get_all_credentials",
            return_value=[],
        ) as get_all_credentials,
    ):
        result = method(api, "authenticated-workspace", workspace_id="workspace-1")

    get_all_credentials.assert_called_once_with(
        tenant_id="workspace-1",
        model_name="gpt-4o-mini",
        model_type=None,
    )
    assert result == {"data": []}


def test_workspace_credentials_passes_model_type_filter(app):
    api = WorkspaceModelProviderCredentialsApi()
    method = unwrap(api.get)
    workspace = SimpleNamespace(id="workspace-1")

    with (
        app.test_request_context("/workspaces/workspace-1/model-providers/credentials?model_type=llm"),
        patch(
            "controllers.service_api.workspace.model_providers._get_workspace",
            return_value=workspace,
        ),
        patch(
            "controllers.service_api.workspace.model_providers.ModelProviderService.get_all_credentials",
            return_value=[],
        ) as get_all_credentials,
    ):
        result = method(api, "authenticated-workspace", workspace_id="workspace-1")

    get_all_credentials.assert_called_once_with(
        tenant_id="workspace-1",
        model_name=None,
        model_type="llm",
    )
    assert result == {"data": []}


def test_workspace_credentials_passes_model_name_and_model_type_filters(app):
    api = WorkspaceModelProviderCredentialsApi()
    method = unwrap(api.get)
    workspace = SimpleNamespace(id="workspace-1")

    with (
        app.test_request_context(
            "/workspaces/workspace-1/model-providers/credentials?model_name=gpt-4o-mini&model_type=llm"
        ),
        patch(
            "controllers.service_api.workspace.model_providers._get_workspace",
            return_value=workspace,
        ),
        patch(
            "controllers.service_api.workspace.model_providers.ModelProviderService.get_all_credentials",
            return_value=[],
        ) as get_all_credentials,
    ):
        result = method(api, "authenticated-workspace", workspace_id="workspace-1")

    get_all_credentials.assert_called_once_with(
        tenant_id="workspace-1",
        model_name="gpt-4o-mini",
        model_type="llm",
    )
    assert result == {"data": []}


def test_workspace_credentials_returns_not_found_for_unknown_workspace(app):
    api = WorkspaceModelProviderCredentialsApi()
    method = unwrap(api.get)

    with (
        app.test_request_context("/workspaces/workspace-1/model-providers/credentials"),
        patch(
            "controllers.service_api.workspace.model_providers._get_workspace",
            return_value=None,
        ),
        pytest.raises(NotFound, match="Workspace not found"),
    ):
        method(api, "authenticated-workspace", workspace_id="workspace-1")
