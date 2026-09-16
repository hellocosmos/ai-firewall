"""Optional Presidio PII adapter without model downloads."""

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
  """The selected scanner is unavailable; callers must not silently bypass it."""


class PiiInspectionError(RuntimeError):
  """Inspection is incomplete. Never include raw input in error messages."""


@dataclass(frozen=True, slots=True)
class PiiFinding:
  """Python character-index spans without original content."""

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
  """Prevent Presidio from swallowing TimeoutError and returning partial success."""

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
  # Load the optional dependency only when selected; do not monkey-patch global SDK state.
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
    # Disable initial network requests and cache writes in the default tldextract instance.
    def __init__(self) -> None:
      super().__init__(supported_language="en")
      self._offline_extract = TLDExtract(suffix_list_urls=(), cache_dir=None)
      self._offline_extract("example.com")

    def validate_result(self, pattern_text: str) -> bool:
      # Do not misinterpret RFC local-part characters such as / ? = as URL paths.
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
      # Own instance-local patterns without changing the upstream class PATTERNS.
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
  """Use explicit en/ko patterns and validators; this does not replace NER or secret detection."""

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
      # Do not expose import or initialization exception strings or traceback context.
      raise PiiInitializationError(
        "Presidio PII initialization failed; install the pinned pii dependency and check configuration"
      ) from None

  def health(self) -> dict[str, Any]:
    """Return initialization configuration only; retain no input or recent findings."""
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
      # Do not return intermediate language results as successful inspection.
      raise PiiInspectionError("Presidio PII inspection did not complete") from None
    return sorted(findings.values(), key=lambda finding: (finding.start, finding.end, finding.entity_type))

  def redact(self, text: str) -> tuple[str, list[PiiFinding]]:
    findings = self.analyze(text)
    if not findings:
      return text, []

    # Merge overlapping spans completely to avoid leaving a trailing part of the original content.
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
