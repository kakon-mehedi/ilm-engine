"""Web UI server: upload → live events → results, review decisions and path safety."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ilm_engine.integrity.hashing import file_sha256
from ilm_engine.pipeline.steps import STEP_NAMES
from ilm_engine.web.server import Paths, create_app

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUB_REF = "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
BOOK = f"/api/books/{PUB_REF.replace('@', '%40')}"


def events(client: TestClient, job_id: str) -> list[dict]:
    received = []
    with client.stream("GET", f"/api/runs/{job_id}/events") as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                received.append(json.loads(line[6:]))
    return received


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    base = tmp_path_factory.mktemp("web")
    data_before = {path.name: file_sha256(path) for path in DATA.iterdir() if path.is_file()}
    client = TestClient(create_app(Paths(out=base / "out", store=base / "store", cache=base / "cache")))
    with (
        (DATA / "demo_book_daraqutni.json").open("rb") as book,
        (DATA / "demo_book_daraqutni_v1.pdf").open("rb") as pdf,
    ):
        response = client.post("/api/runs", files={"book": book, "pdf": pdf}, data={"fresh": "true"})
    assert response.status_code == 200, response.text
    yield {"client": client, "events": events(client, response.json()["job_id"]), "data_before": data_before}
    for path in (base / "store").rglob("*"):
        if path.is_file():
            os.chmod(path, 0o644)


def test_pipeline_lists_the_steps_with_their_phase():
    client = TestClient(create_app(Paths(out=Path("unused"), store=Path("unused"), cache=Path("unused"))))
    steps = client.get("/api/pipeline").json()
    assert [step["name"] for step in steps] == list(STEP_NAMES)
    assert steps[0]["phase"].startswith("Phase 1") and steps[-1]["phase"].startswith("Phase 8")


def test_index_and_static_assets_served():
    client = TestClient(create_app(Paths(out=Path("unused"), store=Path("unused"), cache=Path("unused"))))
    assert "ILM Engine" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200


def test_invalid_json_upload_rejected(tmp_path):
    client = TestClient(
        create_app(Paths(out=tmp_path / "out", store=tmp_path / "store", cache=tmp_path / "c"))
    )
    response = client.post("/api/runs", files={"book": ("book.json", b"{not json", "application/json")})
    assert response.status_code == 400 and "not a valid JSON" in response.json()["detail"]
    retry = client.post("/api/runs", files={"book": ("book.json", b"{not json", "application/json")})
    assert retry.status_code == 400  # the run lock was released


def test_run_streams_every_step_then_done(run):
    received = run["events"]
    started = [e["name"] for e in received if e["type"] == "step_started"]
    finished = [e for e in received if e["type"] == "step_finished"]
    assert started == list(STEP_NAMES) and [e["name"] for e in finished] == list(STEP_NAMES)
    assert all(e["status"] == "ran" for e in finished)
    by_name = {e["name"]: e for e in finished}
    assert by_name["units"]["counts"]["units"] == 75 and "75 knowledge units" in by_name["units"]["summary"]
    assert received[-1]["type"] == "done" and received[-1]["pub_ref"] == PUB_REF
    assert received[-1]["evaluation"]["precision"] == 1.0 and received[-1]["evaluation"]["recall"] == 1.0


def test_overview(run):
    overview = run["client"].get(f"{BOOK}/overview").json()
    assert overview["stats"]["units"] == 75 and overview["stats"]["entities"] == 111
    assert overview["integrity"]["originals_unchanged"] is True and overview["has_pdf"] is True
    assert overview["evaluation"]["recall"] == 1.0
    assert {"enrichment.json", "graph.html", "run_manifest.json"} <= {f["name"] for f in overview["files"]}


def test_books_listing(run):
    assert [book["pub_ref"] for book in run["client"].get("/api/books").json()] == [PUB_REF]


def test_review_items_carry_source_context_and_names(run):
    data = run["client"].get(f"{BOOK}/review").json()
    assert len(data["items"]) == 136
    item = data["items"][0]
    assert item["context"] and item["context"][0]["text"] and item["context"][0]["marks"]
    relationship = next(i for i in data["items"] if i["target_kind"] == "relationship")
    value = relationship["proposed_value"]
    assert value["subject_entity_id"] in data["names"] and value["object_entity_id"] in data["names"]
    assert all(issue_id in data["issues"] for i in data["items"] for issue_id in i["issues"])


def test_sensitive_item_needs_a_scholar(run):
    client = run["client"]
    items = client.get(f"{BOOK}/review").json()["items"]
    sensitive = next(i for i in items if i["sensitive"])
    decision = {"review_id": sensitive["review_id"], "decision": "approved", "reviewer_id": "t"}
    denied = client.post(f"{BOOK}/review", json={**decision, "reviewer_role": "editor_reviewer"})
    assert denied.status_code == 403 and "scholar_reviewer" in denied.json()["detail"]
    allowed = client.post(f"{BOOK}/review", json={**decision, "reviewer_role": "scholar_reviewer"})
    assert allowed.status_code == 200 and allowed.json()["training_examples"] == 1


def test_decision_updates_queue_and_audit(run):
    client = run["client"]
    item = next(i for i in client.get(f"{BOOK}/review").json()["items"] if not i["sensitive"])
    response = client.post(
        f"{BOOK}/review",
        json={
            "review_id": item["review_id"],
            "decision": "rejected",
            "reason": "checked against the scan",
            "reviewer_id": "t",
            "reviewer_role": "editor_reviewer",
        },
    )
    assert response.status_code == 200
    after = {i["review_id"]: i for i in client.get(f"{BOOK}/review").json()["items"]}
    assert after[item["review_id"]]["status"] == "rejected"
    audit = client.get(f"{BOOK}/files/review_audit.jsonl").text.splitlines()
    assert any(json.loads(line)["reason"] == "checked against the scan" for line in audit)


def test_invalid_decision_rejected(run):
    response = run["client"].post(
        f"{BOOK}/review",
        json={
            "review_id": "rev_x",
            "decision": "maybe",
            "reviewer_id": "t",
            "reviewer_role": "editor_reviewer",
        },
    )
    assert response.status_code == 422


def test_records_include_people_added_by_relations(run):
    entities = run["client"].get(f"{BOOK}/records/entities").json()
    relationships = run["client"].get(f"{BOOK}/records/relationships").json()
    ids = {entity["entity_id"] for entity in entities}
    assert len(entities) == 111
    assert all(r["subject_entity_id"] in ids and r["object_entity_id"] in ids for r in relationships)


def test_search_returns_text_and_anchor(run):
    hits = run["client"].get(f"{BOOK}/search", params={"q": "الدارقطني", "limit": 5}).json()
    assert hits and all(hit["anchor"].get("page") for hit in hits)
    assert any("الدارقطني" in hit["text"] for hit in hits)


def test_files_and_pdf(run):
    client = run["client"]
    assert client.get(f"{BOOK}/files/graph.html").headers["content-type"].startswith("text/html")
    assert client.get(f"{BOOK}/pdf").headers["content-type"] == "application/pdf"


@pytest.mark.parametrize(
    "path",
    [
        f"{BOOK}/files/pyproject.toml",
        f"{BOOK}/files/..%2F..%2Fpyproject.toml",
        "/api/books/..%2Fdata/overview",
        "/api/books/pub_unknown@r1/overview",
        f"{BOOK}/records/secrets",
    ],
)
def test_paths_outside_the_book_are_refused(run, path):
    assert run["client"].get(path).status_code == 404


def test_data_folder_unchanged(run):
    assert {path.name: file_sha256(path) for path in DATA.iterdir() if path.is_file()} == run["data_before"]
