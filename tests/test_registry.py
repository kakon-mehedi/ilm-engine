import copy
import json
from pathlib import Path

import pytest

from ilm_engine.adapters.base import SourceAdapter
from ilm_engine.adapters.registry import (
    AdapterRegistry,
    AmbiguousAdapterError,
    DuplicateAdapterError,
    UnknownSchemaError,
    declared_key,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "demo_book_daraqutni.json"


class FakeAdapter:
    def __init__(self, adapter_id, source_code, versions, detects=False):
        self.adapter_id = adapter_id
        self.source_code = source_code
        self.schema_versions = frozenset(versions)
        self.adapter_version = "1.0.0"
        self._detects = detects

    def detect(self, raw):
        return self._detects

    def to_canonical(self, raw, pdf_path=None):
        raise NotImplementedError


@pytest.fixture(scope="module")
def sample():
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_fake_adapter_satisfies_protocol():
    assert isinstance(FakeAdapter("x", "src-x", {"1.0"}), SourceAdapter)


def test_declared_key_of_sample(sample):
    assert declared_key(sample) == ("src-shamela", "3.0")


def test_resolve_by_declared_key(sample):
    registry = AdapterRegistry()
    shamela = registry.register(FakeAdapter("shamela_v3", "src-shamela", {"3.0"}))
    registry.register(FakeAdapter("other", "src-ocr-team", {"1.0"}, detects=True))
    assert registry.resolve(sample) is shamela


def test_unknown_schema_version_fails_closed(sample):
    registry = AdapterRegistry()
    registry.register(FakeAdapter("shamela_v3", "src-shamela", {"3.0"}))
    raw = copy.deepcopy(sample)
    raw["metadata"]["af_schema"] = "9.9"
    with pytest.raises(UnknownSchemaError) as caught:
        registry.resolve(raw)
    issue = caught.value.issue
    assert issue.code == "unknown_schema_version" and issue.severity == "error"
    assert issue.target_id == "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
    assert issue.details["schema_version"] == "9.9" and issue.details["known"] == ["src-shamela@3.0"]
    assert issue.issue_id.startswith("iss_")


def test_unknown_source_code_fails_closed(sample):
    registry = AdapterRegistry()
    registry.register(FakeAdapter("shamela_v3", "src-shamela", {"3.0"}))
    raw = copy.deepcopy(sample)
    raw["pub"]["source_code"] = "src-new-archive"
    with pytest.raises(UnknownSchemaError):
        registry.resolve(raw)


def test_declared_key_is_not_overridden_by_detect(sample):
    registry = AdapterRegistry()
    registry.register(FakeAdapter("greedy", "src-other", {"1.0"}, detects=True))
    with pytest.raises(UnknownSchemaError):
        registry.resolve(sample)


def test_undeclared_input_uses_detect():
    registry = AdapterRegistry()
    registry.register(FakeAdapter("a", "src-a", {"1.0"}))
    b = registry.register(FakeAdapter("b", "src-b", {"1.0"}, detects=True))
    assert registry.resolve({"pages": []}) is b


def test_undeclared_input_matching_two_adapters_is_ambiguous():
    registry = AdapterRegistry()
    registry.register(FakeAdapter("a", "src-a", {"1.0"}, detects=True))
    registry.register(FakeAdapter("b", "src-b", {"1.0"}, detects=True))
    with pytest.raises(AmbiguousAdapterError, match="a, b"):
        registry.resolve({"pages": []})


def test_undeclared_input_without_match_fails_closed():
    registry = AdapterRegistry()
    registry.register(FakeAdapter("a", "src-a", {"1.0"}))
    with pytest.raises(UnknownSchemaError) as caught:
        registry.resolve({})
    assert caught.value.issue.target_id == "unknown"


def test_registering_same_key_twice_raises():
    registry = AdapterRegistry()
    registry.register(FakeAdapter("a", "src-shamela", {"3.0"}))
    with pytest.raises(DuplicateAdapterError, match="already handled by adapter 'a'"):
        registry.register(FakeAdapter("b", "src-shamela", {"3.0", "4.0"}))
    assert registry.keys() == [("src-shamela", "3.0")]


def test_one_adapter_for_several_versions():
    registry = AdapterRegistry()
    adapter = registry.register(FakeAdapter("a", "src-a", {"1.0", "1.1"}))
    assert registry.keys() == [("src-a", "1.0"), ("src-a", "1.1")]
    assert registry.resolve({"pub": {"source_code": "src-a"}, "metadata": {"af_schema": "1.1"}}) is adapter


def test_adapter_without_versions_rejected():
    with pytest.raises(ValueError, match="no schema versions"):
        AdapterRegistry().register(FakeAdapter("a", "src-a", set()))
