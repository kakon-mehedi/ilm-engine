import pytest

from ilm_engine.config import load_config
from ilm_engine.enrichment.models import Anchor
from ilm_engine.extractors.units import assemble_units, detect_entries, with_rule_facts
from ilm_engine.processors.annotations import build as build_annotations
from ilm_engine.processors.origin import assign
from ilm_engine.processors.structure import build as build_structure
from ilm_engine.validation.rules import Records, report, run_checks

PUB_ID = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"


@pytest.fixture(scope="module")
def records(sample_book):
    config = load_config(PUB_ID)
    origins = assign(sample_book, config).blocks
    annotations = build_annotations(sample_book).annotations
    structure = build_structure(sample_book)
    units, _ = assemble_units(
        sample_book, detect_entries(sample_book, origins, config), annotations, structure, config
    )
    return Records(
        units=with_rule_facts(sample_book, units, origins, config), others=[*annotations, *structure.sections]
    )


def by_name(checks):
    return {check.name: check for check in checks}


def test_sample_has_no_failures(sample_book, records):
    checks = by_name(run_checks(sample_book, records))
    for name in ("anchors", "ids_unique", "traceable", "numbering", "origin_present"):
        assert checks[name].passed, (name, checks[name].failures[:3])
    assert checks["anchors"].checked > 300 and checks["numbering"].checked == 75


def test_report_lists_counts_per_check(sample_book, records):
    data = report(run_checks(sample_book, records))
    assert data["passed"] is True
    assert set(data["counts"]) == {
        "anchors",
        "ids_unique",
        "origin_present",
        "relation_endpoints",
        "dual_grammar",
        "numbering",
        "traceable",
    }


def test_stale_anchor_detected(sample_book, records):
    unit = records.units[0]
    bad = unit.anchors[0].model_copy(update={"quote": "x"})
    broken = Records(units=[unit.model_copy(update={"anchors": [bad]})])
    assert by_name(run_checks(sample_book, broken))["anchors"].failures[0]["status"] == "stale"


def test_unknown_block_is_orphaned(sample_book, records):
    unit = records.units[0]
    ghost = Anchor.model_validate({**unit.anchors[0].model_dump(), "block_id": "b999999"})
    failures = by_name(
        run_checks(sample_book, Records(units=[unit.model_copy(update={"anchors": [ghost]})]))
    )["anchors"].failures
    assert failures[0]["status"] == "orphaned"


def test_duplicate_ids_and_gaps(sample_book, records):
    duplicated = Records(units=[records.units[0], records.units[0], records.units[2]])
    checks = by_name(run_checks(sample_book, duplicated))
    assert checks["ids_unique"].failures and {"missing": 2} in checks["numbering"].failures


def test_validate_step_sensitivity_and_results(sample_book, records):
    from ilm_engine.validation.validate import validate

    validation = validate(sample_book, records, load_config(PUB_ID), ["biography", "hadith"])
    assert validation.rules["passed"] is True
    sensitive = [u for u in validation.records.units if u.review_status == "pending_review"]
    assert sensitive and all(i.code == "sensitive_content" for i in validation.issues)
    kinds = {r.target_kind for r in validation.results}
    assert kinds == {"unit", "fact"}
    assert len([r for r in validation.results if r.target_kind == "unit"]) == 75
    for result in validation.results:
        if result.sensitive:
            assert result.decision == "pending_review"
