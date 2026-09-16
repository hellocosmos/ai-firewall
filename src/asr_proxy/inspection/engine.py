from __future__ import annotations

from dataclasses import replace
from urllib.parse import parse_qsl, unquote, urlsplit

from .signatures import DEFAULT_PATTERNS

from .budget import check_deadline
from .authorization import AuthorizationRequest
from .contracts import HttpMessage, InspectionConfig, InspectionError, Verdict
from .identity import IDENTITY_FIELDS, AttestationVerifier, application_headers, request_digest
from .protocol import (
  check_egress,
  encode_json,
  iter_strings,
  route_for,
  semantics,
  strict_json,
  validate_message,
)
from .secret_detection import contains_secret


def field_allowed(path: tuple[str, ...], patterns: list[str]) -> bool:
  for pattern in patterns:
    parts = tuple(p.replace("~1", "/").replace("~0", "~") for p in pattern.split("/")[1:])
    if len(path) == len(parts) and all(rule == "*" or rule == value for rule, value in zip(parts, path)):
      return True
  return False


class InspectionEngine:
  def __init__(self, config: InspectionConfig, pii, verifier: AttestationVerifier, broker):
    self.config, self.pii, self.verifier, self.broker = config, pii, verifier, broker
    import regex
    # Own bounded copies: no global SDK rule changes and no uninterruptible stdlib regex.
    self.signature_patterns = [regex.compile(pattern.regex.pattern, pattern.regex.flags)
                               for pattern in DEFAULT_PATTERNS if pattern.severity >= 2]

  def _find(self, text):
    check_deadline()
    return [finding for finding in self.pii.analyze(text)
            if finding.score >= self.config.pii_min_score]

  def _signatures(self, value):
    if contains_secret(value):
      raise InspectionError("secret_detected")
    for text in iter_strings(value):
      check_deadline()
      try:
        if any(pattern.search(text, timeout=0.02) for pattern in self.signature_patterns):
          raise InspectionError("suspicious_instruction")
      except TimeoutError:
        raise InspectionError("signature_timeout") from None

  def _mask(self, text, findings):
    spans = []
    for finding in sorted(findings, key=lambda f: (f.start, f.end)):
      if spans and finding.start <= spans[-1][1]:
        spans[-1] = (spans[-1][0], max(spans[-1][1], finding.end))
      else:
        spans.append((finding.start, finding.end))
    for start, end in reversed(spans):
      text = text[:start] + "[REDACTED]" + text[end:]
    return text

  def _pii_policy(self, route=None, rule=None):
    if rule is not None and rule.pii_action is not None:
      return rule.pii_action, "tool"
    if route is not None and route.pii_action is not None:
      return route.pii_action, "route"
    return self.config.pii_action, "global"

  def inspect_metadata(self, message: HttpMessage, *, response: bool = False):
    # Credentials are transmitted only to the attested mapped destination, not redacted.
    # They are still bound to authorization; they are never copied into inspection audit.
    credentials = {"authorization", "proxy-authorization", "cookie", "x-api-key", "api-key",
                   "x-goog-api-key"}
    for key, value in application_headers(message.headers).items():
      if not response and key in credentials:
        continue
      self._signatures(value)
      if self._find(value):
        raise InspectionError("pii_in_http_header")
    if not response:
      parsed = urlsplit(message.path)
      candidates = [unquote(message.path), *[unquote(part) for part in parsed.path.split("/")]]
      try:
        for key, value in parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=256):
          candidates.extend((key, value))
      except ValueError:
        raise InspectionError("request_query_limit_exceeded") from None
      for candidate in candidates:
        self._signatures(candidate)
        if self._find(candidate):
          raise InspectionError("pii_in_request_target")

  def _redact_json(self, value, fields: list[str] | None, entities: list[str],
                   pii_action: str, path=()):
    if isinstance(value, dict):
      result = {}
      for key, child in value.items():
        if self._find(key):
          raise InspectionError("pii_in_structural_field")
        result[key] = self._redact_json(child, fields, entities, pii_action, (*path, key))
      return result
    if isinstance(value, list):
      return [self._redact_json(child, fields, entities, pii_action, (*path, str(i)))
              for i, child in enumerate(value)]
    if isinstance(value, str):
      findings = self._find(value)
      entities.extend(f.entity_type for f in findings)
      if findings:
        if pii_action == "block":
          raise InspectionError("pii_block_policy")
        if fields is not None and not field_allowed(path, fields):
          raise InspectionError("pii_in_nonredactable_field")
        return self._mask(value, findings)
    elif type(value) in (int, float) and self._find(str(value)):
      raise InspectionError("pii_in_numeric_field")
    return value

  def inspect_request(self, message: HttpMessage, *, mode: str) -> Verdict:
    verdict = Verdict("allow", "policy_allowed", mode)
    try:
      validate_message(message, self.config)
      route = route_for(message, self.config)
      self.inspect_metadata(message)
      if message.body and message.headers.get("content-type", "").split(";")[0].strip() not in (
        "application/json", "application/json-rpc",
      ):
        raise InspectionError("unsupported_request_media_type")
      value = strict_json(message.body, self.config.max_json_depth) if message.body else {}
      original_semantics = semantics(message, route, value)
      verdict.tool, verdict.access_action, _ = original_semantics
      rule = route.tools.get(original_semantics[0]) if route.protocol == "mcp" else route.rule
      verdict.pii_policy_action, verdict.pii_policy_scope = self._pii_policy(route, rule)
      if rule is not None and rule.effect == "block":
        raise InspectionError("local_policy_denied")
      self._signatures(value)
      check_egress(value, self.config)
      modified = self._redact_json(value, route.redact_fields, verdict.entities,
                                   verdict.pii_policy_action)
      # Only serialize when content actually changes; preserve original wire bytes otherwise.
      new_body = encode_json(modified) if modified != value else message.body
      if semantics(message, route, modified) != original_semantics:
        raise InspectionError("redaction_changed_authorized_action")
      final_message = replace(message, body=new_body)
      verdict.request_digest = request_digest(final_message)
      verdict.body = new_body if new_body != message.body else None
      identity = self.verifier.verify(message, consume=mode == "inline")
      if self.config.edition == "community":
        if identity.get("source_id") not in self.config.trusted_sources:
          raise InspectionError("untrusted_source")
        verdict.source_verified = True
        verdict.authorization_scope = "local_policy"
        if verdict.body is not None:
          verdict.action, verdict.reason = "redact", "pii_redacted"
        return verdict
      verdict.source_verified = True
      verdict.identity_verified = True
      request = AuthorizationRequest(
        **{key: identity[key] for key in IDENTITY_FIELDS},
        tool_name=original_semantics[0], requested_action=original_semantics[1],
        resource_id=original_semantics[2], approval_id=identity.get("approval_id"),
        agent_instance_id=identity.get("agent_instance_id"),
        metadata={"request_digest": verdict.request_digest},
      )
      check_deadline()
      decision = self.broker.authorize(request) if mode == "inline" else self.broker.evaluate(request)
      verdict.authorization_scope = "enterprise_broker"
      if decision.action != "allow":
        verdict.action = decision.action
        verdict.reason = decision.reason_code
        verdict.body = None
        if mode == "inline" and decision.approval:
          verdict.approval_id = decision.approval.approval_id
      elif verdict.body is not None:
        verdict.action, verdict.reason = "redact", "pii_redacted"
      return verdict
    except InspectionError as exc:
      reason = str(exc)
      if mode == "mirror" and reason in ("unmapped_route", "unmapped_tool", "unmapped_http_action"):
        return self._inspect_unmapped_mirror(message, reason)
      uncertain = reason in {"incomplete_capture", "body_limit_exceeded", "invalid_json",
                            "unsupported_content_encoding", "unsupported_request_media_type",
                            "untrusted_or_mismatched_identity", "unmapped_route", "unmapped_tool",
                            "inspection_deadline", "signature_timeout"}
      verdict.action = "unknown" if mode == "mirror" and uncertain else "block"
      verdict.reason = reason
      verdict.coverage = "incomplete" if uncertain else "complete"
      if mode == "mirror" and verdict.entities and reason == "untrusted_or_mismatched_identity":
        verdict.action, verdict.reason = "redact", "pii_detected_identity_unverified"
      verdict.body = None
      return verdict
    except Exception:  # noqa: BLE001 - fail closed for unknown backend errors
      # Scanner/store failures never permit original content, nor leak exception payloads.
      return Verdict("block" if mode == "inline" else "unknown", "inspection_unavailable", mode,
                     coverage="incomplete")

  def _inspect_unmapped_mirror(self, message: HttpMessage, reason: str) -> Verdict:
    """Missing action mapping does not suppress data findings; it still prevents access claims."""
    verdict = Verdict("unknown", reason, "mirror", coverage="incomplete",
                      pii_policy_action=self.config.pii_action, pii_policy_scope="global")
    try:
      validate_message(message, self.config)
      self.inspect_metadata(message)
      media = message.headers.get("content-type", "").split(";")[0].strip()
      if media in ("application/json", "application/json-rpc"):
        value = strict_json(message.body, self.config.max_json_depth)
      elif media == "text/plain":
        value = message.body.decode("utf-8")
      else:
        return verdict
      self._signatures(value)
      check_egress(value, self.config)
      self._redact_json(value, None, verdict.entities, self.config.pii_action)
      if verdict.entities:
        verdict.action, verdict.reason = "redact", "pii_detected_unmapped_context"
      try:
        identity = self.verifier.verify(message, consume=False)
        verdict.source_verified = self.config.edition == "enterprise" or identity.get("source_id") in self.config.trusted_sources
        verdict.identity_verified = self.config.edition == "enterprise"
      except InspectionError:
        pass
    except InspectionError as exc:
      verdict.action, verdict.reason = "block", str(exc)
    except Exception:  # noqa: BLE001 - never label a scanner failure clean
      verdict.action, verdict.reason = "unknown", "inspection_unavailable"
    return verdict

  def inspect_response(self, message: HttpMessage, *, mode: str, pii_action: str | None = None,
                       pii_policy_scope: str | None = None) -> Verdict:
    if pii_action is None:
      try:
        route = route_for(message, self.config)
      except InspectionError:
        route = None
      pii_action, pii_policy_scope = self._pii_policy(route)
    verdict = Verdict("allow", "response_clean", mode, pii_policy_action=pii_action,
                      pii_policy_scope=pii_policy_scope)
    try:
      validate_message(message, self.config)
      self.inspect_metadata(message, response=True)
      media = message.headers.get("content-type", "").split(";")[0].strip()
      if not message.body:
        return verdict
      if media in ("application/json", "application/json-rpc"):
        value = strict_json(message.body, self.config.max_json_depth)
        self._signatures(value)
        modified = self._redact_json(value, None, verdict.entities, pii_action)
        new_body = encode_json(modified) if modified != value else message.body
      elif media == "text/event-stream":
        new_body = self._redact_sse(message.body, verdict.entities, pii_action)
      elif media == "text/plain":
        value = message.body.decode("utf-8")
        self._signatures(value)
        findings = self._find(value)
        verdict.entities.extend(f.entity_type for f in findings)
        if findings and pii_action == "block":
          raise InspectionError("pii_block_policy")
        new_body = self._mask(value, findings).encode()
      else:
        raise InspectionError("unsupported_response_media_type")
      if new_body != message.body:
        verdict.action, verdict.reason, verdict.body = "redact", "response_pii_redacted", new_body
      return verdict
    except (InspectionError, UnicodeError) as exc:
      reason = str(exc) if isinstance(exc, InspectionError) else "invalid_utf8"
      complete_detection = reason in {
        "pii_block_policy", "secret_detected", "suspicious_instruction", "pii_in_http_header",
        "pii_in_structural_field", "pii_in_numeric_field", "pii_in_sse_metadata",
        "pii_in_sse_structural_field", "pii_in_nonredactable_field",
      }
      return Verdict("block" if mode == "inline" or complete_detection else "unknown", reason, mode,
                     entities=verdict.entities,
                     coverage="complete" if complete_detection else "incomplete",
                     pii_policy_action=pii_action, pii_policy_scope=pii_policy_scope)
    except Exception:  # noqa: BLE001 - never release an unchecked response
      return Verdict("block" if mode == "inline" else "unknown", "inspection_unavailable", mode,
                     coverage="incomplete", pii_policy_action=pii_action,
                     pii_policy_scope=pii_policy_scope)

  def _redact_sse(self, body: bytes, entities: list[str], pii_action: str) -> bytes:
    """Reassemble only complete, supported SSE streams; do not infer unknown delta semantics."""
    text = body.decode("utf-8").removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n\n"):
      raise InspectionError("incomplete_sse_event")
    if "\x00" in text:
      raise InspectionError("invalid_sse_control_character")
    events, lanes = [], {}
    family, terminal, anthropic_started = None, False, False
    anthropic_open, anthropic_seen = set(), set()
    structural = {"id", "type", "object", "model", "role", "name", "item_id",
                  "call_id", "tool_use_id", "finish_reason", "signature"}
    response_deltas = {"response.output_text.delta": "text",
                       "response.refusal.delta": "text",
                       "response.function_call_arguments.delta": "json"}
    response_static = {"response.created", "response.in_progress", "response.completed",
                       "response.failed", "response.output_item.added", "response.output_item.done",
                       "response.content_part.added", "response.content_part.done",
                       "response.output_text.done", "response.refusal.done",
                       "response.function_call_arguments.done"}
    anthropic_types = {"message_start", "content_block_start", "content_block_delta",
                       "content_block_stop", "message_delta", "message_stop", "ping"}

    def index(value):
      if type(value) is not int or not 0 <= value <= 1_000_000:
        raise InspectionError("invalid_sse_index")
      return str(value)

    def select_lane(value, path, ordinal):
      # Metadata is inspected separately; it must never interrupt a text delta lane.
      default = ("event", ordinal, *path), "structural" if path[-1] in structural else "text"
      if family == "chat" and len(path) >= 4 and path[0] == "choices" and path[2] == "delta":
        if path[3] in {"content", "refusal"} and len(path) == 4:
          return ("chat", path[1], path[3]), "text"
        if path[3] == "function_call" and path[-1] in {"name", "arguments"}:
          return ("chat", path[1], *path[3:]), "json" if path[-1] == "arguments" else "structural"
        if path[3] == "tool_calls" and path[-1] in {"name", "arguments", "id"}:
          return ("chat", path[1], *path[3:]), "json" if path[-1] == "arguments" else "structural"
      event_type = value.get("type")
      if family == "responses" and event_type in response_deltas and path == ("delta",):
        return ("responses", value["item_id"], index(value["output_index"]),
                str(value.get("content_index", "")), event_type), response_deltas[event_type]
      if family == "responses" and event_type == "response.output_item.added" and path == ("item", "arguments"):
        return ("responses", value["item"]["id"], index(value["output_index"]),
                "", "response.function_call_arguments.delta"), "json"
      if family == "responses" and event_type == "response.content_part.added" and path in (("part", "text"), ("part", "refusal")):
        delta_type = "response.output_text.delta" if path[-1] == "text" else "response.refusal.delta"
        return ("responses", value["item_id"], index(value["output_index"]),
                index(value["content_index"]), delta_type), "text"
      if family == "anthropic":
        if event_type == "content_block_delta" and len(path) == 2 and path[0] == "delta":
          field = path[1]
          if field in {"text", "thinking", "partial_json", "signature"}:
            kind = "json" if field == "partial_json" else "structural" if field in {"thinking", "signature"} else "text"
            return ("anthropic", index(value["index"]), field), kind
        if event_type == "content_block_start" and path in (("content_block", "text"), ("content_block", "thinking")):
          return ("anthropic", index(value["index"]), path[-1]), "structural" if path[-1] == "thinking" else "text"
      if family == "mcp" and len(path) == 4 and path[:2] == ("result", "content") and path[-1] == "text":
        return ("mcp", ordinal, "content_text"), "text"
      # Complete tool arguments are JSON inside a JSON string, not plain text.
      if path[-1] == "arguments" and (family in {"chat", "responses"}):
        return ("event", ordinal, *path), "json"
      return default

    def collect(value, event_value, ordinal, parent=None, key=None, path=()):
      if isinstance(value, dict):
        if value.get("type") in {"image", "audio", "redacted_thinking"} or "encrypted_content" in value:
          raise InspectionError("unsupported_sse_encoded_payload")
        for k, child in value.items():
          if k == "logprobs" and child is not None:
            # Token byte arrays are an alternate copy of the original unredacted output.
            raise InspectionError("unsupported_sse_encoded_payload")
          key_findings = self._find(k)
          if key_findings:
            entities.extend(f.entity_type for f in key_findings)
            raise InspectionError("pii_in_structural_field")
          collect(child, event_value, ordinal, value, k, (*path, k))
      elif isinstance(value, list):
        seen = set()
        for i, child in enumerate(value):
          if family == "chat" and path and path[-1] in {"choices", "tool_calls"}:
            if not isinstance(child, dict) or "index" not in child:
              raise InspectionError("invalid_sse_index")
            lane_index = index(child["index"])
            if lane_index in seen:
              raise InspectionError("duplicate_sse_index")
            seen.add(lane_index)
          else:
            lane_index = str(i)
          collect(child, event_value, ordinal, value, i, (*path, lane_index))
      elif isinstance(value, str):
        lane, kind = select_lane(event_value, path, ordinal)
        lanes.setdefault((lane, kind), []).append((parent, key, value))
      elif type(value) in (int, float):
        findings = self._find(str(value))
        if findings:
          entities.extend(f.entity_type for f in findings)
          raise InspectionError("pii_in_numeric_field")

    for ordinal, event in enumerate(text[:-2].split("\n\n")):
      lines, data_lines, metadata = event.split("\n"), [], {}
      for line in lines:
        field, separator, contents = line.partition(":")
        contents = contents.removeprefix(" ")
        if field == "data":
          data_lines.append(contents if separator else "")
          continue
        # Comments and ignored SSE fields are still bytes sent to the client.
        self._signatures(line)
        findings = self._find(line)
        if findings:
          entities.extend(f.entity_type for f in findings)
          raise InspectionError("pii_in_sse_metadata")
        if field not in {"", "event", "id", "retry"}:
          raise InspectionError("unsupported_sse_field")
        if field:
          if field in metadata:
            raise InspectionError("ambiguous_sse_metadata")
          metadata[field] = contents
        if field == "retry" and (not contents.isascii() or not contents.isdigit()):
          raise InspectionError("invalid_sse_retry")
      data = "\n".join(data_lines)
      if not data:
        events.append((lines, None))
        continue
      if terminal:
        raise InspectionError("sse_data_after_terminal")
      if data == "[DONE]":
        if family not in (None, "chat"):
          raise InspectionError("unexpected_sse_terminal")
        family, terminal = "chat", True
        events.append((lines, None))
        continue
      value = strict_json(data.encode(), self.config.max_json_depth)
      if not isinstance(value, dict):
        raise InspectionError("unsupported_sse_payload")
      self._signatures(value)
      event_type = value.get("type")
      if "choices" in value:
        current = "chat"
        if not isinstance(value["choices"], list) or value.get("object", "chat.completion.chunk") != "chat.completion.chunk":
          raise InspectionError("unsupported_sse_schema")
        for choice in value["choices"]:
          if not isinstance(choice, dict) or not isinstance(choice.get("delta"), dict):
            raise InspectionError("unsupported_sse_schema")
          delta = choice["delta"]
          if set(delta) - {"role", "content", "refusal", "function_call", "tool_calls"}:
            raise InspectionError("unsupported_sse_delta")
          if any(delta.get(k) is not None and not isinstance(delta[k], str) for k in ("content", "refusal", "role")):
            raise InspectionError("unsupported_sse_delta")
      elif event_type in response_deltas or event_type in response_static:
        current = "responses"
        if event_type in response_deltas:
          if not isinstance(value.get("delta"), str) or not isinstance(value.get("item_id"), str):
            raise InspectionError("unsupported_sse_delta")
          index(value.get("output_index"))
          if event_type != "response.function_call_arguments.delta":
            index(value.get("content_index"))
        if event_type == "response.output_item.added":
          item = value.get("item")
          if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise InspectionError("unsupported_sse_schema")
          index(value.get("output_index"))
          if item.get("type") == "message" and item.get("content", []) != []:
            raise InspectionError("unsupported_sse_initial_content")
        if event_type == "response.content_part.added":
          if not isinstance(value.get("item_id"), str) or not isinstance(value.get("part"), dict):
            raise InspectionError("unsupported_sse_schema")
          index(value.get("output_index"))
          index(value.get("content_index"))
        terminal = event_type in {"response.completed", "response.failed"}
      elif event_type in anthropic_types:
        current = "anthropic"
        if event_type == "message_start":
          if anthropic_started:
            raise InspectionError("unexpected_sse_message_start")
          anthropic_started = True
        elif event_type != "ping" and not anthropic_started:
          raise InspectionError("incomplete_sse_stream")
        if event_type.startswith("content_block_"):
          block_index = index(value.get("index"))
        if event_type == "content_block_start":
          block = value.get("content_block")
          if not isinstance(block, dict) or block.get("type") not in {"text", "thinking", "tool_use", "server_tool_use"}:
            raise InspectionError("unsupported_sse_content_block")
          if block_index in anthropic_seen:
            raise InspectionError("unexpected_sse_content_block")
          anthropic_open.add(block_index)
          anthropic_seen.add(block_index)
          if block.get("type") in {"tool_use", "server_tool_use"} and block.get("input", {}) != {}:
            raise InspectionError("unsupported_sse_initial_content")
        elif event_type in {"content_block_delta", "content_block_stop"}:
          if block_index not in anthropic_open:
            raise InspectionError("incomplete_sse_stream")
          if event_type == "content_block_stop":
            anthropic_open.remove(block_index)
        if event_type == "content_block_delta":
          delta = value.get("delta")
          delta_fields = {"text_delta": "text", "thinking_delta": "thinking",
                          "input_json_delta": "partial_json", "signature_delta": "signature"}
          if not isinstance(delta, dict) or delta.get("type") not in delta_fields:
            raise InspectionError("unsupported_sse_delta")
          delta_field = delta_fields[delta["type"]]
          if set(delta) != {"type", delta_field} or not isinstance(delta[delta_field], str):
            raise InspectionError("unsupported_sse_delta")
        terminal = event_type == "message_stop"
        if terminal and anthropic_open:
          raise InspectionError("incomplete_sse_stream")
      elif value.get("jsonrpc") == "2.0" and any(k in value for k in ("method", "result", "error")):
        current = "mcp"
      else:
        raise InspectionError("unsupported_sse_schema")
      if family is not None and family != current:
        raise InspectionError("mixed_sse_protocols")
      family = current
      if metadata.get("event", "message") not in {"message", event_type}:
        raise InspectionError("sse_event_type_mismatch")
      collect(value, value, ordinal)
      events.append((lines, value))
    if family in {"chat", "responses", "anthropic"} and not terminal:
      raise InspectionError("incomplete_sse_stream")

    changed = False
    for (_, kind), string_refs in lanes.items():
      joined = "".join(value for _, _, value in string_refs)
      self._signatures(joined)
      if kind == "json":
        value = strict_json(joined.encode(), self.config.max_json_depth)
        self._signatures(value)
        modified = self._redact_json(value, None, entities, pii_action)
        if modified != value:
          replacement, cursor = encode_json(modified).decode(), 0
          for i, (parent, key, old) in enumerate(string_refs):
            end = len(replacement) if i == len(string_refs) - 1 else cursor + len(old)
            parent[key] = replacement[cursor:end]
            cursor = end
          changed = True
        continue
      findings = self._find(joined)
      entities.extend(f.entity_type for f in findings)
      if findings and pii_action == "block":
        raise InspectionError("pii_block_policy")
      if findings and kind == "structural":
        raise InspectionError("pii_in_sse_structural_field")
      offset = 0
      for parent, key, value in string_refs:
        spans = [(max(f.start - offset, 0), min(f.end - offset, len(value)))
                 for f in findings if f.start < offset + len(value) and f.end > offset]
        offset += len(value)
        if spans:
          mask = [False] * len(value)
          for start, end in spans:
            mask[start:end] = [True] * (end - start)
          parent[key] = "".join("*" if hide else char for char, hide in zip(value, mask))
          changed = True
    if not changed:
      return body
    output = []
    for lines, value in events:
      if value is None:
        output.append("\n".join(lines))
      else:
        kept = [line for line in lines if line.partition(":")[0] != "data"]
        output.append("\n".join([*kept, "data: " + encode_json(value).decode()]))
    return ("\n\n".join(output) + "\n\n").encode()
