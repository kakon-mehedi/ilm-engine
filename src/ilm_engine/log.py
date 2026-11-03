"""Structured logging (NFR-010).

With `json=True` every record is one JSON object per line:
`{"ts", "level", "run_id", "step", "pub_ref", "logger", "msg", "extra"}`. `run_id`, `step` and
`pub_ref` come from `log_context(...)`, so a step sets them once and every log call inside inherits
them. Fields passed with `logger.info(..., extra={...})` land under `extra`.

Log block IDs and offsets, never full book text.
"""

from __future__ import annotations

import contextvars
import json as jsonlib
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import IO, Any

LOGGER_NAME = "ilm_engine"
CONTEXT_FIELDS = ("run_id", "step", "pub_ref")

_context: contextvars.ContextVar[dict[str, str] | None] = contextvars.ContextVar(
    "ilm_engine_log_context", default=None
)

# Attributes every LogRecord has; anything else on a record came from `extra=`.
_RECORD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime"}


def get_logger(name: str | None = None) -> logging.Logger:
    """Logger under the `ilm_engine` namespace, e.g. `get_logger("processors.origin")`."""
    return logging.getLogger(f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME)


@contextmanager
def log_context(**fields: str | None) -> Iterator[None]:
    """Attach `run_id`, `step` and/or `pub_ref` to every record logged inside the block."""
    unknown = set(fields) - set(CONTEXT_FIELDS)
    if unknown:
        raise ValueError(f"unknown log context field(s): {', '.join(sorted(unknown))}")
    merged = {**(_context.get() or {}), **{key: value for key, value in fields.items() if value is not None}}
    token = _context.set(merged)
    try:
        yield
    finally:
        _context.reset(token)


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = _context.get() or {}
        for field in CONTEXT_FIELDS:
            setattr(record, field, context.get(field))
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line, UTF-8 text kept as is (no `\\u` escapes)."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            **{field: getattr(record, field, None) for field in CONTEXT_FIELDS},
            "logger": record.name,
            "msg": record.getMessage(),
            "extra": _extra_fields(record),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return jsonlib.dumps(entry, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable line: `<ts> LEVEL [step] message key=value ...`."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, UTC).strftime("%H:%M:%S")
        step = getattr(record, "step", None)
        parts = [ts, f"{record.levelname:<7}"]
        if step:
            parts.append(f"[{step}]")
        parts.append(record.getMessage())
        parts.extend(f"{key}={value}" for key, value in _extra_fields(record).items())
        line = " ".join(parts)
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def logging_setup(
    level: str | int = "INFO", json: bool = False, stream: IO[str] | None = None
) -> logging.Logger:
    """Configure the `ilm_engine` logger (idempotent: replaces handlers set by an earlier call)."""
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonFormatter() if json else TextFormatter())
    handler.addFilter(_ContextFilter())
    logger.addHandler(handler)
    logger.setLevel(level.upper() if isinstance(level, str) else level)
    logger.propagate = False
    return logger


def _extra_fields(record: logging.LogRecord) -> dict[str, Any]:
    return {
        key: value
        for key, value in sorted(vars(record).items())
        if key not in _RECORD_ATTRS and key not in CONTEXT_FIELDS
    }
