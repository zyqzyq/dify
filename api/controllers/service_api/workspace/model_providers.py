"""Service API endpoints for resolving user workspaces and reading their model credentials."""

import uuid

from flask import request
from flask_login import current_user
from flask_restx import Resource
from sqlalchemy import select
from werkzeug.exceptions import BadRequest, NotFound, Unauthorized

from controllers.service_api import service_api_ns
from controllers.service_api.wraps import validate_dataset_token
from core.model_runtime.utils.encoders import jsonable_encoder
from extensions.ext_database import db
from models.account import Account, Tenant, TenantAccountJoin
from services.account_service import AccountService
from services.model_provider_service import ModelProviderService


def _resolve_account(*, user_id: str | None, email: str | None) -> Account:
    """Resolve one account by ID or email, defaulting to the authenticated account."""
    if user_id and email:
        raise BadRequest("Only one of user_id or email can be provided.")

    account: Account | None
    if user_id:
        try:
            uuid.UUID(user_id)
        except ValueError as exc:
            raise BadRequest("Invalid user_id format. Expected UUID.") from exc
        account = db.session.scalar(select(Account).where(Account.id == user_id))
    elif email:
        account = AccountService.get_account_by_email_with_case_fallback(email)
    else:
        authenticated_account = current_user._get_current_object()
        if not isinstance(authenticated_account, Account):
            raise Unauthorized("Invalid user.")
        account = authenticated_account

    if account is None:
        raise NotFound("User not found.")
    return account


def _get_account_workspaces(account_id: str) -> list[Tenant]:
    """Return every workspace joined by the account, including archived workspaces."""
    statement = (
        select(Tenant)
        .join(TenantAccountJoin, Tenant.id == TenantAccountJoin.tenant_id)
        .where(TenantAccountJoin.account_id == account_id)
        .order_by(Tenant.created_at.asc())
    )
    return list(db.session.scalars(statement).all())


def _get_workspace(workspace_id: str) -> Tenant | None:
    """Return a workspace by ID."""
    return db.session.scalar(select(Tenant).where(Tenant.id == workspace_id))


@service_api_ns.route("/workspaces")
class UserWorkspacesApi(Resource):
    @service_api_ns.doc("get_user_workspaces")
    @service_api_ns.doc(description="Get workspaces for a user resolved by ID or email")
    @service_api_ns.doc(
        params={
            "user_id": {
                "description": "Target user ID; cannot be combined with email",
                "type": "string",
                "required": False,
                "in": "query",
            },
            "email": {
                "description": "Target user email; cannot be combined with user_id",
                "type": "string",
                "required": False,
                "in": "query",
            },
        },
        responses={
            200: "Workspaces retrieved successfully",
            400: "Invalid or conflicting query parameters",
            401: "Unauthorized - invalid API token",
            404: "User not found",
        },
    )
    @validate_dataset_token
    def get(self, _):
        """Get workspace identifiers and names without loading model credentials."""
        account = _resolve_account(
            user_id=request.args.get("user_id"),
            email=request.args.get("email"),
        )
        workspaces = _get_account_workspaces(account.id)
        data = [
            {
                "id": workspace.id,
                "name": workspace.name,
                "status": workspace.status,
            }
            for workspace in workspaces
        ]
        return jsonable_encoder({"data": data})


@service_api_ns.route("/workspaces/<string:workspace_id>/model-providers/credentials")
class WorkspaceModelProviderCredentialsApi(Resource):
    @service_api_ns.doc("get_workspace_model_provider_credentials")
    @service_api_ns.doc(description="Get model provider credentials for one workspace")
    @service_api_ns.doc(
        params={
            "workspace_id": {
                "description": "Target workspace ID",
                "type": "string",
                "required": True,
                "in": "path",
            },
            "model_name": {
                "description": "Optional exact model name used to filter model-level credentials",
                "type": "string",
                "required": False,
                "in": "query",
            },
            "model_type": {
                "description": "Optional exact model type used to filter model-level credentials",
                "type": "string",
                "required": False,
                "in": "query",
            },
        },
        responses={
            200: "Credentials retrieved successfully",
            401: "Unauthorized - invalid API token",
            404: "Workspace not found",
        },
    )
    @validate_dataset_token
    def get(self, _, workspace_id: str):
        """Get provider credentials and optionally filter model-level credentials."""
        workspace = _get_workspace(workspace_id)
        if workspace is None:
            raise NotFound("Workspace not found.")

        model_name = request.args.get("model_name")
        if model_name is not None:
            model_name = model_name.strip() or None

        model_type = request.args.get("model_type")
        if model_type is not None:
            model_type = model_type.strip() or None

        credentials = ModelProviderService().get_all_credentials(
            tenant_id=workspace.id,
            model_name=model_name,
            model_type=model_type,
        )
        return jsonable_encoder({"data": credentials})
