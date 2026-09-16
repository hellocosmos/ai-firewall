from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ScanPattern:
    name: str
    regex: re.Pattern[str]
    severity: int
    description: str


DEFAULT_PATTERNS: tuple[ScanPattern, ...] = (
    ScanPattern(
        name="prompt_injection",
        regex=re.compile(r"ignore\s+(all|any|previous|prior)\s+instructions", re.IGNORECASE),
        severity=2,
        description="Prompt-injection style instruction override detected.",
    ),
    ScanPattern(
        name="system_prompt_exfil",
        regex=re.compile(r"reveal\s+(the\s+)?(system|developer)\s+prompt", re.IGNORECASE),
        severity=2,
        description="Prompt asks to reveal hidden system or developer instructions.",
    ),
    ScanPattern(
        name="hidden_html_comment",
        regex=re.compile(r"<!--.*?-->", re.IGNORECASE | re.DOTALL),
        severity=1,
        description="Hidden HTML comment detected in payload.",
    ),
    ScanPattern(
        name="invisible_unicode",
        regex=re.compile(r"[\u200b-\u200f\u2060\ufeff]"),
        severity=1,
        description="Invisible unicode characters detected in payload.",
    ),
    ScanPattern(
        name="base64_blob",
        regex=re.compile(r"(?:[A-Za-z0-9+/]{40,}={0,2})"),
        severity=1,
        description="Large base64-like blob detected in payload.",
    ),
    ScanPattern(
        name="exfil_instruction",
        regex=re.compile(
            r"(send|post|upload|email)\s+.*?(secret|credential|token|prompt|file)",
            re.IGNORECASE,
        ),
        severity=2,
        description="Outbound exfiltration-style instruction detected.",
    ),
)
