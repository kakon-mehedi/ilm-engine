import io
import json
import logging

import pytest
from typer.testing import CliRunner

from ilm_engine.cli import app
from ilm_engine.log import LOGGER_NAME, JsonFormatter, get_logger, log_context, logging_setup


@pytest.fixture
def stream():
    buffer = io.StringIO()
    logging_setup("DEBUG", json=True, stream=buffer)
    yield buffer
    logging_setup("INFO")


def lines(buffer: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in buffer.getvalue().splitlines()]


def test_one_json_object_per_line_with_context(stream):
    log = get_logger("processors.origin")
    with log_context(run_id="run_0123456789ab", step="origin", pub_ref="pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"):
        log.info("origin assigned", extra={"block_id": "b000098", "origin": "author_text"})
        log.warning("override applied")
    records = lines(stream)
    assert len(records) == 2
    first = records[0]
    assert set(first) == {"ts", "level", "run_id", "step", "pub_ref", "logger", "msg", "extra"}
    assert first["run_id"] == "run_0123456789ab"
    assert first["step"] == "origin"
    assert first["pub_ref"] == "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
    assert first["level"] == "INFO"
    assert first["logger"] == "ilm_engine.processors.origin"
    assert first["msg"] == "origin assigned"
    assert first["extra"] == {"block_id": "b000098", "origin": "author_text"}
    assert first["ts"].endswith("+00:00")
    assert records[1]["level"] == "WARNING" and records[1]["extra"] == {}


def test_context_fields_null_when_unset(stream):
    get_logger().info("no context")
    record = lines(stream)[0]
    assert record["run_id"] is None and record["step"] is None and record["pub_ref"] is None


def test_nested_context_overrides_and_restores(stream):
    log = get_logger()
    with log_context(run_id="run_a", step="adapt"):
        with log_context(step="structure"):
            log.info("inner")
        log.info("outer")
    log.info("outside")
    inner, outer, outside = lines(stream)
    assert (inner["run_id"], inner["step"]) == ("run_a", "structure")
    assert (outer["run_id"], outer["step"]) == ("run_a", "adapt")
    assert outside["run_id"] is None


def test_arabic_is_utf8_not_escaped(stream):
    get_logger().info("entry detected", extra={"quote": "أسلمت"})
    raw = stream.getvalue()
    assert "أسلمت" in raw
    assert "\\u" not in raw
    assert lines(stream)[0]["extra"]["quote"] == "أسلمت"


def test_exception_included(stream):
    try:
        raise ValueError("bad block")
    except ValueError:
        get_logger().exception("step failed")
    record = lines(stream)[0]
    assert record["level"] == "ERROR"
    assert "ValueError: bad block" in record["exc"]


def test_non_serializable_extra_falls_back_to_str():
    record = logging.LogRecord(LOGGER_NAME, logging.INFO, __file__, 1, "msg", None, None)
    record.path = object()
    assert json.loads(JsonFormatter().format(record))["extra"]["path"].startswith("<object")


def test_unknown_context_field_rejected():
    with pytest.raises(ValueError, match="unknown log context field"):
        with log_context(book="x"):
            pass


def test_level_filters_records():
    buffer = io.StringIO()
    logging_setup("WARNING", json=True, stream=buffer)
    get_logger().info("hidden")
    get_logger().warning("shown")
    assert [record["msg"] for record in lines(buffer)] == ["shown"]
    logging_setup("INFO")


def test_setup_is_idempotent():
    buffer = io.StringIO()
    logging_setup("INFO", json=True, stream=buffer)
    logging_setup("INFO", json=True, stream=buffer)
    get_logger().info("once")
    assert len(lines(buffer)) == 1
    assert len(logging.getLogger(LOGGER_NAME).handlers) == 1
    logging_setup("INFO")


def test_text_format_is_human_readable():
    buffer = io.StringIO()
    logging_setup("INFO", json=False, stream=buffer)
    with log_context(step="structure"):
        get_logger().info("sections built", extra={"count": 15})
    line = buffer.getvalue().strip()
    assert "INFO" in line and "[structure]" in line and "sections built" in line and "count=15" in line
    logging_setup("INFO")


def test_cli_accepts_log_json_flag():
    result = CliRunner().invoke(app, ["--log-json", "--log-level", "DEBUG", "version"])
    assert result.exit_code == 0, result.output
    assert logging.getLogger(LOGGER_NAME).level == logging.DEBUG
    assert isinstance(logging.getLogger(LOGGER_NAME).handlers[0].formatter, JsonFormatter)
    logging_setup("INFO")
