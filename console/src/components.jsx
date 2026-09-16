import { t } from "./i18n";
import React, { useEffect, useRef } from 'react';
import { X, Search, ArrowUpRight, Inbox } from 'lucide-react';
import { date, reasons } from './client';
const decisionLabel = {
  allow: "Allow",
  block: "Block",
  redact: "Redact",
  approval_required: "Approval required",
  unknown: "Needs review",
  pending: "Pending",
  approved: "Approve",
  denied: "Deny",
  low: "Low",
  medium: "Medium",
  high: "High",
  active: "Active"
};
export function Badge({
  value,
  children
}) {
  return <span className={`td-badge ${value}`}>{children || t(decisionLabel[value] || value)}</span>;
}
export function Empty({
  text = t("No records match the current filters.")
}) {
  return <div className="td-empty"><Inbox size={28} /><p>{text}</p></div>;
}
export function Metric({
  label,
  value,
  caption,
  icon: Icon,
  tone = 'blue',
  onClick
}) {
  return <button className={`td-metric ${tone}`} onClick={onClick} disabled={!onClick}><div><span>{label}</span>{Icon && <Icon size={17} />}</div><strong>{value}</strong><small>{caption}</small></button>;
}
export function Panel({
  title,
  sub,
  action,
  children,
  className = ''
}) {
  return <section className={`td-panel ${className}`}><header><div><h2>{title}</h2>{sub && <p>{sub}</p>}</div>{action}</header>{children}</section>;
}
export function SearchBox({
  value,
  onChange,
  placeholder = t("Search")
}) {
  return <label className="td-search"><Search size={16} /><input aria-label={placeholder} placeholder={placeholder} value={value} onChange={e => onChange(e.target.value)} /></label>;
}
export function Drawer({
  title,
  onClose,
  children,
  wide = false
}) {
  const box = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    box.current?.querySelector('button')?.focus();
    const key = e => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Tab') {
        const nodes = box.current?.querySelectorAll('button:not(:disabled),input,select,textarea,a[href]');
        if (!nodes?.length) return;
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
        if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', key);
    return () => {
      document.removeEventListener('keydown', key);
      previous?.focus();
    };
  }, []);
  return <div className="td-overlay" onClick={e => e.target === e.currentTarget && onClose()}><aside ref={box} className={`td-drawer ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}><header><h2>{title}</h2><button className="td-icon" onClick={onClose} aria-label={t("Close")}><X size={20} /></button></header><div className="td-drawer-body">{children}</div></aside></div>;
}
export function EventDetail({
  event,
  onClose
}) {
  const piiAction = event.pii_policy_action === 'block' ? t("Block") : event.pii_policy_action === 'redact' ? t("Redact") : t("Not applicable");
  const piiScope = {
    global: t("Global default"),
    route: t("Route override"),
    tool: t("Tool override")
  }[event.pii_policy_scope] || t("Not applicable");
  const mirrorAssessment = {
    would_allow: t("Would allow"),
    would_block: t("Would block"),
    would_redact: t("Would redact"),
    would_approval_required: t("Would require approval"),
    would_unknown: t("Needs review")
  }[event.hypothetical_action];
  return <Drawer title={t("Decision details \xB7 #{0}", [event.id])} onClose={onClose}><div className="td-detail-hero"><Badge value={event.action} /><span>{event.mode === 'mirror' ? t("Observation only") : event.transport ? t("Real proxy path") : t("In-process demo")}</span><h3>{t(event.label)}</h3><p>{t(reasons[event.reason] || event.reason)}</p></div><dl className="td-dl">{Object.entries({
        [t("Time")]: date(event.ts),
        [t("Agent")]: event.agent,
        [t("Tool")]: event.tool,
        [t("Resource")]: event.resource,
        [t("Rule reason")]: event.reason,
        [t("Policy")]: `v${event.policy_version}`,
        [t("PII policy")]: `${piiAction} · ${piiScope}`,
        ...(event.mode === 'mirror' ? {
          [t("Mirror assessment")]: mirrorAssessment || t("Needs review")
        } : {}),
        [t("Local decision latency")]: `${event.latency_ms} ms`,
        [t("Authorization scope")]: event.authorization_scope,
        [t("Forwarding source")]: event.source_verified ? t("Signature verified") : t("Not verified"),
        [t("User identity")]: t("Synthetic context \xB7 real IAM not connected"),
        [t("Coverage")]: event.coverage,
        ...(event.transport ? {
          [t("Actual HTTP status")]: event.transport.http_status ?? t("Not confirmed"),
          [t("Destination delivery")]: event.transport.upstream_received === true ? t("Receipt confirmed") : event.transport.upstream_received === false ? t("Not forwarded") : t("Not confirmed"),
          [t("Round-trip time")]: event.transport.round_trip_ms != null ? `${event.transport.round_trip_ms} ms` : t("External request"),
          [t("Request masking at destination")]: event.transport.receipt?.request_redacted ? t("Redacted receipt confirmed") : t("Not applicable"),
          [t("Response masking")]: event.transport.response_redacted ? t("Redacted response confirmed") : t("Not applicable")
        } : {})
      }).map(([key, value]) => <React.Fragment key={key}><dt>{key}</dt><dd>{value}</dd></React.Fragment>)}</dl><h3 className="td-section-title">{t("Decision path")}</h3><div className="td-timeline">{event.steps.map((step, index) => <div key={t(step.stage)}><span>{index + 1}</span><section><strong>{t(step.stage)}</strong><p>{t(step.status)}</p></section></div>)}</div><h3 className="td-section-title">{t("Sanitized request metadata")}</h3><pre>{JSON.stringify(event.request, null, 2)}</pre>{event.entities.length > 0 && <p className="td-note">{t("Detected types:")}{event.entities.join(', ')}</p>}<p className="td-note">{t("Original bodies and authentication keys are not stored.")}{" "}{event.transport ? t("The synthetic request traversed real Envoy. The destination is a test HTTP server; no external business tool ran.") : t("The engine evaluated synthetic input; no external tool ran.")}</p>{event.request_digest && <><h3 className="td-section-title">{t("Request digest")}</h3><code className="td-digest">{event.request_digest}</code></>}</Drawer>;
}
export function EventTable({
  events,
  onSelect,
  limit
}) {
  const rows = limit ? events.slice(0, limit) : events;
  return !rows.length ? <Empty /> : <div className="td-table-wrap"><table><thead><tr><th>{t("Time")}</th><th>{t("Decision")}</th><th>{t("Agent / tool")}</th><th>{t("Detection / policy reason")}</th><th>{t("Latency")}</th><th></th></tr></thead><tbody>{rows.map(event => <tr key={event.id}><td className="td-nowrap">{date(event.ts)}</td><td><Badge value={event.action} />{event.mode === 'mirror' && <small className="td-muted td-block">{t("Observe")}</small>}</td><td><strong>{event.agent}</strong><small className="td-mono td-block">{event.tool}</small></td><td><span>{t(event.label)}</span><small className="td-muted td-block">{event.reason}</small></td><td className="td-mono td-nowrap">{event.latency_ms} ms</td><td><button className="td-icon" aria-label={t("Event {0} details", [event.id])} onClick={() => onSelect(event)}><ArrowUpRight size={16} /></button></td></tr>)}</tbody></table></div>;
}
export function TrafficChart({
  events
}) {
  const now = Date.now();
  const buckets = Array.from({
    length: 12
  }, (_, i) => ({
    label: new Date(now - (11 - i) * 2 * 3600000).getHours() + t("h"),
    allow: 0,
    risk: 0
  }));
  events.forEach(e => {
    const ago = (now - new Date(e.ts).getTime()) / 7200000;
    const index = 11 - Math.floor(ago);
    if (index >= 0 && index < 12) buckets[index][e.action === 'allow' ? 'allow' : 'risk']++;
  });
  const max = Math.max(1, ...buckets.map(b => b.allow + b.risk));
  return <div className="td-chart" role="img" aria-label={t("Synthetic decisions over the last 24 hours")}><div className="td-chart-legend"><span><i className="blue" />{t("Allow")}</span><span><i className="orange" />{t("Block \xB7 redact \xB7 review")}</span><small>{t("Stored synthetic events \xB7 2-hour buckets")}</small></div><div className="td-bars">{buckets.map((b, i) => <div className="td-bar-cell" key={i}><div className="td-bar-stack" title={t("{0}: {1} records", [b.label, b.allow + b.risk])}><span className="risk" style={{
            height: `${b.risk / max * 125}px`
          }} /><span className="allow" style={{
            height: `${b.allow / max * 125}px`
          }} /></div><small>{b.label}</small></div>)}</div></div>;
}
