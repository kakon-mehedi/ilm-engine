import hashlib
import re

import pytest

from ilm_engine.ids import PREFIXES, make_id, natural_key, pub_ref

SAMPLE_PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"


def test_pub_ref_sample():
    assert pub_ref("pub_01M0CJECV4ZHFTP02BJQ6D3STJ", 6) == SAMPLE_PUB_REF


@pytest.mark.parametrize(
    "pub_id, revision", [("", 6), ("pub_X@r1", 6), ("pub_X", -1), ("pub_X", "6"), ("pub_X", True)]
)
def test_pub_ref_rejects_invalid_input(pub_id, revision):
    with pytest.raises(ValueError):
        pub_ref(pub_id, revision)


def test_make_id_matches_formula():
    key = natural_key(8, "b000135", 0)
    expected = hashlib.sha256(f"{SAMPLE_PUB_REF}|8|b000135|0".encode()).hexdigest()[:12]
    assert make_id("ku", SAMPLE_PUB_REF, key) == f"ku_{expected}"


def test_same_input_same_id():
    assert make_id("ent", SAMPLE_PUB_REF, "هند|b000135") == make_id("ent", SAMPLE_PUB_REF, "هند|b000135")


def test_different_natural_key_different_id():
    assert make_id("ku", SAMPLE_PUB_REF, "8|b000135|0") != make_id("ku", SAMPLE_PUB_REF, "9|b000136|0")


def test_different_revision_different_id():
    assert make_id("sec", SAMPLE_PUB_REF, "1|b000098") != make_id(
        "sec", "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r5", "1|b000098"
    )


def test_different_prefix_keeps_hash():
    ku = make_id("ku", SAMPLE_PUB_REF, "8|b000135|0")
    rev = make_id("rev", SAMPLE_PUB_REF, "8|b000135|0")
    assert ku.split("_")[1] == rev.split("_")[1] and ku != rev


@pytest.mark.parametrize("prefix", sorted(PREFIXES))
def test_every_prefix_produces_well_formed_id(prefix):
    assert re.fullmatch(rf"{prefix}_[0-9a-f]{{12}}", make_id(prefix, SAMPLE_PUB_REF, "key"))


def test_allowed_prefixes():
    assert PREFIXES == {"sec", "ku", "ent", "rel", "ann", "cit", "wrk", "iss", "rev", "run", "grp"}


@pytest.mark.parametrize("prefix", ["", "foo", "KU", "pub", "b", "ku_"])
def test_invalid_prefix_raises(prefix):
    with pytest.raises(ValueError, match="unknown ID prefix"):
        make_id(prefix, SAMPLE_PUB_REF, "key")


def test_our_wrk_ids_differ_from_source_work_ids():
    ours = make_id("wrk", SAMPLE_PUB_REF, "الإصابة في تمييز الصحابة")
    assert re.fullmatch(r"wrk_[0-9a-f]{12}", ours)
    assert not re.fullmatch(r"wrk_[0-9A-HJKMNP-TV-Z]{26}", ours)


def test_empty_pub_ref_or_key_raises():
    with pytest.raises(ValueError):
        make_id("ku", "", "key")
    with pytest.raises(ValueError):
        make_id("ku", SAMPLE_PUB_REF, "")


def test_natural_key_joins_parts():
    assert natural_key("toc", 3, "b000098") == "toc|3|b000098"
    with pytest.raises(ValueError):
        natural_key()
