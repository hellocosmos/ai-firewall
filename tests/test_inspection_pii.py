from __future__ import annotations

import importlib.util
import logging
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from asr_proxy.inspection import pii
from asr_proxy.inspection.pii import (
  PiiFinding,
  PiiInitializationError,
  PiiInspectionError,
  PresidioScanner,
)


def _result(entity: str, start: int, end: int, score: float = 0.9) -> SimpleNamespace:
  return SimpleNamespace(entity_type=entity, start=start, end=end, score=score)


class _Analyzer:
  def __init__(self, responses: dict[str, object]) -> None:
    self.responses = responses
    self.calls: list[dict[str, object]] = []

  def analyze(self, **kwargs: object) -> object:
    self.calls.append(kwargs)
    response = self.responses.get(str(kwargs["language"]), [])
    if isinstance(response, Exception):
      raise response
    return response


def _scanner(monkeypatch: pytest.MonkeyPatch, responses: dict[str, object]) -> PresidioScanner:
  analyzer = _Analyzer(responses)
  monkeypatch.setattr(pii, "_create_analyzer", lambda *_: analyzer)
  return PresidioScanner()


def test_initialization_failure_is_explicit_and_does_not_expose_exception(monkeypatch):
  def fail(*_):
    raise ImportError("private payload must not appear")

  monkeypatch.setattr(pii, "_create_analyzer", fail)
  with pytest.raises(PiiInitializationError) as error:
    PresidioScanner()
  assert "private payload" not in str(error.value)
  assert error.value.__suppress_context__ is True


def test_wrong_dependency_version_is_not_silently_used(monkeypatch):
  monkeypatch.setattr(pii, "version", lambda _: "0.0.0")
  with pytest.raises(PiiInitializationError):
    PresidioScanner()


@pytest.mark.parametrize("threshold", [0, -1, 1.1, float("nan"), float("inf"), True, "0.4"])
def test_invalid_threshold_is_rejected(threshold):
  with pytest.raises(ValueError):
    PresidioScanner(score_threshold=threshold)


@pytest.mark.parametrize("timeout", [0, -1, 6, float("nan"), float("inf"), True, "0.1"])
def test_invalid_regex_timeout_is_rejected(timeout):
  with pytest.raises(ValueError):
    PresidioScanner(regex_timeout_seconds=timeout)


@pytest.mark.parametrize("during_iteration", [False, True])
def test_regex_timeout_is_not_the_swallowed_upstream_exception(during_iteration):
  class TimedOutRegex:
    def finditer(self, *_, **kwargs):
      assert kwargs["timeout"] == 0.1
      if not during_iteration:
        raise TimeoutError("private payload must not appear")

      def iterator():
        raise TimeoutError("private payload must not appear")
        yield

      return iterator()

  compiled = pii._FailClosedRegex(TimedOutRegex(), 0.1)
  with pytest.raises(PiiInspectionError) as error:
    list(compiled.finditer("private payload must not appear", timeout=60))
  assert "private payload" not in str(error.value)


def test_all_six_languages_are_inspected_without_decision_trace(monkeypatch):
  scanner = _scanner(monkeypatch, {"en": [_result("EMAIL_ADDRESS", 1, 4)], "ko": [_result("KR_RRN", 4, 8)]})
  findings = scanner.analyze("abcdefghij")
  assert [finding.entity_type for finding in findings] == ["EMAIL_ADDRESS", "KR_RRN"]
  assert [call["language"] for call in scanner._analyzer.calls] == ["en", "ko", "zh", "ja", "es", "fr"]
  assert all(call["return_decision_process"] is False for call in scanner._analyzer.calls)
  assert set(asdict(findings[0])) == {"entity_type", "start", "end", "score"}


def test_partial_language_failure_does_not_return_partial_success(monkeypatch):
  scanner = _scanner(monkeypatch, {"en": [_result("EMAIL_ADDRESS", 0, 4)], "ko": RuntimeError("private payload")})
  with pytest.raises(PiiInspectionError) as error:
    scanner.analyze("abcdefghij")
  assert "private payload" not in str(error.value)


@pytest.mark.parametrize("result", [
  _result("EMAIL_ADDRESS", -1, 2),
  _result("EMAIL_ADDRESS", 1, 1),
  _result("EMAIL_ADDRESS", 1, 20),
  _result("EMAIL_ADDRESS", True, 2),
  _result("EMAIL_ADDRESS", 0, 2, float("nan")),
  _result("EMAIL_ADDRESS", 0, 2, 1.1),
  _result("UNCONFIGURED_ENTITY", 0, 2),
  _result("<script>", 0, 2),
])
def test_invalid_or_unconfigured_results_fail_closed(monkeypatch, result):
  scanner = _scanner(monkeypatch, {"en": [result]})
  with pytest.raises(PiiInspectionError):
    scanner.redact("abcdefghij")


def test_duplicate_spans_keep_highest_score_and_low_confidence_is_preserved(monkeypatch):
  scanner = _scanner(monkeypatch, {
    "en": [_result("EMAIL_ADDRESS", 0, 2, 0.5), _result("EMAIL_ADDRESS", 0, 2, 0.9)],
    "ko": [_result("KR_PASSPORT", 3, 6, 0.05)],
  })
  assert scanner.analyze("abcdefghij") == [
    PiiFinding("EMAIL_ADDRESS", 0, 2, 0.9), PiiFinding("KR_PASSPORT", 3, 6, 0.05),
  ]


def test_below_threshold_result_is_not_returned(monkeypatch):
  scanner = _scanner(monkeypatch, {"en": [_result("EMAIL_ADDRESS", 0, 2, 0.3)]})
  assert scanner.analyze("abcd") == []


def test_partially_overlapping_spans_are_fully_redacted(monkeypatch):
  scanner = _scanner(monkeypatch, {
    "en": [_result("EMAIL_ADDRESS", 1, 5), _result("PHONE_NUMBER", 3, 8)],
    "ko": [_result("KR_RRN", 7, 10)],
  })
  redacted, findings = scanner.redact("0123456789ABC")
  assert redacted == "0<redacted:PII>ABC"
  assert len(findings) == 3


def test_unicode_offsets_and_adjacent_spans_preserve_other_characters(monkeypatch):
  scanner = _scanner(monkeypatch, {"en": [_result("EMAIL_ADDRESS", 2, 4), _result("PHONE_NUMBER", 4, 6)]})
  redacted, _ = scanner.redact("한글ab12끝")
  assert redacted == "한글<redacted:EMAIL_ADDRESS><redacted:PHONE_NUMBER>끝"


def test_empty_clean_and_nonstring_inputs(monkeypatch):
  scanner = _scanner(monkeypatch, {})
  assert scanner.redact("") == ("", [])
  assert scanner._analyzer.calls == []
  assert scanner.redact("safe model gpt-4.1-mini-2025-04-14") == ("safe model gpt-4.1-mini-2025-04-14", [])
  with pytest.raises(TypeError):
    scanner.analyze(123456789)


def test_health_is_configuration_only_and_returns_independent_collections(monkeypatch):
  scanner = _scanner(monkeypatch, {})
  metadata = scanner.health()
  assert metadata["network_required"] is False
  assert metadata["ner_enabled"] is False
  metadata["entities"].clear()
  assert scanner.health()["languages"] == ["en", "ko", "zh", "ja", "es", "fr"]
  assert len(scanner.health()["entities"]) == 16
  assert "text" not in metadata


@pytest.fixture(scope="module")
def real_scanner():
  if importlib.util.find_spec("presidio_analyzer") is None:
    pytest.skip("optional Presidio dependency is not installed")
  return PresidioScanner()


@pytest.mark.parametrize(("text", "entity"), [
  ("Send to pilot@example.com", "EMAIL_ADDRESS"),
  ("/mcp?email=pilot@example.com", "EMAIL_ADDRESS"),
  ("/path/pilot@example.com", "EMAIL_ADDRESS"),
  ("Call +1 415-555-2671", "PHONE_NUMBER"),
  ("전화번호 010-1234-5678", "PHONE_NUMBER"),
  ("Card 4111 1111 1111 1111", "CREDIT_CARD"),
  ("IBAN GB82 WEST 1234 5698 7654 32", "IBAN_CODE"),
  ("SSN 219-09-9999", "US_SSN"),
  ("주민등록번호 900101-1234567", "KR_RRN"),
  ("외국인등록번호 900101-5234567", "KR_FRN"),
  ("운전면허번호 11-20-123456-78", "KR_DRIVER_LICENSE"),
  ("여권 M123A4567", "KR_PASSPORT"),
  ("여권 M12345678", "KR_PASSPORT"),
  ("사업자등록번호 123-45-67891", "KR_BRN"),
  ("居民身份证 999999199001011238", "CN_RESIDENT_ID"),
  ("手机 +86 138 0013 8000", "PHONE_NUMBER"),
  ("マイナンバー 123456789018", "JP_MY_NUMBER"),
  ("電話 090-1234-5678", "PHONE_NUMBER"),
  ("DNI 12345678Z", "ES_NIF"),
  ("NIE X1234567L", "ES_NIE"),
  ("Pasaporte AAA000000", "ES_PASSPORT"),
  ("Teléfono +34 612 34 56 78", "PHONE_NUMBER"),
  ("Numéro de sécurité sociale 1 99 01 99 999 999 79", "FR_NIR"),
  ("NIR Corse 1 99 01 2A 999 999 08", "FR_NIR"),
  ("Téléphone +33 6 12 34 56 78", "PHONE_NUMBER"),
])
def test_real_recognizer_fixture_and_redaction(real_scanner, text, entity):
  findings = real_scanner.analyze(text)
  assert entity in {finding.entity_type for finding in findings}
  redacted, _ = real_scanner.redact(text)
  assert redacted != text
  for finding in findings:
    assert text[finding.start:finding.end] not in redacted


@pytest.mark.parametrize(("text", "entity"), [
  ("居民身份证 999999199001011239", "CN_RESIDENT_ID"),
  ("居民身份证 999999199013011238", "CN_RESIDENT_ID"),
  ("マイナンバー 123456789019", "JP_MY_NUMBER"),
  ("DNI 12345678A", "ES_NIF"),
  ("NIE X1234567A", "ES_NIE"),
  ("Numéro de sécurité sociale 1 99 01 99 999 999 78", "FR_NIR"),
])
def test_real_invalid_national_identifier_is_not_accepted(real_scanner, text, entity):
  assert entity not in {finding.entity_type for finding in real_scanner.analyze(text)}


def test_real_no_general_ner_or_date_claim(real_scanner):
  assert real_scanner.analyze("김민수 lives at Seoul. Model gpt-4.1-mini-2025-04-14.") == []
  assert "PERSON" not in real_scanner.health()["entities"]
  assert "LOCATION" not in real_scanner.health()["entities"]


def test_real_low_confidence_passport_score_is_not_inflated(real_scanner):
  findings = real_scanner.analyze("M12345678")
  passport = [finding for finding in findings if finding.entity_type == "KR_PASSPORT"]
  assert passport[0].score == 0.05


def test_real_upstream_regex_timeout_is_not_silently_skipped(real_scanner):
  class TimedOutRegex:
    def finditer(self, *_, **__):
      raise TimeoutError("private payload")

  scanner = PresidioScanner()
  email = scanner._analyzer.registry.recognizers[0]
  email.patterns[0].compiled_regex = pii._FailClosedRegex(TimedOutRegex(), 0.1)
  with pytest.raises(PiiInspectionError):
    scanner.analyze("synthetic@example.com")
  # Instance-local pattern copies prevent injected errors from affecting other scanners.
  assert real_scanner.analyze("synthetic@example.com")


def test_real_constructor_and_scan_do_not_fetch_or_log_input(monkeypatch, caplog):
  if importlib.util.find_spec("presidio_analyzer") is None:
    pytest.skip("optional Presidio dependency is not installed")
  import requests
  import spacy

  def forbidden(*_, **__):
    pytest.fail("PII inspection attempted network access or an NLP model load")

  monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
  monkeypatch.setattr(spacy, "load", forbidden)
  monkeypatch.setattr(spacy.cli, "download", forbidden)
  caplog.set_level(logging.DEBUG)
  scanner = PresidioScanner()
  assert scanner.analyze("offline-only-synthetic@example.com")
  assert "offline-only-synthetic" not in caplog.text
  assert scanner._analyzer.nlp_engine.engine_name == "no_op"
