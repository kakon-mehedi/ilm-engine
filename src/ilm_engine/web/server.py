"""Local web UI for the pipeline (`ilm-engine serve`): upload a book, watch the steps, review, browse results.

The server is a thin layer over the same functions the CLI uses: `prepare_context` + `Runner` for a run,
`apply_decisions` for review, `search` for the index. A run executes in a background thread and reports
each step through a `StepListener`; the browser follows it as server-sent events. One run at a time,
because runs share the output folder and the step cache. Bound to localhost by default.
"""

from __future__ import annotations

import asyncio
import json
import re
import threading
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ilm_engine.enrichment.models import ReviewDecision, StepRecord
from ilm_engine.pipeline.narration import STORIES, summarize
from ilm_engine.pipeline.runner import RunContext, Runner, Step
from ilm_engine.pipeline.steps import PIPELINE

STATIC = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
FILES = {  # downloadable outputs and their media types
    "enrichment.json": "application/json",
    "metadata.json": "application/json",
    "document_report.json": "application/json",
    "structure.json": "application/json",
    "origin_map.json": "application/json",
    "annotations.json": "application/json",
    "citations.json": "application/json",
    "related_works.json": "application/json",
    "knowledge_units.json": "application/json",
    "entities.json": "application/json",
    "relationships.json": "application/json",
    "validation_report.json": "application/json",
    "review_queue.json": "application/json",
    "review_decisions.json": "application/json",
    "review_audit.jsonl": "application/x-ndjson",
    "training_examples.jsonl": "application/x-ndjson",
    "run_manifest.json": "application/json",
    "eval_report.json": "application/json",
    "graph.html": "text/html",
    "graph.cypher": "text/plain",
    "enrichment.db": "application/vnd.sqlite3",
}


@dataclass
class Paths:
    out: Path
    store: Path
    cache: Path

    @property
    def uploads(self) -> Path:
        return self.cache / "uploads"


@dataclass
class Job:
    job_id: str
    status: str = "running"  # running | done | failed
    events: list[dict[str, Any]] = field(default_factory=list)
    pub_ref: str | None = None

    def emit(self, kind: str, **data: Any) -> None:
        self.events.append({"type": kind, **data})


class EventListener:
    """Turns runner callbacks into JSON events for the browser."""

    def __init__(self, job: Job) -> None:
        self.job = job

    def started(self, index: int, total: int, step: Step, ctx: RunContext) -> None:
        self.job.emit("step_started", index=index, total=total, name=step.name)

    def finished(
        self, index: int, total: int, step: Step, ctx: RunContext, record: StepRecord, next_step: str | None
    ) -> None:
        result = ctx.results.get(step.name)
        counts = (result.data.get("counts") if result else None) or {}
        self.job.emit(
            "step_finished",
            index=index,
            total=total,
            name=step.name,
            status=record.status,
            duration_ms=record.duration_ms,
            summary="" if record.status == "failed" else summarize(step.name, ctx, record),
            counts={key: value for key, value in counts.items() if isinstance(value, int)},
            issues=len(result.issues) if result else 0,
            pub_ref=ctx.pub_ref,
        )


class DecisionIn(BaseModel):
    review_id: str
    decision: str
    new_value: Any | None = None
    reason: str | None = None
    reviewer_id: str
    reviewer_role: str


def _safe_name(name: str | None, default: str) -> str:
    cleaned = re.sub(r"[^\w.\-]", "_", Path(name or default).name)
    return cleaned if cleaned.strip("._") else default


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def create_app(paths: Paths) -> FastAPI:
    app = FastAPI(title="ILM Engine", docs_url="/api/docs", redoc_url=None)
    jobs: dict[str, Job] = {}
    run_lock = threading.Lock()
    books_cache: dict[str, tuple[float, Any]] = {}

    def book_dir(pub_ref: str) -> Path:
        directory = paths.out / pub_ref
        if "/" in pub_ref or pub_ref.startswith(".") or not (directory / "enrichment.json").is_file():
            raise HTTPException(404, f"no processed book {pub_ref!r}")
        return directory

    def canonical(pub_ref: str) -> Any:
        """The canonical book, rebuilt from the read-only store copy (cached per store manifest)."""
        from ilm_engine.adapters.registry import resolve

        stored = paths.store / pub_ref
        manifest_path = stored / "manifest.json"
        if not manifest_path.is_file():
            raise HTTPException(404, f"originals of {pub_ref!r} are not in the store")
        stamp = manifest_path.stat().st_mtime
        cached = books_cache.get(pub_ref)
        if cached and cached[0] == stamp:
            return cached[1]
        sources = sorted(stored.glob("*.json"))
        raw = _read_json(next(p for p in sources if p.name != "manifest.json"))
        pdfs = sorted(stored.glob("*.pdf"))
        book = resolve(raw).to_canonical(raw, pdfs[0] if pdfs else None)
        books_cache[pub_ref] = (stamp, book)
        return book

    def run_job(job: Job, inputs: dict[str, Path], fresh: bool) -> None:
        from ilm_engine.pipeline.session import prepare_context

        try:
            ctx = prepare_context(inputs, paths.out, paths.store, paths.cache)
            Runner(PIPELINE, cache_dir=paths.cache / "steps").run(
                ctx, no_cache=fresh, listener=EventListener(job)
            )
            job.pub_ref = ctx.pub_ref
            evaluation = _evaluate(paths.out / str(ctx.pub_ref))
            job.status = "done"
            job.emit("done", pub_ref=ctx.pub_ref, evaluation=evaluation)
        except Exception as error:  # reported to the browser; the server keeps running
            job.status = "failed"
            job.emit("failed", error=f"{type(error).__name__}: {error}")
        finally:
            run_lock.release()

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse((STATIC / "index.html").read_text(encoding="utf-8"))

    @app.get("/api/pipeline")
    def pipeline() -> list[dict[str, Any]]:
        return [
            {
                "index": index,
                "name": name,
                "phase": STORIES[name].phase,
                "title": STORIES[name].title,
                "doing": STORIES[name].doing,
            }
            for index, name in enumerate(PIPELINE.names(), 1)
        ]

    @app.post("/api/runs")
    async def start_run(
        book: Annotated[UploadFile, File()],
        pdf: Annotated[UploadFile | None, File()] = None,
        fresh: Annotated[bool, Form()] = True,
    ) -> dict[str, str]:
        if not run_lock.acquire(blocking=False):
            raise HTTPException(409, "another run is in progress")
        try:
            job = Job(uuid.uuid4().hex[:12])
            folder = paths.uploads / job.job_id
            folder.mkdir(parents=True, exist_ok=True)
            json_path = folder / _safe_name(book.filename, "book.json")
            payload = await book.read(MAX_UPLOAD_BYTES + 1)
            if len(payload) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "the book JSON is larger than 200 MB")
            try:
                json.loads(payload)
            except ValueError as error:
                raise HTTPException(400, f"not a valid JSON file: {error}") from None
            json_path.write_bytes(payload)
            inputs = {"json": json_path}
            if pdf is not None and pdf.filename:
                pdf_path = folder / _safe_name(pdf.filename, "scan.pdf")
                pdf_path.write_bytes(await pdf.read())
                inputs["pdf"] = pdf_path
        except BaseException:
            run_lock.release()
            raise
        jobs[job.job_id] = job
        threading.Thread(target=run_job, args=(job, inputs, fresh), daemon=True).start()
        return {"job_id": job.job_id}

    @app.get("/api/runs/{job_id}/events")
    async def run_events(job_id: str) -> StreamingResponse:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "unknown run")

        async def stream() -> AsyncIterator[str]:
            sent = 0
            while True:
                while sent < len(job.events):
                    yield f"data: {json.dumps(job.events[sent], ensure_ascii=False)}\n\n"
                    sent += 1
                if job.status != "running" and sent >= len(job.events):
                    return
                await asyncio.sleep(0.05)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/books")
    def books() -> list[dict[str, Any]]:
        listing = []
        for directory in sorted(paths.out.glob("*/enrichment.json")):
            folder = directory.parent
            manifest = folder / "run_manifest.json"
            meta = _read_json(folder / "metadata.json") if (folder / "metadata.json").is_file() else {}
            listing.append(
                {
                    "pub_ref": folder.name,
                    "title": (meta.get("title") or {}).get("value"),
                    "finished_at": _read_json(manifest).get("finished_at") if manifest.is_file() else None,
                }
            )
        return listing

    @app.get("/api/books/{pub_ref}/overview")
    def overview(pub_ref: str) -> dict[str, Any]:
        directory = book_dir(pub_ref)
        enrichment = _read_json(directory / "enrichment.json")
        queue = _read_json(directory / "review_queue.json")
        manifest = _read_json(directory / "run_manifest.json")
        origins = _read_json(directory / "origin_map.json")["counts"]
        decisions: dict[str, int] = {}
        for result in enrichment["validation"]:
            decisions[result["decision"]] = decisions.get(result["decision"], 0) + 1
        review: dict[str, int] = {}
        for item in queue:
            review[item["status"]] = review.get(item["status"], 0) + 1
        evaluation = directory / "eval_report.json"
        return {
            "pub_ref": pub_ref,
            "stats": enrichment["stats"],
            "metadata": enrichment["metadata"],
            "document_report": enrichment["document_report"],
            "origins": origins,
            "validation": decisions,
            "review": review,
            "works": len(enrichment["works"]),
            "manifest": {
                key: manifest.get(key)
                for key in ("run_id", "code_version", "config_hash", "started_at", "finished_at", "adapter")
            },
            "integrity": manifest.get("integrity"),
            "evaluation": _read_json(evaluation) if evaluation.is_file() else None,
            "has_pdf": any((paths.store / pub_ref).glob("*.pdf")),
            "files": [
                {"name": name, "bytes": (directory / name).stat().st_size}
                for name in FILES
                if (directory / name).is_file()
            ],
        }

    @app.get("/api/books/{pub_ref}/review")
    def review(pub_ref: str) -> dict[str, Any]:
        directory = book_dir(pub_ref)
        book = canonical(pub_ref)
        items = _read_json(directory / "review_queue.json")
        for item in items:
            item["context"] = [
                {
                    "block_id": block_id,
                    "page": book.blocks[block_id].page,
                    "text": book.blocks[block_id].text,
                    "marks": sorted(
                        [a["start"], a["end"]]
                        for a in item["anchors"]
                        if a["block_id"] == block_id and not a.get("quote_truncated")
                    ),
                }
                for block_id in item["context_block_ids"][:3]
                if block_id in book.blocks
            ]
        entities = _read_json(directory / "enrichment.json")["entities"]
        wanted = {issue_id for item in items for issue_id in item["issues"]}
        issues = {
            issue["issue_id"]: {key: issue[key] for key in ("code", "message", "severity")}
            for issue in _read_json(directory / "enrichment.json")["issues"]
            if issue["issue_id"] in wanted
        }
        decisions = directory / "review_decisions.json"
        return {
            "items": items,
            "issues": issues,
            "names": {entity["entity_id"]: entity["canonical_name"] for entity in entities},
            "decisions": _read_json(decisions) if decisions.is_file() else [],
        }

    @app.post("/api/books/{pub_ref}/review")
    def decide(pub_ref: str, decision: DecisionIn) -> dict[str, Any]:
        from pydantic import ValidationError

        from ilm_engine.validation.review_queue import ReviewError, apply_decisions, now

        directory = book_dir(pub_ref)
        try:
            parsed = ReviewDecision.model_validate({**decision.model_dump(), "decided_at": now()})
            summary = apply_decisions(directory, [parsed])
        except ValidationError as error:
            raise HTTPException(422, str(error)) from None
        except ReviewError as error:
            raise HTTPException(403, str(error)) from None
        return {"ok": True, **summary}

    @app.get("/api/books/{pub_ref}/records/{kind}")
    def records(pub_ref: str, kind: str) -> list[dict[str, Any]]:
        """Consolidated records from enrichment.json (entities include people added by `relations`)."""
        if kind not in ("knowledge_units", "entities", "relationships", "citations", "works"):
            raise HTTPException(404, f"no records {kind!r}")
        result: list[dict[str, Any]] = _read_json(book_dir(pub_ref) / "enrichment.json")[kind]
        return result

    @app.get("/api/books/{pub_ref}/search")
    def search(pub_ref: str, q: str, limit: int = 20) -> list[dict[str, Any]]:
        from ilm_engine.search.lexical import search as lexical_search

        directory = book_dir(pub_ref)
        index = _read_json(directory / "search_index.json")
        book = canonical(pub_ref)
        hits = []
        for hit in lexical_search(index, q, limit=min(limit, 100)):
            anchor = hit.anchor or {}
            block = book.blocks.get(anchor.get("block_id", ""))
            hits.append(
                {
                    "doc_id": hit.doc_id,
                    "kind": hit.kind,
                    "score": round(hit.score, 3),
                    "anchor": anchor,
                    "text": block.text if block else anchor.get("quote"),
                }
            )
        return hits

    @app.get("/api/books/{pub_ref}/files/{name}")
    def download(pub_ref: str, name: str) -> FileResponse:
        path = book_dir(pub_ref) / name
        if name not in FILES or not path.is_file():
            raise HTTPException(404, f"no file {name!r}")
        disposition = "inline" if name == "graph.html" else "attachment"
        return FileResponse(path, media_type=FILES[name], filename=name, content_disposition_type=disposition)

    @app.get("/api/books/{pub_ref}/pdf")
    def scan(pub_ref: str) -> FileResponse:
        book_dir(pub_ref)
        pdfs = sorted((paths.store / pub_ref).glob("*.pdf"))
        if not pdfs:
            raise HTTPException(404, "no scan PDF for this book")
        return FileResponse(pdfs[0], media_type="application/pdf", content_disposition_type="inline")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


def _evaluate(directory: Path) -> dict[str, Any] | None:
    """Precision/recall against the printed-index gold sample, when the gold is for this book."""
    from ilm_engine.enrichment.models import Enrichment
    from ilm_engine.eval.gold import DEFAULT_GOLD, evaluate, load_gold
    from ilm_engine.storage.json_store import JsonStore

    if not DEFAULT_GOLD.is_file():
        return None
    gold = load_gold()
    if gold.get("pub_ref") != directory.name:
        return None
    enrichment = Enrichment.model_validate_json((directory / "enrichment.json").read_text(encoding="utf-8"))
    report = evaluate(enrichment, gold)
    JsonStore(enrichment.pub_ref, directory.parent).write("eval_report.json", report)
    return {key: report[key] for key in ("precision", "recall", "f1", "matched")}
