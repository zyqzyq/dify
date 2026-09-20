import logging
import types
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from core.model_runtime.entities.model_entities import ModelType
from services.model_provider_service import ModelProviderService


def _model_credential(
    *,
    credential_id: str,
    provider_name: str = "langgenius/openai_api_compatible/openai_api_compatible",
    model_name: str = "gpt-4o-mini",
    model_type: str = "llm",
    credential_name: str = "Model Key 1",
    encrypted_config: str = '{"api_key": "enc:sk-plain", "endpoint_url": "https://llm.internal/v1"}',
):
    return types.SimpleNamespace(
        id=credential_id,
        tenant_id="tenant-1",
        provider_name=provider_name,
        model_name=model_name,
        model_type=model_type,
        credential_name=credential_name,
        encrypted_config=encrypted_config,
    )


def _patch_credential_query(records: list):
    scalars_result = MagicMock()
    scalars_result.all.return_value = records
    return patch(
        "services.model_provider_service.db.session.scalars",
        return_value=scalars_result,
    )


@contextmanager
def _patch_decrypt():
    with (
        patch.object(
            ModelProviderService,
            "_try_decrypt_credential_value",
            side_effect=lambda value, *_args: value.removeprefix("enc:") if value.startswith("enc:") else value,
        ),
        patch(
            "services.model_provider_service.encrypter.get_decrypt_decoding",
            return_value=(object(), object()),
        ),
    ):
        yield


@pytest.fixture
def service() -> ModelProviderService:
    svc = ModelProviderService()
    svc.provider_manager.get_configurations = MagicMock(side_effect=AssertionError("plugin daemon path must not run"))
    return svc


def test_get_all_credentials_returns_only_model_credentials(service: ModelProviderService):
    records = [
        _model_credential(credential_id="model-cred-1"),
        _model_credential(
            credential_id="model-cred-2",
            provider_name="langgenius/openai/openai",
            model_name="gpt-4o",
            encrypted_config='{"api_key": "enc:sk-openai"}',
        ),
    ]

    with _patch_credential_query(records), _patch_decrypt():
        result = service.get_all_credentials(tenant_id="tenant-1")

    assert [item.provider for item in result] == [
        "langgenius/openai_api_compatible/openai_api_compatible",
        "langgenius/openai/openai",
    ]
    assert result[0].provider_credentials == []
    assert result[1].provider_credentials == []
    assert result[0].label.en_US == "langgenius/openai_api_compatible/openai_api_compatible"
    assert result[0].model_credentials[0].credential_id == "model-cred-1"
    assert result[0].model_credentials[0].model == "gpt-4o-mini"
    assert result[0].model_credentials[0].model_type == ModelType.LLM
    assert result[0].model_credentials[0].credentials == {
        "api_key": "sk-plain",
        "endpoint_url": "https://llm.internal/v1",
    }
    assert result[1].model_credentials[0].credentials == {"api_key": "sk-openai"}


def test_get_all_credentials_does_not_call_get_configurations(service: ModelProviderService):
    with _patch_credential_query([]), _patch_decrypt():
        result = service.get_all_credentials(tenant_id="tenant-1")

    assert result == []
    service.provider_manager.get_configurations.assert_not_called()


def test_get_all_credentials_returns_api_key_key_when_value_is_missing(service: ModelProviderService):
    records = [
        _model_credential(
            credential_id="model-cred-no-api-key",
            encrypted_config='{"endpoint_url": "https://example.com"}',
        )
    ]

    with _patch_credential_query(records), _patch_decrypt():
        result = service.get_all_credentials(tenant_id="tenant-1")

    assert result[0].model_credentials[0].credentials == {
        "api_key": None,
        "endpoint_url": "https://example.com",
    }


def test_get_all_credentials_skips_invalid_model_type(service: ModelProviderService, caplog: pytest.LogCaptureFixture):
    records = [
        _model_credential(credential_id="valid", model_name="gpt-4o-mini"),
        _model_credential(credential_id="invalid", model_name="broken", model_type="not-a-type"),
    ]

    with (
        _patch_credential_query(records),
        _patch_decrypt(),
        caplog.at_level(logging.WARNING, logger="services.model_provider_service"),
    ):
        result = service.get_all_credentials(tenant_id="tenant-1")

    assert [item.credential_id for item in result[0].model_credentials] == ["valid"]
    assert "Skipping model credential with invalid model type" in caplog.text


def test_get_all_credentials_filters_model_credentials_by_model_name(service: ModelProviderService):
    records = [
        _model_credential(credential_id="llm-cred", model_name="gpt-4o-mini"),
        _model_credential(
            credential_id="embedding-cred",
            model_name="text-embedding-3-small",
            model_type="text-embedding",
        ),
    ]

    with _patch_credential_query(records), _patch_decrypt():
        result = service.get_all_credentials(tenant_id="tenant-1", model_name="text-embedding-3-small")

    assert len(result) == 1
    assert [credential.model for credential in result[0].model_credentials] == ["text-embedding-3-small"]


def test_get_all_credentials_filters_model_credentials_by_model_type(service: ModelProviderService):
    records = [
        _model_credential(credential_id="llm-cred", model_name="gpt-4o-mini", model_type="text-generation"),
        _model_credential(
            credential_id="embedding-cred",
            model_name="text-embedding-3-small",
            model_type="embeddings",
        ),
    ]

    with _patch_credential_query(records), _patch_decrypt():
        result = service.get_all_credentials(tenant_id="tenant-1", model_type="llm")

    assert len(result) == 1
    assert [credential.model for credential in result[0].model_credentials] == ["gpt-4o-mini"]
    assert result[0].model_credentials[0].model_type == ModelType.LLM


def test_get_all_credentials_filters_model_credentials_by_model_name_and_model_type(
    service: ModelProviderService,
):
    records = [
        _model_credential(credential_id="llm-cred", model_name="gpt-4o-mini"),
        _model_credential(
            credential_id="embedding-cred",
            model_name="text-embedding-3-small",
            model_type="text-embedding",
        ),
    ]

    with _patch_credential_query(records), _patch_decrypt():
        result = service.get_all_credentials(
            tenant_id="tenant-1",
            model_name="text-embedding-3-small",
            model_type="text-embedding",
        )

    assert len(result) == 1
    assert [credential.model for credential in result[0].model_credentials] == ["text-embedding-3-small"]


def test_get_all_credentials_logs_duration(service: ModelProviderService, caplog: pytest.LogCaptureFixture):
    records = [_model_credential(credential_id="model-cred-1")]

    with (
        _patch_credential_query(records),
        _patch_decrypt(),
        caplog.at_level(logging.INFO, logger="services.model_provider_service"),
    ):
        service.get_all_credentials(tenant_id="tenant-1", model_name="gpt-4o-mini", model_type="llm")

    assert "get_all_credentials" in caplog.text
    assert "tenant_id=tenant-1" in caplog.text
    assert "model_name=gpt-4o-mini" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "query_ms=" in caplog.text
