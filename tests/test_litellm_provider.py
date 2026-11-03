import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from ilm_engine.config import DEFAULT_CONFIG_DIR, ConfigError, load_config, model_family
from ilm_engine.llm.gateway import LLMGateway, get_provider
from ilm_engine.llm.providers.anthropic import ProviderConfigError
from ilm_engine.llm.providers.base import LLMRequest
from ilm_engine.llm.providers.litellm import LiteLLMProvider


class Kind(BaseModel):
    kind: str
    quote: str


def fake_completion(text, model="openai/verifier-x"):
    calls = []

    def completion(**params):
        calls.append(params)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
            model=model,
            usage=SimpleNamespace(prompt_tokens=50, completion_tokens=8),
        )

    return completion, calls


def write_override(tmp_path: Path, body: str) -> Path:
    target = tmp_path / "config"
    shutil.copytree(DEFAULT_CONFIG_DIR, target)
    (target / "books" / "pub_TEST.yaml").write_text(body, encoding="utf-8")
    return target


def test_mocked_call_works():
    completion, calls = fake_completion('{"kind": "full", "quote": "ابنا أبي هالة"}')
    provider = LiteLLMProvider(
        default_model="openai/verifier-x", api_base="http://localhost:8000", completion=completion
    )
    result = LLMGateway(provider).complete_json("judge", "v1", {"text": "ابنا أبي هالة"}, Kind)
    assert result.output == Kind(kind="full", quote="ابنا أبي هالة")
    assert result.model == "openai/verifier-x" and result.usage == {"input_tokens": 50, "output_tokens": 8}
    [params] = calls
    assert params["api_base"] == "http://localhost:8000" and params["temperature"] == 0
    assert params["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
    assert params["messages"][0]["role"] == "system"


def test_repair_turn():
    completion, _ = fake_completion("{}")
    request = LLMRequest(
        "t", "v1", {}, Kind.model_json_schema(), "m", repair_of="{}", repair_errors="kind missing"
    )
    roles = [m["role"] for m in LiteLLMProvider(completion=completion).build_params(request)["messages"]]
    assert roles == ["system", "user", "assistant", "user"]


def test_missing_model_is_a_clear_error():
    completion, _ = fake_completion("{}")
    with pytest.raises(ProviderConfigError, match="needs a model"):
        LiteLLMProvider(completion=completion).complete(LLMRequest("t", "v1", {}, {}, ""))


def test_missing_package_only_errors_when_used(monkeypatch):
    monkeypatch.setitem(sys.modules, "litellm", None)
    provider = LiteLLMProvider(default_model="openai/x")
    with pytest.raises(ProviderConfigError, match="litellm is not installed"):
        provider.complete(LLMRequest("t", "v1", {}, {}, "openai/x"))


def test_registered_with_gateway():
    assert get_provider("litellm").name == "litellm"


@pytest.mark.parametrize(
    "model, family",
    [
        ("claude-sonnet-5-5", "anthropic"),
        ("anthropic/claude-opus-5-5", "anthropic"),
        ("openrouter/anthropic/claude-haiku-5-5", "anthropic"),
        ("openai/gpt-x", "openai"),
        ("gemini/gemini-x-pro", "google"),
        ("hosted_vllm/Qwen/Qwen3-32B", "qwen"),
        ("meta-llama/Llama-x", "meta"),
    ],
)
def test_model_family(model, family):
    assert model_family(model) == family


def test_default_config_has_extractor_and_no_verifier():
    llm = load_config().llm
    assert llm.extractor.provider == "anthropic" and llm.extractor.model == "claude-sonnet-5-5"
    assert llm.verifier is None


def test_verifier_from_different_family_accepted(tmp_path):
    config_dir = write_override(tmp_path, "llm:\n  verifier: {provider: litellm, model: openai/gpt-x}\n")
    assert load_config("pub_TEST", config_dir).llm.verifier.family == "openai"


def test_same_family_for_extractor_and_verifier_fails_validation(tmp_path):
    config_dir = write_override(
        tmp_path, "llm:\n  verifier: {provider: litellm, model: anthropic/claude-opus-5-5}\n"
    )
    with pytest.raises(ConfigError, match="same model family"):
        load_config("pub_TEST", config_dir)
