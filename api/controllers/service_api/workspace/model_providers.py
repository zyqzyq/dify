from flask_login import current_user
from flask_restx import Resource
from werkzeug.exceptions import Unauthorized

from controllers.service_api import service_api_ns
from controllers.service_api.wraps import validate_dataset_token
from core.model_runtime.utils.encoders import jsonable_encoder
from extensions.ext_database import db
from models.account import Account, TenantAccountJoin
from services.model_provider_service import ModelProviderService


@service_api_ns.route("/workspaces/model-providers/credentials")
class UserWorkspacesModelProviderCredentialsApi(Resource):
    @service_api_ns.doc("get_user_workspaces_model_provider_credentials")
    @service_api_ns.doc(description="Get model provider credentials for all workspaces the current user belongs to")
    @service_api_ns.doc(
        responses={
            200: "Credentials retrieved successfully",
            401: "Unauthorized - invalid API token",
        }
    )
    @validate_dataset_token
    def get(self, _):
        account = current_user._get_current_object()
        if not isinstance(account, Account):
            raise Unauthorized("Invalid user.")

        tenant_joins = db.session.query(TenantAccountJoin).where(TenantAccountJoin.account_id == account.id).all()
        tenant_ids = [tj.tenant_id for tj in tenant_joins]

        service = ModelProviderService()
        result = []
        for tenant_id in tenant_ids:
            credentials = service.get_all_credentials(tenant_id=tenant_id)
            result.append(
                {
                    "tenant_id": tenant_id,
                    "credentials": credentials,
                }
            )

        return jsonable_encoder({"data": result})
