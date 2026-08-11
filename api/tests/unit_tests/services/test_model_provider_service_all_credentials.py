import types
from unittest.mock import MagicMock, patch

import pytest

from core.entities.provider_entities import CredentialConfiguration, CustomModelConfiguration
from core.model_runtime.entities.common_entities import I18nObject
from core.model_runtime.entities.model_entities import ModelType
from core.model_runtime.entities.provider_entities import (
    ConfigurateMethod,
    CredentialFormSchema,
    FormType,
    ProviderCredentialSchema,
)
from models.provider import ProviderCredential, ProviderModelCredential, ProviderType
from services.model_provider_service import ModelProviderService


class _FakeConfigurations:
    def __init__(self, *provider_configurations: types.SimpleNamespace) -> None:
        self._provider_configurations = list(provider_configurations)

    def values(self) -> list[types.SimpleNamespace]:
        return self._provider_configurations


def _make_fake_provider_configuration(
    provider_name: str = "langgenius/openai_api_compatible/openai_api_compatible",
    has_custom_config: bool = True,
    provider_available_credentials: list[CredentialConfiguration] | None = None,
    model_available_credentials: list[CredentialConfiguration] | None = None,
    provider_credential_form_schemas: list[CredentialFormSchema] | None = None,
    model_credential_form_schemas: list[CredentialFormSchema] | None = None,
    provider_credentials: dict | None = None,
    model_credentials: dict | None = None,
):
    fake_provider = types.SimpleNamespace(
        provider=provider_name,
        label=I18nObject(en_US="OpenAI API Compatible", zh_Hans="OpenAI API Compatible"),
        description=None,
        icon_small=None,
        icon_small_dark=None,
        background=None,
        help=None,
        supported_model_types=[ModelType.LLM],
        configurate_methods=[ConfigurateMethod.CUSTOMIZABLE_MODEL],
        provider_credential_schema=ProviderCredentialSchema(credential_form_schemas=provider_credential_form_schemas)
        if provider_credential_form_schemas is not None
        else None,
        model_credential_schema=types.SimpleNamespace(credential_form_schemas=model_credential_form_schemas)
        if model_credential_form_schemas is not None
        else None,
    )

    custom_model = CustomModelConfiguration(
        model="gpt-4o-mini",
        model_type=ModelType.LLM,
        credentials={"api_key": "sk-plain-text"},
        current_credential_id="model-cred-1",
        current_credential_name="Model Key 1",
        available_model_credentials=model_available_credentials or [],
        unadded_to_model_list=False,
    )

    fake_custom_provider = types.SimpleNamespace(
        current_credential_id="provider-cred-1",
        current_credential_name="Provider Key 1",
        available_credentials=provider_available_credentials or [],
    )

    fake_custom_configuration = types.SimpleNamespace(
        provider=fake_custom_provider,
        models=[custom_model],
        can_added_models=[],
    )

    fake_system_configuration = types.SimpleNamespace(enabled=False, current_quota_type=None, quota_configurations=[])

    def _get_provider_credential(credential_id: str | None = None):
        if credential_id == "provider-cred-1":
            return provider_credentials or {"api_key": "******abcd"}
        raise ValueError("Credential not found")

    def _get_custom_model_credential(model_type, model, credential_id):
        if credential_id == "model-cred-1":
            return {
                "current_credential_id": "model-cred-1",
                "current_credential_name": "Model Key 1",
                "credentials": model_credentials or {"api_key": "******efgh"},
            }
        raise ValueError("Credential not found")

    fake_provider_configuration = types.SimpleNamespace(
        provider=fake_provider,
        preferred_provider_type=ProviderType.CUSTOM,
        custom_configuration=fake_custom_configuration,
        system_configuration=fake_system_configuration,
        is_custom_configuration_available=lambda: has_custom_config,
        extract_secret_variables=lambda schemas: [
            schema.variable for schema in schemas if schema.type == FormType.SECRET_INPUT
        ],
        get_provider_credential=_get_provider_credential,
        get_custom_model_credential=_get_custom_model_credential,
    )

    return fake_provider_configuration


@pytest.fixture(autouse=True)
def mock_credential_queries():
    records = {
        "provider-cred-1": types.SimpleNamespace(
            id="provider-cred-1",
            tenant_id="tenant-1",
            provider_name="openai",
            credential_name="Provider Key 1",
            encrypted_config='{"api_key": "encrypted-provider-key"}',
        ),
        "model-cred-1": types.SimpleNamespace(encrypted_config='{"api_key": "******efgh"}'),
        "model-cred-2": types.SimpleNamespace(encrypted_config='{"api_key": "******ijkl"}'),
        "model-cred-no-api-key": types.SimpleNamespace(encrypted_config='{"base_url": "https://example.com"}'),
    }

    def execute(statement):
        selected_entity = statement.column_descriptions[0].get("entity")
        if selected_entity is ProviderCredential:
            params = statement.compile().params
            provider_names = next((value for value in params.values() if isinstance(value, list)), [])
            result = MagicMock()
            result.scalars.return_value.all.return_value = [
                record for record in records.values() if getattr(record, "provider_name", None) in provider_names
            ]
            return result

        credential_id = next(
            (value for value in statement.compile().params.values() if isinstance(value, str) and value in records),
            None,
        )
        result = MagicMock()
        result.scalar_one_or_none.return_value = records.get(credential_id)
        return result

    with patch("services.model_provider_service.db.session.execute", side_effect=execute):
        yield


@pytest.fixture
def service_with_all_credentials():
    provider_config = _make_fake_provider_configuration(
        provider_name="openai",
        provider_available_credentials=[
            CredentialConfiguration(credential_id="provider-cred-1", credential_name="Provider Key 1")
        ],
        model_available_credentials=[
            CredentialConfiguration(credential_id="model-cred-1", credential_name="Model Key 1")
        ],
    )

    class _FakeProviderManager:
        def get_configurations(self, tenant_id: str) -> _FakeConfigurations:
            return _FakeConfigurations(provider_config)

    svc = ModelProviderService()
    svc.provider_manager = _FakeProviderManager()
    return svc


def test_get_all_credentials_returns_provider_and_model_credentials(
    service_with_all_credentials: ModelProviderService,
):
    result = service_with_all_credentials.get_all_credentials(tenant_id="tenant-1")

    assert len(result) == 1
    assert result[0].provider == "openai"
    assert len(result[0].provider_credentials) == 1
    assert result[0].provider_credentials[0].credential_id == "provider-cred-1"
    assert result[0].provider_credentials[0].credential_name == "Provider Key 1"
    assert result[0].provider_credentials[0].credentials == {"api_key": "encrypted-provider-key"}

    assert len(result[0].model_credentials) == 1
    assert result[0].model_credentials[0].credential_id == "model-cred-1"
    assert result[0].model_credentials[0].credential_name == "Model Key 1"
    assert result[0].model_credentials[0].model == "gpt-4o-mini"
    assert result[0].model_credentials[0].model_type == ModelType.LLM
    assert result[0].model_credentials[0].credentials == {"api_key": "******efgh"}


def test_get_all_credentials_decrypts_enterprise_provider_api_key_without_active_custom_configuration():
    provider_config = _make_fake_provider_configuration(
        provider_name="openai",
        has_custom_config=False,
        provider_credential_form_schemas=[
            CredentialFormSchema(
                variable="api_key",
                label=I18nObject(en_US="API Key"),
                type=FormType.SECRET_INPUT,
            )
        ],
    )

    class _FakeProviderManager:
        def get_configurations(self, tenant_id: str) -> _FakeConfigurations:
            return _FakeConfigurations(provider_config)

    service = ModelProviderService()
    service.provider_manager = _FakeProviderManager()

    with patch(
        "services.model_provider_service.encrypter.decrypt_token",
        return_value="sk-enterprise-plain-text",
    ) as decrypt_token:
        result = service.get_all_credentials(tenant_id="tenant-1")

    assert len(result) == 1
    assert result[0].provider == "openai"
    assert result[0].provider_credentials[0].credentials == {"api_key": "sk-enterprise-plain-text"}
    assert result[0].model_credentials == []
    decrypt_token.assert_called_once_with(tenant_id="tenant-1", token="encrypted-provider-key")


def test_get_all_credentials_returns_enterprise_model_credential_not_present_in_local_configuration():
    provider_name = "langgenius/openai_api_compatible/openai_api_compatible"
    provider_config = _make_fake_provider_configuration(
        provider_name=provider_name,
        has_custom_config=False,
        model_available_credentials=[],
        model_credential_form_schemas=[
            CredentialFormSchema(
                variable="api_key",
                label=I18nObject(en_US="API Key"),
                type=FormType.SECRET_INPUT,
            )
        ],
    )
    enterprise_model_credential = types.SimpleNamespace(
        id="enterprise-model-cred-1",
        tenant_id="tenant-1",
        provider_name=provider_name,
        model_name="internal-chat-model",
        model_type="llm",
        credential_name="Enterprise Internal Model",
        encrypted_config='{"api_key": "encrypted-enterprise-model-key", "endpoint_url": "https://llm.internal/v1"}',
    )

    class _FakeProviderManager:
        def get_configurations(self, tenant_id: str) -> _FakeConfigurations:
            return _FakeConfigurations(provider_config)

    def execute(statement):
        selected_entity = statement.column_descriptions[0].get("entity")
        result = MagicMock()
        if selected_entity is ProviderCredential:
            result.scalars.return_value.all.return_value = []
        elif selected_entity is ProviderModelCredential:
            result.scalars.return_value.all.return_value = [enterprise_model_credential]
        return result

    service = ModelProviderService()
    service.provider_manager = _FakeProviderManager()

    with (
        patch("services.model_provider_service.db.session.execute", side_effect=execute),
        patch(
            "services.model_provider_service.encrypter.decrypt_token",
            return_value="sk-enterprise-model-plain-text",
        ) as decrypt_token,
    ):
        result = service.get_all_credentials(tenant_id="tenant-1")

    assert len(result) == 1
    assert result[0].provider == provider_name
    assert result[0].provider_credentials == []
    assert len(result[0].model_credentials) == 1
    model_credential = result[0].model_credentials[0]
    assert model_credential.model == "internal-chat-model"
    assert model_credential.model_type == ModelType.LLM
    assert model_credential.credential_id == "enterprise-model-cred-1"
    assert model_credential.credential_name == "Enterprise Internal Model"
    assert model_credential.credentials == {
        "api_key": "sk-enterprise-model-plain-text",
        "endpoint_url": "https://llm.internal/v1",
    }
    decrypt_token.assert_called_once_with(
        tenant_id="tenant-1",
        token="encrypted-enterprise-model-key",
    )


def test_get_all_credentials_matches_credential_provider_name_aliases():
    provider_config = _make_fake_provider_configuration(
        provider_name="langgenius/openai/openai",
        provider_available_credentials=[
            CredentialConfiguration(credential_id="provider-cred-1", credential_name="Provider Key 1")
        ],
        model_available_credentials=[
            CredentialConfiguration(credential_id="model-cred-1", credential_name="Model Key 1")
        ],
    )

    class _FakeProviderManager:
        def get_configurations(self, tenant_id: str) -> _FakeConfigurations:
            return _FakeConfigurations(provider_config)

    def execute(statement):
        params = statement.compile().params
        provider_name_params = [value for key, value in params.items() if "provider_name" in key]
        assert ["langgenius/openai/openai", "openai"] in provider_name_params

        result = MagicMock()
        if "model-cred-1" in params.values():
            result.scalar_one_or_none.return_value = types.SimpleNamespace(encrypted_config='{"api_key": "sk-model"}')
        else:
            result.scalar_one_or_none.return_value = None
        return result

    service = ModelProviderService()
    service.provider_manager = _FakeProviderManager()

    with patch("services.model_provider_service.db.session.execute", side_effect=execute):
        result = service.get_all_credentials(tenant_id="tenant-1")

    assert result[0].model_credentials[0].credentials == {"api_key": "sk-model"}


def test_get_all_credentials_returns_api_key_key_when_model_credential_value_is_missing():
    provider_config = _make_fake_provider_configuration(
        provider_name="openai",
        model_available_credentials=[
            CredentialConfiguration(credential_id="model-cred-no-api-key", credential_name="Model Key 1")
        ],
        model_credential_form_schemas=[
            CredentialFormSchema(
                variable="api_key",
                label=I18nObject(en_US="API Key"),
                type=FormType.SECRET_INPUT,
            )
        ],
    )

    class _FakeProviderManager:
        def get_configurations(self, tenant_id: str) -> _FakeConfigurations:
            return _FakeConfigurations(provider_config)

    service = ModelProviderService()
    service.provider_manager = _FakeProviderManager()

    result = service.get_all_credentials(tenant_id="tenant-1")

    assert result[0].model_credentials[0].credentials == {
        "api_key": None,
        "base_url": "https://example.com",
    }


def test_get_all_credentials_skips_providers_without_custom_config():
    configured = _make_fake_provider_configuration(
        provider_name="openai",
        has_custom_config=True,
        provider_available_credentials=[
            CredentialConfiguration(credential_id="provider-cred-1", credential_name="Provider Key 1")
        ],
        model_available_credentials=[
            CredentialConfiguration(credential_id="model-cred-1", credential_name="Model Key 1")
        ],
    )
    unconfigured = _make_fake_provider_configuration(
        provider_name="azure",
        has_custom_config=False,
        provider_available_credentials=[
            CredentialConfiguration(credential_id="provider-cred-2", credential_name="Provider Key 2")
        ],
    )

    class _FakeProviderManager:
        def get_configurations(self, tenant_id: str) -> _FakeConfigurations:
            return _FakeConfigurations(configured, unconfigured)

    svc = ModelProviderService()
    svc.provider_manager = _FakeProviderManager()

    result = svc.get_all_credentials(tenant_id="tenant-1")

    assert len(result) == 1
    assert result[0].provider == "openai"


def test_get_all_credentials_skips_missing_credentials_gracefully():
    fake_provider = types.SimpleNamespace(
        provider="openai",
        label=I18nObject(en_US="OpenAI", zh_Hans="OpenAI"),
        description=None,
        icon_small=None,
        icon_small_dark=None,
        background=None,
        help=None,
        supported_model_types=[ModelType.LLM],
        configurate_methods=[ConfigurateMethod.CUSTOMIZABLE_MODEL],
        provider_credential_schema=None,
        model_credential_schema=None,
    )

    custom_model = CustomModelConfiguration(
        model="gpt-4o-mini",
        model_type=ModelType.LLM,
        credentials={"api_key": "sk-plain-text"},
        current_credential_id="model-cred-1",
        current_credential_name="Model Key 1",
        available_model_credentials=[
            CredentialConfiguration(credential_id="model-cred-1", credential_name="Model Key 1"),
            CredentialConfiguration(credential_id="model-cred-missing", credential_name="Missing Key"),
        ],
        unadded_to_model_list=False,
    )

    fake_custom_provider = types.SimpleNamespace(
        current_credential_id="provider-cred-1",
        current_credential_name="Provider Key 1",
        available_credentials=[
            CredentialConfiguration(credential_id="provider-cred-1", credential_name="Provider Key 1"),
            CredentialConfiguration(credential_id="provider-cred-missing", credential_name="Missing Key"),
        ],
    )

    fake_custom_configuration = types.SimpleNamespace(
        provider=fake_custom_provider,
        models=[custom_model],
        can_added_models=[],
    )

    fake_system_configuration = types.SimpleNamespace(enabled=False, current_quota_type=None, quota_configurations=[])

    def _get_provider_credential(credential_id: str | None = None):
        if credential_id == "provider-cred-1":
            return {"api_key": "******abcd"}
        raise ValueError("Credential not found")

    def _get_custom_model_credential(model_type, model, credential_id):
        if credential_id == "model-cred-1":
            return {
                "current_credential_id": "model-cred-1",
                "current_credential_name": "Model Key 1",
                "credentials": {"api_key": "******efgh"},
            }
        raise ValueError("Credential not found")

    fake_provider_configuration = types.SimpleNamespace(
        provider=fake_provider,
        preferred_provider_type=ProviderType.CUSTOM,
        custom_configuration=fake_custom_configuration,
        system_configuration=fake_system_configuration,
        is_custom_configuration_available=lambda: True,
        extract_secret_variables=lambda _: [],
        get_provider_credential=_get_provider_credential,
        get_custom_model_credential=_get_custom_model_credential,
    )

    class _FakeProviderManager:
        def get_configurations(self, tenant_id: str) -> _FakeConfigurations:
            return _FakeConfigurations(fake_provider_configuration)

    svc = ModelProviderService()
    svc.provider_manager = _FakeProviderManager()

    result = svc.get_all_credentials(tenant_id="tenant-1")

    assert len(result) == 1
    assert len(result[0].model_credentials) == 1
    assert result[0].model_credentials[0].credential_id == "model-cred-1"


def test_get_all_credentials_filters_model_credentials_by_model_name():
    provider_config = _make_fake_provider_configuration(
        provider_name="openai",
        provider_available_credentials=[
            CredentialConfiguration(credential_id="provider-cred-1", credential_name="Provider Key 1")
        ],
        model_available_credentials=[
            CredentialConfiguration(credential_id="model-cred-1", credential_name="Model Key 1")
        ],
    )
    provider_config.custom_configuration.models.append(
        CustomModelConfiguration(
            model="text-embedding-3-small",
            model_type=ModelType.TEXT_EMBEDDING,
            credentials={"api_key": "sk-plain-text"},
            current_credential_id="model-cred-2",
            current_credential_name="Model Key 2",
            available_model_credentials=[
                CredentialConfiguration(credential_id="model-cred-2", credential_name="Model Key 2")
            ],
            unadded_to_model_list=False,
        )
    )

    class _FakeProviderManager:
        def get_configurations(self, tenant_id: str) -> _FakeConfigurations:
            return _FakeConfigurations(provider_config)

    service = ModelProviderService()
    service.provider_manager = _FakeProviderManager()

    result = service.get_all_credentials(tenant_id="tenant-1", model_name="text-embedding-3-small")

    assert len(result) == 1
    assert [credential.model for credential in result[0].model_credentials] == ["text-embedding-3-small"]


def test_get_all_credentials_filters_model_credentials_by_model_type():
    provider_config = _make_fake_provider_configuration(
        provider_name="openai",
        provider_available_credentials=[
            CredentialConfiguration(credential_id="provider-cred-1", credential_name="Provider Key 1")
        ],
        model_available_credentials=[
            CredentialConfiguration(credential_id="model-cred-1", credential_name="Model Key 1")
        ],
    )
    provider_config.custom_configuration.models.append(
        CustomModelConfiguration(
            model="text-embedding-3-small",
            model_type=ModelType.TEXT_EMBEDDING,
            credentials={"api_key": "sk-plain-text"},
            current_credential_id="model-cred-2",
            current_credential_name="Model Key 2",
            available_model_credentials=[
                CredentialConfiguration(credential_id="model-cred-2", credential_name="Model Key 2")
            ],
            unadded_to_model_list=False,
        )
    )

    class _FakeProviderManager:
        def get_configurations(self, tenant_id: str) -> _FakeConfigurations:
            return _FakeConfigurations(provider_config)

    service = ModelProviderService()
    service.provider_manager = _FakeProviderManager()

    result = service.get_all_credentials(tenant_id="tenant-1", model_type="text-embedding")

    assert len(result) == 1
    assert [credential.model for credential in result[0].model_credentials] == ["text-embedding-3-small"]


def test_get_all_credentials_filters_model_credentials_by_model_name_and_model_type():
    provider_config = _make_fake_provider_configuration(
        provider_name="openai",
        provider_available_credentials=[
            CredentialConfiguration(credential_id="provider-cred-1", credential_name="Provider Key 1")
        ],
        model_available_credentials=[
            CredentialConfiguration(credential_id="model-cred-1", credential_name="Model Key 1")
        ],
    )
    provider_config.custom_configuration.models.append(
        CustomModelConfiguration(
            model="text-embedding-3-small",
            model_type=ModelType.TEXT_EMBEDDING,
            credentials={"api_key": "sk-plain-text"},
            current_credential_id="model-cred-2",
            current_credential_name="Model Key 2",
            available_model_credentials=[
                CredentialConfiguration(credential_id="model-cred-2", credential_name="Model Key 2")
            ],
            unadded_to_model_list=False,
        )
    )

    class _FakeProviderManager:
        def get_configurations(self, tenant_id: str) -> _FakeConfigurations:
            return _FakeConfigurations(provider_config)

    service = ModelProviderService()
    service.provider_manager = _FakeProviderManager()

    result = service.get_all_credentials(
        tenant_id="tenant-1", model_name="text-embedding-3-small", model_type="text-embedding"
    )

    assert len(result) == 1
    assert [credential.model for credential in result[0].model_credentials] == ["text-embedding-3-small"]
