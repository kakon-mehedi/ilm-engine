import os
import sys
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from ilm_engine.llm.gateway import LLMGateway, get_provider
from ilm_engine.llm.providers.anthropic import AnthropicProvider, ProviderConfigError, strict_schema
from ilm_engine.llm.providers.base import LLMRequest

INPUT = {"block_id": "b000135", "text": "٨ - هند بنت عتيق بن عابد؛ أسلمت وتزوجت"}


class Fact(BaseModel):
    predicate: str
    quote: str


class Facts(BaseModel):
    facts: list[Fact]


class FakeMessages:
    def __init__(self, text, model="claude-sonnet-5-5", stop_reason="end_turn"):
        self.calls = []
        self.text, self.model, self.stop_reason = text, model, stop_reason

    def create(self, **params):
        self.calls.append(params)
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="thinking", thinking=""),
                SimpleNamespace(type="text", text=self.text),
            ],
            model=self.model,
            stop_reason=self.stop_reason,
            stop_details=None,
            usage=SimpleNamespace(input_tokens=120, output_tokens=30),
        )


def fake_client(messages):
    return SimpleNamespace(messages=messages, beta=SimpleNamespace(messages=messages))


def test_mocked_call_returns_validated_object_and_model_id():
    messages = FakeMessages('{"facts": [{"predicate": "converted_to_islam", "quote": "أسلمت"}]}')
    gateway = LLMGateway(AnthropicProvider(client=fake_client(messages)))
    result = gateway.complete_json("entry_facts", "v1", INPUT, Facts)
    assert result.output == Facts(facts=[Fact(predicate="converted_to_islam", quote="أسلمت")])
    assert result.model == "claude-sonnet-5-5" and result.provider == "anthropic"
    assert result.usage == {"input_tokens": 120, "output_tokens": 30}


def test_request_parameters():
    messages = FakeMessages('{"facts": []}')
    provider = AnthropicProvider(client=fake_client(messages))
    LLMGateway(provider).complete_json("entry_facts", "v1", INPUT, Facts, prompt="Extract facts.")
    [params] = messages.calls
    assert params["model"] == "claude-sonnet-5-5" and params["system"] == "Extract facts."
    assert "temperature" not in params and "tool_choice" not in params
    schema = params["output_config"]["format"]["schema"]
    assert params["output_config"]["format"]["type"] == "json_schema"
    assert (
        schema["additionalProperties"] is False and schema["$defs"]["Fact"]["additionalProperties"] is False
    )
    assert params["betas"] == ["server-side-fallback-2026-07-01"] and params["fallbacks"] == "default"
    assert "أسلمت" in params["messages"][0]["content"]


def test_model_id_configurable_and_recorded():
    messages = FakeMessages('{"facts": []}', model="claude-opus-5-5")
    gateway = LLMGateway(AnthropicProvider(client=fake_client(messages)), model="claude-opus-5-5")
    result = gateway.complete_json("judge", "v1", INPUT, Facts)
    assert messages.calls[0]["model"] == "claude-opus-5-5" and result.model == "claude-opus-5-5"


def test_without_fallbacks_uses_plain_messages_api():
    plain, beta = FakeMessages('{"facts": []}'), FakeMessages("unused")
    client = SimpleNamespace(messages=plain, beta=SimpleNamespace(messages=beta))
    LLMGateway(AnthropicProvider(client=client, fallbacks=False)).complete_json("t", "v1", INPUT, Facts)
    assert len(plain.calls) == 1 and beta.calls == [] and "betas" not in plain.calls[0]


def test_repair_turn_carries_previous_output_and_errors():
    provider = AnthropicProvider(client=fake_client(FakeMessages("{}")))
    request = LLMRequest(
        "t", "v1", INPUT, Facts.model_json_schema(), "m", repair_of="{}", repair_errors="facts missing"
    )
    roles = [message["role"] for message in provider.build_params(request)["messages"]]
    assert roles == ["user", "assistant", "user"]


def test_refusal_yields_invalid_output():
    messages = FakeMessages("", stop_reason="refusal")
    result = LLMGateway(AnthropicProvider(client=fake_client(messages))).complete_json(
        "t", "v1", INPUT, Facts
    )
    assert result.output is None and result.schema_valid is False


def test_missing_sdk_gives_clear_error_only_when_used(monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic", None)
    provider = AnthropicProvider()  # selecting it does not fail by itself
    with pytest.raises(ProviderConfigError, match="'llm' extra"):
        provider.complete(LLMRequest("t", "v1", INPUT, {}, "claude-sonnet-5-5"))


def test_missing_credentials_gives_clear_error(monkeypatch):
    class AnthropicError(Exception):
        pass

    def no_credentials():
        raise AnthropicError("no api key")

    fake_sdk = SimpleNamespace(Anthropic=no_credentials, AnthropicError=AnthropicError)
    monkeypatch.setitem(sys.modules, "anthropic", fake_sdk)
    with pytest.raises(ProviderConfigError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider().complete(LLMRequest("t", "v1", INPUT, {}, "claude-sonnet-5-5"))


def test_registered_with_gateway():
    assert get_provider("anthropic", client=fake_client(FakeMessages("{}"))).name == "anthropic"


def test_strict_schema_does_not_mutate_input():
    schema = Facts.model_json_schema()
    strict_schema(schema)
    assert "additionalProperties" not in schema


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="no ANTHROPIC_API_KEY")
def test_live_call():
    result = LLMGateway(AnthropicProvider()).complete_json(
        "entry_facts", "v1", {"text": INPUT["text"], "task": "list stated facts with verbatim quotes"}, Facts
    )
    assert result.schema_valid
