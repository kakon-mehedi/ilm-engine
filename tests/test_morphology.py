import pytest

from ilm_engine.nlp import morphology
from ilm_engine.nlp.morphology import analyze, is_available, roots_and_lemmas


def test_disabled_returns_empty():
    assert analyze("أسلمت") == []
    assert analyze("أسلمت", enabled=False) == []
    assert roots_and_lemmas(["أسلمت", "وتزوجت"]) == ([], [])


def test_missing_library_returns_empty(monkeypatch):
    morphology._backend.cache_clear()
    import builtins

    real_import = builtins.__import__

    def no_camel(name, *args, **kwargs):
        if name.startswith("camel_tools"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_camel)
    try:
        assert analyze("أسلمت", enabled=True) == []
        assert is_available() is False
    finally:
        morphology._backend.cache_clear()


def test_backend_deduplicates_analyses():
    class FakeAnalyzer:
        def analyze(self, word):
            return [
                {"lex": "أَسْلَم", "root": "س.ل.م", "pos": "verb"},
                {"lex": "أَسْلَم", "root": "س.ل.م", "pos": "verb"},
                {"lex": "سَلِم", "root": "س.ل.م", "pos": "verb"},
            ]

    backend = morphology._Backend(FakeAnalyzer())
    assert backend.analyze("أسلمت") == [
        {"lemma": "أَسْلَم", "root": "س.ل.م", "pos": "verb"},
        {"lemma": "سَلِم", "root": "س.ل.م", "pos": "verb"},
    ]
    assert backend.analyze("  ") == []


@pytest.mark.skipif(not is_available(), reason="camel-tools or its morphology database is not installed")
def test_real_backend_finds_root_slm():
    roots = {item["root"] for item in analyze("أسلمت", enabled=True)}
    assert any(root and {"س", "ل", "م"} <= set(root) for root in roots)
