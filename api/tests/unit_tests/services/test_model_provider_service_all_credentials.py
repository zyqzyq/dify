import types

import pytest

from core.entities.provider_entities import CredentialConfiguration, CustomModelConfiguration
from core.model_runtime.entities.common_entities import I18nObject
from core.model_runtime.entities.model_entities import ModelType
from core.model_runtime.entities.provider_entities import ConfigurateMethod
from models.provider import ProviderType
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
        provider_credential_schema=None,
        model_credential_schema=None,
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

    fake_system_configuration = types.SimpleNamespace(
        enabled=False, current_quota_type=None, quota_configurations=[]
    )

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
        get_provider_credential=_get_provider_credential,
        get_custom_model_credential=_get_custom_model_credential,
    )

    return fake_provider_configuration


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
    assert result[0].provider_credentials[0].credentials == {"api_key": "******abcd"}

    assert len(result[0].model_credentials) == 1
    assert result[0].model_credentials[0].credential_id == "model-cred-1"
    assert result[0].model_credentials[0].credential_name == "Model Key 1"
    assert result[0].model_credentials[0].model == "gpt-4o-mini"
    assert result[0].model_credentials[0].model_type == ModelType.LLM
    assert result[0].model_credentials[0].credentials == {"api_key": "******efgh"}


def test_get_all_credentials_skips_providers_without_custom_config():
    configured = _make_fake_provider_configuration(
        provider_name="openai",
        has_custom_config=True,
        provider_available_credentials=[
            CredentialConfiguration(credential_id="provider-cred-1", credential_name="Provider Key 1")
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

    fake_system_configuration = types.SimpleNamespace(
        enabled=False, current_quota_type=None, quota_configurations=[]
    )

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
    assert len(result[0].provider_credentials) == 1
    assert result[0].provider_credentials[0].credential_id == "provider-cred-1"
    assert len(result[0].model_credentials) == 1
    assert result[0].model_credentials[0].credential_id == "model-cred-1"
