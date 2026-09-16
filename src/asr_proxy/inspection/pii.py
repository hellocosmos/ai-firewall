"""모델 다운로드 없이 실행하는 선택적 Presidio PII 어댑터."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from importlib.metadata import version
from typing import Any

PRESIDIO_VERSION = "2.2.364"
LANGUAGE_ENTITIES: dict[str, tuple[str, ...]] = {
  "en": ("EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "IBAN_CODE", "US_SSN"),
  "ko": ("KR_RRN", "KR_FRN", "KR_DRIVER_LICENSE", "KR_PASSPORT", "KR_BRN"),
}
_ENTITY_LABEL = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")


class PiiInitializationError(RuntimeError):
  """선택한 검사기를 사용할 수 없음. 호출자는 조용히 우회하지 않아야 한다."""


class PiiInspectionError(RuntimeError):
  """검사가 완료되지 않음. 오류 메시지에 입력 원문을 포함하지 않는다."""


@dataclass(frozen=True, slots=True)
class PiiFinding:
  """원문을 담지 않는 Python 문자열 문자 단위 구간."""

  entity_type: str
  start: int
  end: int
  score: float

  def __post_init__(self) -> None:
    if not isinstance(self.entity_type, str) or not _ENTITY_LABEL.fullmatch(self.entity_type):
      raise ValueError("Invalid PII entity label")
    if type(self.start) is not int or type(self.end) is not int or not 0 <= self.start < self.end:
      raise ValueError("Invalid PII finding span")
    if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
      raise ValueError("Invalid PII finding score")  # noqa: TRY004 - uniform invalid-finding contract
    if not math.isfinite(self.score) or not 0 <= self.score <= 1:
      raise ValueError("Invalid PII finding score")


class _FailClosedRegex:
  """Presidio가 TimeoutError를 삼켜 부분 성공으로 반환하지 못하도록 한다."""

  def __init__(self, compiled: Any, timeout_seconds: float) -> None:
    self._compiled = compiled
    self._timeout_seconds = timeout_seconds

  def finditer(self, text: str, **kwargs: Any) -> Any:
    kwargs["timeout"] = self._timeout_seconds
    try:
      yield from self._compiled.finditer(text, **kwargs)
    except TimeoutError:
      raise PiiInspectionError("PII pattern inspection timed out") from None


def _create_analyzer(
  score_threshold: float,
  passport_score_threshold: float,
  regex_timeout_seconds: float,
) -> Any:
  # optional dependency는 선택 시점에만 로드한다. 전역 SDK monkey patch는 하지 않는다.
  if version("presidio-analyzer") != PRESIDIO_VERSION:
    raise PiiInitializationError("Unsupported Presidio analyzer version")

  import regex as timed_regex
  from presidio_analyzer import AnalyzerEngine, Pattern, RecognizerRegistry
  from presidio_analyzer.nlp_engine import NoOpNlpEngine
  from presidio_analyzer.predefined_recognizers import (
    CreditCardRecognizer,
    EmailRecognizer,
    IbanRecognizer,
    KrBrnRecognizer,
    KrDriverLicenseRecognizer,
    KrFrnRecognizer,
    KrPassportRecognizer,
    KrRrnRecognizer,
    PhoneRecognizer,
    UsSsnRecognizer,
  )
  from tldextract import TLDExtract

  class OfflineEmailRecognizer(EmailRecognizer):
    # tldextract 기본 인스턴스의 최초 실행 네트워크 요청/캐시 쓰기를 금지한다.
    def __init__(self) -> None:
      super().__init__(supported_language="en")
      self._offline_extract = TLDExtract(suffix_list_urls=(), cache_dir=None)
      self._offline_extract("example.com")

    def validate_result(self, pattern_text: str) -> bool:
      # RFC local-part의 / ? = 등을 URL 경로로 해석하여 이메일을 누락하지 않는다.
      domain = pattern_text.rsplit("@", 1)[-1]
      return self._offline_extract(domain).fqdn != ""

  recognizers = [
    OfflineEmailRecognizer(),
    PhoneRecognizer(
      supported_language="en",
      supported_regions=(*PhoneRecognizer.DEFAULT_SUPPORTED_REGIONS, "KR"),
    ),
    CreditCardRecognizer(supported_language="en"),
    IbanRecognizer(supported_language="en"),
    UsSsnRecognizer(supported_language="en"),
    KrRrnRecognizer(supported_language="ko"),
    KrFrnRecognizer(supported_language="ko"),
    KrDriverLicenseRecognizer(supported_language="ko"),
    KrPassportRecognizer(supported_language="ko"),
    KrBrnRecognizer(supported_language="ko"),
  ]
  for recognizer in recognizers:
    thresholds = {"default": score_threshold}
    if "KR_PASSPORT" in recognizer.supported_entities:
      thresholds["KR_PASSPORT"] = passport_score_threshold
    recognizer.score_thresholds = thresholds
    if hasattr(recognizer, "patterns"):
      # upstream 클래스 공유 PATTERNS를 바꾸지 않고 이 인스턴스만 소유한다.
      recognizer.patterns = [
        Pattern(name=pattern.name, regex=pattern.regex, score=pattern.score)
        for pattern in recognizer.patterns
      ]
      for pattern in recognizer.patterns:
        flags = recognizer.global_regex_flags
        pattern.compiled_regex = _FailClosedRegex(
          timed_regex.compile(pattern.regex, flags=flags), regex_timeout_seconds,
        )
        pattern.compiled_with_flags = flags
    recognizer.load()
    recognizer.is_loaded = True

  languages = list(LANGUAGE_ENTITIES)
  registry = RecognizerRegistry(recognizers=recognizers, supported_languages=languages)
  nlp_engine = NoOpNlpEngine(
    models=[{"lang_code": language, "model_name": ""} for language in languages],
  )
  return AnalyzerEngine(
    registry=registry,
    nlp_engine=nlp_engine,
    supported_languages=languages,
    default_score_threshold=score_threshold,
    log_decision_process=False,
  )


class PresidioScanner:
  """en/ko의 명시적 패턴·검증기만 사용하며 NER·비밀 탐지기를 대체하지 않는다."""

  def __init__(
    self,
    *,
    score_threshold: float = 0.4,
    passport_score_threshold: float = 0.05,
    regex_timeout_seconds: float = 0.1,
  ) -> None:
    for threshold in (score_threshold, passport_score_threshold):
      if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not math.isfinite(threshold)
        or not 0 < threshold <= 1
      ):
        raise ValueError("PII score thresholds must be finite and in (0, 1]")
    if (
      isinstance(regex_timeout_seconds, bool)
      or not isinstance(regex_timeout_seconds, (int, float))
      or not math.isfinite(regex_timeout_seconds)
      or not 0 < regex_timeout_seconds <= 5
    ):
      raise ValueError("PII regex timeout must be finite and in (0, 5] seconds")
    self._score_threshold = float(score_threshold)
    self._passport_score_threshold = float(passport_score_threshold)
    self._regex_timeout_seconds = float(regex_timeout_seconds)
    try:
      self._analyzer = _create_analyzer(
        self._score_threshold, self._passport_score_threshold, self._regex_timeout_seconds,
      )
    except Exception:  # noqa: BLE001 - sanitize optional backend initialization failures
      # import/초기화 예외 문자열이나 traceback context를 외부 응답에 전달하지 않는다.
      raise PiiInitializationError(
        "Presidio PII initialization failed; install the pinned pii dependency and check configuration"
      ) from None

  def health(self) -> dict[str, Any]:
    """초기화 구성 정보만 반환하며 입력이나 최근 탐지 결과를 보관하지 않는다."""
    return {
      "backend": "presidio",
      "version": PRESIDIO_VERSION,
      "initialized": True,
      "nlp_engine": "no_op",
      "ner_enabled": False,
      "network_required": False,
      "languages": list(LANGUAGE_ENTITIES),
      "entities": sorted(entity for entities in LANGUAGE_ENTITIES.values() for entity in entities),
      "score_threshold": self._score_threshold,
      "entity_score_thresholds": {"KR_PASSPORT": self._passport_score_threshold},
      "regex_timeout_seconds": self._regex_timeout_seconds,
    }

  def analyze(self, text: str) -> list[PiiFinding]:
    if not isinstance(text, str):
      raise TypeError("PII inspection requires a string")
    if not text:
      return []

    findings: dict[tuple[str, int, int], PiiFinding] = {}
    try:
      for language, entities in LANGUAGE_ENTITIES.items():
        results = self._analyzer.analyze(
          text=text,
          language=language,
          entities=list(entities),
          return_decision_process=False,
        )
        for result in results:
          finding = PiiFinding(result.entity_type, result.start, result.end, result.score)
          if finding.entity_type not in entities or finding.end > len(text):
            raise ValueError("Unexpected PII recognizer result")
          threshold = (
            self._passport_score_threshold if finding.entity_type == "KR_PASSPORT"
            else self._score_threshold
          )
          if finding.score < threshold:
            continue
          key = (finding.entity_type, finding.start, finding.end)
          if key not in findings or findings[key].score < finding.score:
            findings[key] = finding
    except Exception:  # noqa: BLE001 - partial recognizer success must never fail open
      # 중간 언어 검사 결과를 성공으로 반환하지 않는다.
      raise PiiInspectionError("Presidio PII inspection did not complete") from None
    return sorted(findings.values(), key=lambda finding: (finding.start, finding.end, finding.entity_type))

  def redact(self, text: str) -> tuple[str, list[PiiFinding]]:
    findings = self.analyze(text)
    if not findings:
      return text, []

    # 겹치는 구간 전체를 합쳐 부분 중첩 결과의 후반 원문이 남는 것을 막는다.
    spans: list[tuple[int, int, set[str]]] = []
    for finding in findings:
      if spans and finding.start < spans[-1][1]:
        start, end, labels = spans[-1]
        spans[-1] = (start, max(end, finding.end), labels | {finding.entity_type})
      else:
        spans.append((finding.start, finding.end, {finding.entity_type}))
    chunks: list[str] = []
    cursor = 0
    for start, end, labels in spans:
      chunks.append(text[cursor:start])
      label = next(iter(labels)) if len(labels) == 1 else "PII"
      chunks.append(f"<redacted:{label}>")
      cursor = end
    chunks.append(text[cursor:])
    return "".join(chunks), findings
