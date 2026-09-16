"""Guard semantic equivalence of fixed-registry inspection optimizations."""
from __future__ import annotations

import random
import string
from types import MethodType
from unittest.mock import patch

import pytest
from presidio_analyzer import AnalyzerEngine

from asr_proxy.inspection.contracts import InspectionConfig, InspectionError
from asr_proxy.inspection.pii import PresidioScanner
from asr_proxy.inspection.protocol import check_egress


@pytest.fixture(scope="module")
def scanner():
  return PresidioScanner()


def test_marker_free_ascii_avoids_fixed_recognizer_work(scanner):
  with patch.object(AnalyzerEngine, "analyze", side_effect=AssertionError("unnecessary recognition")):
    assert scanner.analyze("content-type application/json notes.read synthetic benchmark text") == []


def test_prerequisite_filter_matches_unoptimized_six_language_pipeline(scanner):
  rng = random.Random(20260916)
  alphabet = "".join(c for c in string.printable if c not in "@0123456789")
  samples = ["".join(rng.choices(alphabet, k=length)) for length in [1, 20, 100, 1024] for _ in range(10)]
  samples += [
    "synthetic benchmark text " * 2622,
    "pilot@example.com", "+1 415-555-2671", "4111 1111 1111 1111",
    "GB82 WEST 1234 5698 7654 32", "219-09-9999",
    "주민등록번호 900101-1234567", "외국인등록번호 900101-5234567",
    "11-20-123456-78", "M123A4567", "123-45-67891",
    "居民身份证 999999199001011238", "手机 +86 138 0013 8000",
    "マイナンバー 123456789018", "電話 090-1234-5678",
    "DNI 12345678Z", "NIE X1234567L", "Pasaporte AAA000000",
    "Téléphone +33 6 12 34 56 78", "1 99 01 99 999 999 79",
    "１２３４５６７８９０", "١٢٣٤٥٦٧٨٩٠", "김민수", "電話", "école",
    "a@example.com " + "synthetic text " * 4096,
  ]
  for text in samples:
    actual = scanner.analyze(text)
    with patch.object(scanner._analyzer, "analyze", MethodType(AnalyzerEngine.analyze, scanner._analyzer)):
      assert actual == scanner.analyze(text)


@pytest.mark.parametrize("text", ["a@example.com", "123456789", "１２３", "電話"])
def test_candidates_and_unicode_still_use_complete_pipeline(scanner, text):
  with patch.object(AnalyzerEngine, "analyze", wraps=MethodType(AnalyzerEngine.analyze, scanner._analyzer)) as analyze:
    scanner.analyze(text)
    assert analyze.call_count == 6


@pytest.mark.parametrize("control", [chr(i) for i in range(32)] + [chr(127)])
def test_control_obfuscated_egress_stays_blocked(control):
  config = InspectionConfig.model_validate({"edition": "community", "routes": []})
  with pytest.raises(InspectionError, match="ambiguous_nested_url"):
    check_egress({"url": "ht" + control + "tps://example.com"}, config)
