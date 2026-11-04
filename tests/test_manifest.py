from pathlib import Path

import pytest

from ilm_engine.config import load_config
from ilm_engine.enrichment.models import RunManifest, StepRecord
from ilm_engine.integrity.hashing import file_sha256
from ilm_engine.pipeline.manifest import build_manifest, code_version, manifest_step
from ilm_engine.pipeline.runner import RunContext, StepResult

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "demo_book_daraqutni.json"
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"


@pytest.fixture
def ctx(tmp_path):
    context = RunContext(
        config=load_config("pub_01M0CJECV4ZHFTP02BJQ6D3STJ"), inputs={"json": SAMPLE}, out_root=tmp_path
    )
    context.pub_ref = PUB_REF
    context.store.write("document_report.json", {"block_total": 594})
    context.store.write("structure.json", {"sections": []})
    context.results["adapt"] = StepResult(
        data={"adapter": {"id": "shamela_v3", "version": "1.0.0"}, "counts": {"blocks": 594}}
    )
    context.results["integrity_verify"] = StepResult(data={"integrity": {"originals_unchanged": True}})
    return context


def record(name):
    return StepRecord(name=name, version="1.0.0", status="ran", cache_key="k", duration_ms=3, outputs=[])


def test_manifest_lists_every_output_with_sha256(ctx):
    manifest = build_manifest(ctx, [record("ingest"), record("adapt")])
    assert {item.path for item in manifest.outputs} == {"document_report.json", "structure.json"}
    for item in manifest.outputs:
        assert item.sha256 == file_sha256(ctx.store.path(item.path)) and item.bytes > 0


def test_input_hash_of_sample_present(ctx):
    [entry] = build_manifest(ctx, []).inputs
    assert entry.path == str(SAMPLE) and entry.sha256 == file_sha256(SAMPLE)


def test_provenance_fields(ctx):
    manifest = build_manifest(ctx, [record("ingest")])
    assert manifest.pub_ref == PUB_REF and manifest.config_hash == ctx.config.config_hash
    assert manifest.canonical_schema_version == "1.0" and manifest.enrichment_schema_version == "1.0"
    assert manifest.normalizer_version == "1.0.0"
    assert manifest.adapter == {"id": "shamela_v3", "version": "1.0.0"}
    assert manifest.counts == {"blocks": 594} and manifest.integrity == {"originals_unchanged": True}
    assert manifest.llm["provider"] == "null" and manifest.llm["prompts"]["entry_facts"] == "v1"
    assert [step.name for step in manifest.steps] == ["ingest"]
    assert manifest.code_version


def test_run_id_is_deterministic(ctx):
    first = build_manifest(ctx, [], code="abc")
    second = build_manifest(ctx, [], code="abc")
    assert first.run_id == second.run_id and first.run_id.startswith("run_")
    assert build_manifest(ctx, [], code="def").run_id != first.run_id


def test_manifest_step_writes_valid_manifest(ctx):
    ctx.records = [record("ingest")]
    result = manifest_step(ctx)
    manifest = result.files["run_manifest.json"]
    assert isinstance(manifest, RunManifest)
    path = ctx.store.write("run_manifest.json", manifest)
    assert RunManifest.model_validate_json(path.read_text(encoding="utf-8")) == manifest
    assert "run_manifest.json" not in {item.path for item in build_manifest(ctx, []).outputs}


def test_manifest_step_skipped_without_pub_ref(tmp_path):
    context = RunContext(config=load_config(), inputs={"json": SAMPLE}, out_root=tmp_path)
    assert manifest_step(context).skipped


def test_code_version_format():
    version = code_version()
    assert version == "unknown" or len(version) == 40 or version.startswith("dirty-")
