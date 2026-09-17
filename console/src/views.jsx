import { t } from "./i18n";
import React, { useState } from 'react';
import { Activity, ShieldAlert, ScanLine, Clock, Download, Play, Check, Plus, Server, KeyRound, Network, Database, ShieldCheck, Save, FlaskConical } from 'lucide-react';
import { Badge, Empty, Metric, Panel, SearchBox, EventTable, TrafficChart, Drawer } from './components';
import { request, date, exportCSV } from './client';
export function Overview({
  data,
  navigate,
  onSelect,
  run,
  busy
}) {
  const events = data.events,
    blocked = events.filter(e => e.action === 'block').length,
    redacted = events.filter(e => e.action === 'redact').length;
  const pending = data.broker.approvals.filter(a => a.status === 'pending' && new Date(a.expires_at) > new Date());
  const latency = events.map(e => e.latency_ms).sort((a, b) => a - b),
    p95 = latency[Math.max(0, Math.ceil(latency.length * .95) - 1)] || 0;
  const top = Object.entries(events.reduce((result, e) => {
    if (e.action !== 'allow') result[e.tool] = (result[e.tool] || 0) + 1;
    return result;
  }, {})).sort((a, b) => b[1] - a[1]);
  return <><div className="td-metrics"><Metric label={t("Inspected requests")} value={events.length.toLocaleString()} caption={data.synthetic ? t("Stored synthetic scenarios") : t("Deployment traffic")} icon={Activity} onClick={() => navigate('events')} /><Metric label={t("Blocked / redacted")} value={`${blocked} / ${redacted}`} caption={t("Actual engine decisions")} icon={ShieldAlert} tone="orange" onClick={() => navigate('events')} /><Metric label={t("Pending approvals")} value={data.capabilities?.broker===false?t('Disabled'):pending.length} caption={data.capabilities?.broker===false?t('Enable in deployment.yaml'):t('Unexpired review requests')} icon={Clock} tone="purple" onClick={() => navigate('broker')} /><Metric label={t("Local decision p95")} value={`${p95} ms`} caption={data.integrated || data.deployment ? t("Proxy inspection stream \xB7 includes destination response") : t("In-process timing \xB7 excludes network")} icon={ScanLine} /></div><div className="td-grid-2"><Panel title={t("Decision trend")} sub={data.synthetic ? t("Last 24 hours \xB7 synthetic events") : t("Deployment traffic")}><TrafficChart synthetic={data.synthetic} events={events} /></Panel><Panel title={t("Tools requiring review")} sub={t("Blocked, redacted or approval-required requests")}><div className="td-ranked">{top.map(([tool, count], i) => <button key={tool} onClick={() => navigate('events')}><span className="td-rank">0{i + 1}</span><div><strong>{tool}</strong><div className="td-progress"><span style={{
                  width: `${count / Math.max(1, top[0][1]) * 100}%`
                }} /></div></div><strong>{count}<small>{t("records")}</small></strong></button>)}{!top.length && <Empty />}</div></Panel></div><Panel title={t("Recent decisions")} sub={t("Sanitized evidence without original content")} action={<button className="td-link" onClick={() => navigate('events')}>{t("View all \u2192")}</button>}><EventTable events={events} onSelect={onSelect} limit={6} /></Panel>{data.synthetic && <Panel title={t("Run a scenario")} sub={data.integrated ? t("Send real HTTP requests through Envoy to the synthetic destination.") : t("Call the inspection engine with the current policy. No external services receive data.")} action={<span className="td-tag"><FlaskConical size={13} />{t("Synthetic input")}</span>}><div className="td-scenario-grid">{data.scenarios.map(s => <button disabled={busy} className="td-scenario" key={s.id} onClick={() => run(s.id)}><Play size={14} /><span>{t(s.label)}</span></button>)}</div></Panel>}</>;
}
export function Events({
  synthetic = true,
  events,
  onSelect
}) {
  const [search, setSearch] = useState(''),
    [action, setAction] = useState('all'),
    [hours, setHours] = useState('all'),
    [page, setPage] = useState(0);
  const rows = events.filter(e => (action === 'all' || e.action === action) && (hours === 'all' || Date.now() - new Date(e.ts) < Number(hours) * 3600000) && `${e.agent} ${e.tool} ${e.reason} ${e.label}`.toLowerCase().includes(search.toLowerCase()));
  const change = (setter, value) => {
    setter(value);
    setPage(0);
  };
  return <Panel title={t("Traffic decisions")} sub={synthetic ? t("{0} records \xB7 synthetic HTTP / MCP requests", [rows.length]) : t("Deployment traffic")} action={<button className="td-btn" onClick={() => exportCSV('trapdefense-events.csv', rows, ['ts', 'agent', 'tool', 'action', 'reason', 'mode', 'latency_ms'])}><Download size={15} />{t("Export CSV")}</button>}><div className="td-toolbar"><SearchBox value={search} onChange={v => change(setSearch, v)} placeholder={t("Search agent, tool or reason")} /><select aria-label={t("Decision filter")} value={action} onChange={e => change(setAction, e.target.value)}><option value="all">{t("All decisions")}</option><option value="allow">{t("Allow")}</option><option value="block">{t("Block")}</option><option value="redact">{t("Redact")}</option><option value="approval_required">{t("Approval required")}</option></select><select aria-label={t("Time filter")} value={hours} onChange={e => change(setHours, e.target.value)}><option value="all">{t("All time")}</option><option value="1">{t("Last hour")}</option><option value="24">{t("Last 24 hours")}</option></select></div><EventTable events={rows.slice(page * 12, (page + 1) * 12)} onSelect={onSelect} /><div className="td-pagination"><span>{rows.length ? `${page * 12 + 1}–${Math.min((page + 1) * 12, rows.length)}` : '0'} / {rows.length}</span><div><button className="td-btn" disabled={!page} onClick={() => setPage(page - 1)}>{t("Previous")}</button><button className="td-btn" disabled={(page + 1) * 12 >= rows.length} onClick={() => setPage(page + 1)}>{t("Next")}</button></div></div></Panel>;
}
export function Policies({
  policy,
  deployment,
  mutate,
  busy,
  integrated = false, brokerEnabled = false
}) {
  const [draft, setDraft] = useState(policy),
    [validated, setValidated] = useState(false);
  const change = (key, value) => {
    setDraft({
      ...draft,
      [key]: value
    });
    setValidated(false);
  };
  return <div className="td-policy-layout"><Panel title={t("Inspection and execution policy")} sub={deployment ? `v${policy.version}` : t("Applied policy v{0} \xB7 changes update the local demo engine.", [policy.version])}><div className="td-form-body"><div className="td-callout"><ShieldCheck size={18} /><div><strong>{deployment ? t("Saved changes apply to new requests.") : t("Saved changes apply to the next synthetic request.")}</strong><p>{integrated || deployment ? t("Applies to this installation's Envoy inspector. In-flight streams keep their original policy; new requests use the update.") : t("Does not deploy to external Envoy or customer equipment. Unmapped requests are blocked by default.")}</p></div></div><label>{t("Inspection mode")}<select value={draft.mode} onChange={e => change('mode', e.target.value)}><option value="inline">{t("Inline \u2014 allow, block, redact")}</option><option value="mirror">{t("Mirror \u2014 observation only")}</option></select></label><label>{t("Personal data handling")}<select value={draft.pii_action} onChange={e => change('pii_action', e.target.value)}><option value="redact">{t("Redact permitted fields")}</option><option value="block">{t("Block personal data")}</option></select></label><h3>{t("Tool execution rules")}</h3><div className="td-rule-list">{Object.entries(draft.rules).map(([name, value]) => <div key={name}><div><strong>{name}</strong><small>{name === 'infra.deploy' ? t("Broker approval is still required after policy allows") : name === 'notes.delete' ? t("Delete notes") : deployment ? name : t("Read notes")}</small></div><div className="td-rule-controls"><label>{t("Action policy")}<select aria-label={t("{0} policy", [name])} value={value} onChange={e => change('rules', {
              ...draft.rules,
              [name]: e.target.value
            })}><option value="allow">{t("Allow")}</option><option value="block">{t("Block")}</option></select></label><label>{t("PII override")}<select aria-label={t("{0} PII policy", [name])} value={draft.pii_rules[name]} onChange={e => change('pii_rules', {
              ...draft.pii_rules,
              [name]: e.target.value
            })}><option value="inherit">{t("Inherit global")}</option><option value="redact">{t("Redact")}</option><option value="block">{t("Block")}</option></select></label></div></div>)}</div><div className="td-form-actions"><button className="td-btn" disabled={busy} onClick={async () => {
            if (await mutate(() => request('/policy/validate', draft), t("Policy syntax and mappings were validated."))) setValidated(true);
          }}><Check size={15} />{t("Validate policy")}</button><button className="td-btn primary" disabled={busy || !validated} onClick={async () => {
            const result = await mutate(() => request('/policy', draft), t("The policy was applied to the local inspector."));
            if (result) {
              setDraft(result);
              setValidated(false);
            }
          }}><Save size={15} />{t("Apply policy")}</button></div></div></Panel><Panel title={t("Applied scope")} sub={brokerEnabled?t("Inspection + built-in Access Broker"):t("Inspection only")}><div className="td-form-body"><dl className="td-dl"><dt>{t("Forwarding source")}</dt><dd>{deployment?.source || "demo-decryptor"}</dd><dt>{t("Destination")}</dt><dd>{deployment?.upstream || "tools.demo.test"}</dd><dt>{t("Path")}</dt><dd>{deployment ? deployment.routes.map(r=>`${r.method} ${r.path}`).join(", ") : "POST /mcp"}</dd><dt>{t("Target field")}</dt><dd>{deployment ? "deployment.yaml: redact_fields" : "params.arguments.message"}</dd><dt>{t("External URLs")}</dt><dd>{t("Empty allowlist \xB7 default deny")}</dd><dt>{t("Inspection failure")}</dt><dd>{t("Inline blocks / Mirror uncertain")}</dd></dl><p className="td-note">{deployment ? t("Only routed traffic is inspected. Target-service permissions still apply.") : integrated ? t("The destination is the installed synthetic HTTP server. Mirror observes the same path without changing content or consuming approvals. Inspector communication failures still block traffic.") : t("This form manages fixed demo mappings. Arbitrary destinations and production deployment require separate integration.")}</p></div></Panel></div>;
}
export function Connections({
  data
}) {
  return <><div className="td-callout"><Network size={19} /><div><strong>{t("Local components and external connections are distinguished.")}</strong><p>{t("The engine and Broker are running. TLS equipment, Envoy and real IAM are not connected in this mode.")}</p></div></div><div className="td-connection-path"><span>{t("Synthetic agent")}</span><i>→</i><span>{t("Trusted-hop signature")}</span><i>→</i><span className="selected">{t("Inspection + Access Broker")}</span><i>→</i><span>{t("Decision record")}</span></div><div className="td-grid-2">{[{
        icon: ScanLine,
        title: t("AI Firewall inspector"),
        status: t("Ready"),
        kind: 'allow',
        body: t("Current Python engine \xB7 policy / PII / signature / replay checks"),
        facts: [[t("Policy"), `v${data.policy.version}`], [t("Mode"), data.policy.mode], ['PII', data.policy.pii_action]]
      }, {
        icon: KeyRound,
        title: t('Built-in Access Broker'),
        status: t("Ready"),
        kind: 'allow',
        body: t("Open-source broker \xB7 local file storage \xB7 request-bound one-time approval"),
        facts: [[t("Tenant"), 'synthetic-tenant'], [t("Registered agents"), data.broker.agents.length], [t("Delegations"), data.broker.delegations.length]]
      }, {
        icon: Server,
        title: t("TLS / proxy data path"),
        status: t("Not connected"),
        kind: 'unknown',
        body: t("Request signing and inspection are simulated inside the process."),
        facts: [[t("Real TLS equipment"), t("Not connected")], [t("Real Envoy"), t("Not connected")], [t("External tool execution"), t("None")]]
      }, {
        icon: Database,
        title: t("IAM / storage"),
        status: t("Synthetic environment"),
        kind: 'approval_required',
        body: t("Local admin sessions and synthetic delegation context. This does not prove real IdP integration."),
        facts: [['Microsoft Entra ID', t("Synthetic validation in a separate harness")], [t("Current sign-in"), t("Local account")], [t("Audit storage"), t("SQLite \xB7 not immutable")]]
      }].map(item => <Panel key={item.title} title={item.title} action={<Badge value={item.kind}>{item.status}</Badge>}><div className="td-form-body"><item.icon size={28} className="td-accent" /><p className="td-muted">{item.body}</p><dl className="td-dl">{item.facts.map(([key, val]) => <React.Fragment key={key}><dt>{key}</dt><dd>{val}</dd></React.Fragment>)}</dl></div></Panel>)}</div></>;
}
export function Audit({
  records
}) {
  const [search, setSearch] = useState('');
  const rows = records.filter(r => `${r.event} ${r.actor} ${r.detail}`.toLowerCase().includes(search.toLowerCase()));
  return <Panel title={t("Operational audit")} sub={t("Sign-in, policy, approval and account changes \xB7 latest 1,000 records")} action={<button className="td-btn" onClick={() => exportCSV('trapdefense-audit.csv', rows, ['ts', 'actor', 'event', 'detail'])}><Download size={15} />{t("Export CSV")}</button>}><div className="td-toolbar"><SearchBox value={search} onChange={setSearch} placeholder={t("Search action, actor or changes")} /><span className="td-muted">{rows.length}{t("records")}</span></div>{rows.length ? <div className="td-table-wrap"><table><thead><tr><th>{t("Time")}</th><th>{t("Actor")}</th><th>{t("Action")}</th><th>{t("Change / decision details")}</th></tr></thead><tbody>{rows.map(r => <tr key={r.id}><td className="td-nowrap">{date(r.ts)}</td><td>{r.actor}</td><td className="td-mono">{r.event}</td><td>{r.detail}</td></tr>)}</tbody></table></div> : <Empty />}</Panel>;
}
export function Settings({
  deployment,
  mutate,
  busy,
  onChanged,
  session
}) {
  const [current, setCurrent] = useState(''),
    [next, setNext] = useState(''),
    [confirm, setConfirm] = useState(''),
    [error, setError] = useState('');
  return <div className="td-policy-layout"><Panel title={t("Administrator password")} sub={t("Changing it ends all active sessions immediately.")}><form className="td-form-body" onSubmit={async e => {
        e.preventDefault();
        setError('');
        if (next !== confirm) {
          setError(t("The new passwords do not match."));
          return;
        }
        const result = await mutate(() => request('/password', {
          current_password: current,
          new_password: next
        }), t("Password changed. Sign in with your new password."));
        if (result) onChanged();
      }}><label>{t("Account")}<input value="admin" disabled autoComplete="username" /></label><label>{t("Current password")}<input type="password" required maxLength={128} autoComplete="current-password" value={current} onChange={e => setCurrent(e.target.value)} /></label><label>{t("New password")}<input type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={next} onChange={e => setNext(e.target.value)} /><small>{t("At least 8 characters \xB7 different from the current password")}</small></label><label>{t("Confirm new password")}<input type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={confirm} onChange={e => setConfirm(e.target.value)} /></label>{error && <div className="td-error" role="alert">{error}</div>}<button className="td-btn primary" disabled={busy}><KeyRound size={15} />{t("Change password")}</button></form></Panel><Panel title={deployment ? t("Console identity") : t("Account and demo data")} sub={deployment ? t("Self-hosted AI Firewall") : t("Stored on this computer.")}><div className="td-form-body"><dl className="td-dl"><dt>{t("User")}</dt><dd>admin</dd><dt>{t("Role")}</dt><dd>{deployment ? t("Administrator") : t("Demo administrator")}</dd><dt>{t("Default password")}</dt><dd>{deployment ? t("No default password") : session.password_changed ? t("Changed") : t("In use \xB7 change recommended")}</dd><dt>{t("Session")}</dt><dd>{t("Server-side \xB7 up to 8 hours")}</dd><dt>{t("Data")}</dt><dd>{deployment ? t("Deployment traffic") : t("Synthetic data only")}</dd></dl><p className="td-note">{deployment ? t("Edit deployment.yaml for destinations and mappings, then recreate the stack. Policies and passwords are managed here.") : t("Passwords and policies survive restart. Do not expose this demo server to the Internet.")}</p></div></Panel></div>;
}
