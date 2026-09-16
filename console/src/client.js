import { t, getLocale } from "./i18n";
export async function request(path, body) {
  const response = await fetch(`/demo-api${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-TD-Demo': '1'
    },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : t("Request failed ({0})", [response.status]));
    error.status = response.status;
    throw error;
  }
  return data;
}
export function exportCSV(name, rows, columns) {
  const cell = value => {
    let text = String(value ?? '');
    if (/^(?:\s*[=+\-@]|[\t\r])/.test(text)) text = `'${text}`;
    return `"${text.replaceAll('"', '""')}"`;
  };
  const content = '\uFEFF' + [columns, ...rows.map(row => columns.map(key => row[key]))].map(row => row.map(cell).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([content], {
    type: 'text/csv;charset=utf-8'
  }));
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
export function date(value) {
  return value ? new Date(value).toLocaleString(getLocale(), {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }) : '—';
}
export const reasons = {
  high_risk_action_requires_approval: "High-risk deployment requires approval for this request.",
  approved_high_risk_action: "The request-bound approval was verified and consumed once.",
  response_pii_redacted: "Personal data in the tool response was redacted.",
  policy_allowed: "The mapped tool and local policy allowed the request.",
  pii_redacted: "Personal data in permitted fields was redacted.",
  secret_detected: "A recognized credential was blocked without recording its value.",
  local_policy_denied: "An explicit policy blocked this tool action.",
  suspicious_instruction: "A known suspicious instruction pattern was detected.",
  pii_block_policy: "The request matched the personal-data blocking policy.",
  high_risk_action: "A high-risk action requires human approval.",
  agent_not_registered: "The agent is not registered.",
  egress_not_allowed: "An external destination outside the allowlist was detected."
};
