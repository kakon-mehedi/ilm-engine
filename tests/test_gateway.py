import json

import pytest
from pydantic import BaseModel

from ilm_engine.llm.cache import ResponseCache, cache_key, request_key
from ilm_engine.llm.gateway import LLMGateway, get_provider, needs_llm_issue
from ilm_engine.llm.providers.base import LLMRequest, ProviderResponse
from ilm_engine.llm.providers.fixture import FixtureMissingError, FixtureProvider, record_fixture
from ilm_engine.llm.providers.null import NullProvider

INPUT = {"block_id": "b000135", "text": "٨ - هند بنت عتيق بن عابد؛ أسلمت وتزوجت"}


class Gender(BaseModel):
    gender: str
    quote: str


class ScriptedProvider:
    """Answers with the next scripted text and counts calls."""

    name = "scripted"
    default_model = "scripted-model"

    def __init__(self, *texts):
        self.texts = list(texts)
        self.requests: list[LLMRequest] = []

    def complete(self, request):
        self.requests.append(request)
        return ProviderResponse(
            self.texts.pop(0), self.default_model, {"input_tokens": 10, "output_tokens": 5}
        )


def call(gateway):
    return gateway.complete_json("classify_gender", "v1", INPUT, Gender)


def test_null_provider_returns_needs_llm():
    result = call(LLMGateway(NullProvider()))
    assert result.output is None and result.needs_llm is True and result.raw is None
    assert result.provider == "null" and result.schema_valid is False


def test_needs_llm_issue():
    issue = needs_llm_issue("pub_X@r6", "unit", "ku_0123456789ab", "extract_biography", "units")
    assert issue.code == "needs_llm" and issue.target_id == "ku_0123456789ab"
    assert (
        issue.issue_id
        == needs_llm_issue("pub_X@r6", "unit", "ku_0123456789ab", "extract_biography", "units").issue_id
    )


def test_valid_output_and_request_fields():
    provider = ScriptedProvider('{"gender": "f", "quote": "هند بنت عتيق"}')
    result = call(LLMGateway(provider))
    assert result.output == Gender(gender="f", quote="هند بنت عتيق")
    assert result.schema_valid and not result.repaired and not result.cached
    assert result.model == "scripted-model" and result.usage == {"input_tokens": 10, "output_tokens": 5}
    [request] = provider.requests
    assert request.temperature == 0 and request.output_schema["title"] == "Gender"


def test_json_in_code_fence_accepted():
    result = call(LLMGateway(ScriptedProvider('Here:\n```json\n{"gender": "f", "quote": "هند"}\n```')))
    assert result.output.gender == "f"


def test_one_repair_retry():
    provider = ScriptedProvider('{"gender": "f"}', '{"gender": "f", "quote": "هند"}')
    result = call(LLMGateway(provider))
    assert result.output.quote == "هند" and result.repaired is True
    assert (
        provider.requests[1].repair_of == '{"gender": "f"}' and "quote" in provider.requests[1].repair_errors
    )


def test_invalid_after_repair_returns_no_output():
    provider = ScriptedProvider("not json", '{"gender": 1}')
    result = call(LLMGateway(provider))
    assert result.output is None and result.schema_valid is False and result.errors
    assert len(provider.requests) == 2


def test_second_identical_call_is_cached(tmp_path):
    provider = ScriptedProvider('{"gender": "f", "quote": "هند"}')
    gateway = LLMGateway(provider, cache=ResponseCache(tmp_path))
    first, second = call(gateway), call(gateway)
    assert len(provider.requests) == 1
    assert first.cached is False and second.cached is True
    assert second.output == first.output and second.raw == first.raw


def test_cached_repair_replays_without_calls(tmp_path):
    provider = ScriptedProvider('{"gender": "f"}', '{"gender": "f", "quote": "هند"}')
    gateway = LLMGateway(provider, cache=ResponseCache(tmp_path))
    call(gateway)
    again = call(gateway)
    assert len(provider.requests) == 2 and again.cached and again.repaired and again.output.quote == "هند"


def test_null_results_are_not_cached(tmp_path):
    cache = ResponseCache(tmp_path)
    call(LLMGateway(NullProvider(), cache=cache))
    assert list(tmp_path.iterdir()) == []


def test_cache_key_covers_every_part():
    base = cache_key("anthropic", "m", "task", "v1", INPUT)
    assert base == cache_key("anthropic", "m", "task", "v1", dict(reversed(list(INPUT.items()))))
    assert base != cache_key("litellm", "m", "task", "v1", INPUT)
    assert base != cache_key("anthropic", "m2", "task", "v1", INPUT)
    assert base != cache_key("anthropic", "m", "task2", "v1", INPUT)
    assert base != cache_key("anthropic", "m", "task", "v2", INPUT)
    assert base != cache_key("anthropic", "m", "task", "v1", {**INPUT, "text": "x"})


def test_cache_rejects_bad_keys_and_survives_corruption(tmp_path):
    cache = ResponseCache(tmp_path)
    with pytest.raises(ValueError):
        cache.get("../escape")
    key = "ab" * 32
    (tmp_path / f"{key}.json").write_text("{broken", encoding="utf-8")
    assert cache.get(key) is None
    cache.put(key, {"text": "x", "model": "m"})
    assert cache.get(key) == {"text": "x", "model": "m"}


def test_fixture_provider_replays_deterministically(tmp_path):
    request = LLMRequest("classify_gender", "v1", INPUT, Gender.model_json_schema(), "fixture")
    record_fixture(tmp_path, request, '{"gender": "f", "quote": "هند بنت عتيق"}')
    gateway = LLMGateway(FixtureProvider(tmp_path))
    first, second = call(gateway), call(gateway)
    assert first.output == second.output == Gender(gender="f", quote="هند بنت عتيق")
    stored = json.loads(next(tmp_path.iterdir()).read_text(encoding="utf-8"))
    assert stored["task"] == "classify_gender"


def test_fixture_provider_raises_on_missing_fixture(tmp_path):
    with pytest.raises(FixtureMissingError, match="classify_gender"):
        call(LLMGateway(FixtureProvider(tmp_path)))


def test_fixture_name_is_the_request_key(tmp_path):
    request = LLMRequest("classify_gender", "v1", INPUT, {}, "fixture")
    path = record_fixture(tmp_path, request, "{}")
    assert path.name == f"{request_key('fixture', 'classify_gender', 'v1', INPUT)}.json"


def test_get_provider():
    assert get_provider("null").name == "null"
    assert get_provider("fixture").name == "fixture"
    with pytest.raises(ValueError, match="unknown LLM provider"):
        get_provider("nope")
