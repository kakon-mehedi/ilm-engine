"""The pipeline's 21 steps, in execution order (DECISIONS §12b).

Each step declares the steps it needs, the output files it writes (DECISIONS §10) and the config
sections it reads; together these form its cache key (ADR-004). A step whose implementation has not
been wired yet runs as a placeholder and is reported as `skipped`. Implementations are attached with
`_wire`, from `ilm_engine.pipeline.stages`.
"""

from __future__ import annotations

from ilm_engine.pipeline.runner import RunContext, Step, StepRegistry, StepResult


def _placeholder(ctx: RunContext) -> StepResult:
    return StepResult(skipped=True)


def _step(name: str, *needs: str, outputs: tuple[str, ...] = (), config: tuple[str, ...] = (), **kw) -> Step:
    return Step(name=name, fn=_placeholder, needs=needs, outputs=outputs, config=config, **kw)


STEP_NAMES = (
    "ingest",
    "adapt",
    "integrity_register",
    "document_analysis",
    "structure",
    "origin",
    "metadata",
    "genre",
    "annotations",
    "citations",
    "related_works",
    "units",
    "entities",
    "relations",
    "search_index",
    "validate",
    "review_queue",
    "store",
    "export",
    "integrity_verify",
    "manifest",
)


def build_registry() -> StepRegistry:
    """A fresh registry with every step as a placeholder."""
    return StepRegistry(
        [
            _step("ingest", uses_inputs=True),
            _step("adapt", "ingest"),
            _step("integrity_register", "ingest", "adapt"),
            _step("document_analysis", "adapt", "integrity_register", outputs=("document_report.json",)),
            _step("structure", "adapt", outputs=("structure.json",)),
            _step("origin", "adapt", "structure", outputs=("origin_map.json",), config=("origin",)),
            _step("metadata", "adapt", "origin", "document_analysis", outputs=("metadata.json",)),
            _step("genre", "adapt", "metadata", config=("llm",)),
            _step("annotations", "adapt", "origin", outputs=("annotations.json",)),
            _step("citations", "annotations", "origin", outputs=("citations.json",)),
            _step("related_works", "citations", "metadata", outputs=("related_works.json",), config=("llm",)),
            _step(
                "units",
                "structure",
                "origin",
                "annotations",
                "citations",
                "genre",
                outputs=("knowledge_units.json",),
                config=("entries", "llm"),
            ),
            _step("entities", "units", "annotations", outputs=("entities.json",), config=("llm",)),
            _step(
                "relations",
                "entities",
                "units",
                "structure",
                outputs=("relationships.json",),
                config=("llm",),
            ),
            _step("search_index", "units", "entities", outputs=("search_index.json",), config=("features",)),
            _step(
                "validate",
                "metadata",
                "citations",
                "related_works",
                "units",
                "entities",
                "relations",
                outputs=("validation_report.json",),
                config=("review", "confidence"),
            ),
            _step("review_queue", "validate", outputs=("review_queue.json",), config=("review",)),
            _step("store", "review_queue", "search_index"),
            _step("export", "store", outputs=("enrichment.json",)),
            _step("integrity_verify", "export", "integrity_register"),
            _step("manifest", "integrity_verify", outputs=("run_manifest.json",)),
        ]
    )


def _wire(registry: StepRegistry) -> StepRegistry:
    """Attach the implemented steps (imported here to keep module imports light)."""
    from ilm_engine.pipeline import stages
    from ilm_engine.pipeline.manifest import manifest_step

    registry.replace("ingest", stages.ingest)
    registry.replace("adapt", stages.adapt)
    registry.replace("integrity_register", stages.integrity_register)
    registry.replace("document_analysis", stages.document_analysis)
    registry.replace("structure", stages.structure)
    registry.replace("origin", stages.origin)
    registry.replace("metadata", stages.metadata)
    registry.replace("genre", stages.genre)
    registry.replace("annotations", stages.annotate)
    registry.replace("manifest", manifest_step)
    return registry


PIPELINE = _wire(build_registry())
assert tuple(PIPELINE.names()) == STEP_NAMES
