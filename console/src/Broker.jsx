import { t } from "./i18n";
import React, { useState } from 'react';
import { Plus, ArrowUpRight, Check, X, Play } from 'lucide-react';
import { Panel, Badge, Drawer, Empty, SearchBox } from './components';
import { request, date, reasons } from './client';
const fieldLabels = {
  approval_id: "Approval ID",
  status: "Status",
  tenant_id: "Tenant",
  user_id: "Delegator",
  agent_id: "Agent",
  delegation_id: "Delegation ID",
  task_id: "Task",
  tool_name: "Tool",
  resource_id: "Resource",
  requested_action: "Requested action",
  agent_instance_id: "Runtime instance",
  request_digest: "Request digest",
  expires_at: "Expires at",
  consumed_at: "Consumed at",
  created_at: "Created at",
  decided_at: "Reviewed at",
  approver_id: "Reviewer",
  comment: "Review reason",
  owner_id: "Owner",
  sponsor_id: "Sponsor",
  runtime: "Runtime",
  model: "Model",
  allowed_tools: "Allowed tools",
  allowed_resources: "Allowed resources",
  risk_tier: "Risk level",
  enabled: "Enabled",
  purpose: "Delegation purpose",
  allowed_actions: "Allowed actions"
};
export default function Broker({
  broker,
  mutate,
  busy,
  run,
  synthetic
}) {
  const [tab, setTab] = useState('approvals'),
    [search, setSearch] = useState(''),
    [selected, setSelected] = useState(null),
    [form, setForm] = useState(null),
    [comment, setComment] = useState('');
  const [agent, setAgent] = useState({
    agent_id: '',
    owner_id: '',
    risk_tier: 'medium',
    allowed_tools: ['notes.read']
  });
  const [delegation, setDelegation] = useState({
    agent_id: broker.agents[0]?.agent_id || '',
    user_id: 'synthetic-user',
    task_id: '',
    purpose: '',
    ttl_seconds: 3600
  });
  const rows = broker[tab].filter(r => JSON.stringify(r).toLowerCase().includes(search.toLowerCase()));
  const title = {
    agents: t("Agent"),
    delegations: t("Delegations"),
    approvals: t("Approval requests")
  };
  const state = a => a.consumed_at ? 'consumed' : new Date(a.expires_at) < new Date() ? 'expired' : a.status;
  return <><div className="td-subtabs">{Object.entries(title).map(([key, label]) => <button className={key === tab ? 'active' : ''} key={key} onClick={() => {
        setTab(key);
        setSearch('');
      }}>{label}<span>{broker[key].length}</span></button>)}</div><Panel title={title[tab]} sub={t("Built-in Access Broker · Experimental")} action={<div className="td-inline">{tab === 'agents' && <button className="td-btn primary" onClick={() => setForm('agent')}><Plus size={14} />{t("Register agent")}</button>}{tab === 'delegations' && <>{synthetic && <button className="td-btn" disabled={busy} onClick={() => mutate(() => request('/demo/renew-delegation', {}), t("The default deployment delegation was renewed for 24 hours."))}>{t("Renew demo delegation")}</button>}<button className="td-btn primary" onClick={() => setForm('delegation')}><Plus size={14} />{t("Create delegation")}</button></>}{tab === 'approvals' && synthetic && <button className="td-btn" disabled={busy} onClick={() => run('deploy')}><Play size={14} />{t("Deployment approval scenario")}</button>}</div>}><div className="td-toolbar"><SearchBox value={search} onChange={setSearch} placeholder={t("Search agents, users or tasks")} /><span className="td-muted">{rows.length}{t("records")}</span></div>{!rows.length ? <Empty /> : <div className="td-table-wrap"><table><thead><tr>{(tab === 'agents' ? [t("Agent"), t("Owner"), t("Risk level"), t("Allowed tools"), t("Status"), ''] : tab === 'delegations' ? [t("Delegation / task"), t("Agent"), t("Delegator"), t("Allowed actions"), t("Expired"), ''] : [t("Status"), t("Agent / task"), t("Resource"), t("Requested at"), t("Validity"), '']).map((h, i) => <th key={i}>{h}</th>)}</tr></thead><tbody>{rows.map(row => <tr key={row.agent_id + '-' + (row.approval_id || row.delegation_id || 'agent')}>{tab === 'agents' ? <><td><strong>{row.agent_id}</strong><small className="td-block td-muted">{row.runtime}</small></td><td>{row.owner_id}</td><td><Badge value={row.risk_tier} /></td><td className="td-mono">{row.allowed_tools.join(', ')}</td><td><Badge value={row.enabled ? 'active' : 'block'}>{row.enabled ? t("Active") : t("Disabled")}</Badge></td></> : tab === 'delegations' ? <><td><strong>{row.task_id}</strong><small className="td-block td-muted">{row.purpose}</small></td><td>{row.agent_id}</td><td>{row.user_id}</td><td>{row.allowed_actions.join(', ')}</td><td>{date(row.expires_at)}{new Date(row.expires_at) < new Date() && <Badge value="block">{t("Expired")}</Badge>}</td></> : <><td><Badge value={state(row)}>{{
                      consumed: t("Consumed"),
                      expired: t("Expired")
                    }[state(row)]}</Badge></td><td><strong>{row.agent_id}</strong><small className="td-block td-mono">{row.tool_name}</small></td><td>{row.resource_id}</td><td>{date(row.created_at)}</td><td>{date(row.expires_at)}</td></>}<td><button className="td-icon" aria-label={t("{0} details", [row.approval_id || row.delegation_id || row.agent_id])} onClick={() => {
                  setSelected({
                    ...row,
                    type: tab
                  });
                  setComment('');
                }}><ArrowUpRight size={15} /></button></td></tr>)}</tbody></table></div>}</Panel>{selected && <Drawer title={selected.type === 'approvals' ? t("Review approval request") : selected.type === 'agents' ? t("Agent details") : t("Delegation details")} onClose={() => setSelected(null)}><div className="td-detail-hero"><Badge value={selected.status || selected.risk_tier || 'active'} /><h3>{selected.agent_id}</h3><p>{t(reasons[selected.reason] || selected.reason) || selected.purpose || selected.owner_id}</p></div><dl className="td-dl">{Object.entries(selected).filter(([key]) => !['type', 'metadata', 'reason'].includes(key)).map(([key, value]) => <React.Fragment key={key}><dt>{t(fieldLabels[key] || key)}</dt><dd>{Array.isArray(value) ? value.join(', ') : key.endsWith('_at') ? date(value) : typeof value === 'boolean' ? value ? t("Yes") : t("No") : String(value ?? '—')}</dd></React.Fragment>)}</dl>{selected.type === 'approvals' && <><div className="td-callout"><span>{t("Approval is bound to the request digest. It only authorizes a synthetic replay; no external business tool runs.")}</span></div>{state(selected) === 'pending' ? <form onSubmit={e => e.preventDefault()}><label>{t("Review reason")}<textarea value={comment} onChange={e => setComment(e.target.value)} maxLength={300} placeholder={t("Enter the reason for approval or denial")} /></label><div className="td-form-actions"><button className="td-btn danger" disabled={busy || comment.trim().length < 3} onClick={async () => {
              const result = await mutate(() => request(`/approvals/${selected.approval_id}/deny`, {
                comment: comment.trim()
              }), t("The approval request was denied."));
              if (result) setSelected({
                ...result,
                type: 'approvals'
              });
            }}><X size={15} />{t("Deny")}</button><button className="td-btn primary" disabled={busy || comment.trim().length < 3} onClick={async () => {
              const result = await mutate(() => request(`/approvals/${selected.approval_id}/approve`, {
                comment: comment.trim()
              }), t("The request was approved. No tool has run yet."));
              if (result) setSelected({
                ...result,
                type: 'approvals'
              });
            }}><Check size={15} />{t("Approve")}</button></div></form> : state(selected) === 'approved' ? <button className="td-btn primary" disabled={busy} onClick={async () => {
          const result = await run('deploy', selected.approval_id);
          if (result) setSelected(null);
        }}><Play size={15} />{t("Replay approved synthetic request")}</button> : <p className="td-note">{state(selected) === 'expired' ? t("This request has expired. Run the deployment approval scenario again.") : t("This request has been processed. A new execution needs a new decision.")}</p>}</>}</Drawer>}{form && <Drawer title={form === 'agent' ? t("Register agent") : t("Create task delegation")} onClose={() => setForm(null)}><form onSubmit={async e => {
        e.preventDefault();
        const result = await mutate(() => request(form === 'agent' ? '/agents' : '/delegations', form === 'agent' ? agent : delegation), form === 'agent' ? t("The agent was registered.") : t("The task delegation was created."));
        if (result) setForm(null);
      }}>{form === 'agent' ? <><label>{t("Agent ID")}<input required pattern="[a-zA-Z0-9_-]{2,60}" value={agent.agent_id} onChange={e => setAgent({
              ...agent,
              agent_id: e.target.value
            })} placeholder="security-assistant" /></label><label>{t("Owner")}<input required minLength={2} maxLength={80} value={agent.owner_id} onChange={e => setAgent({
              ...agent,
              owner_id: e.target.value
            })} placeholder="security-team" /></label><label>{t("Risk level")}<select value={agent.risk_tier} onChange={e => setAgent({
              ...agent,
              risk_tier: e.target.value
            })}><option value="low">{t("Low")}</option><option value="medium">{t("Medium")}</option><option value="high">{t("High")}</option></select></label><label>{t("Allowed tools")}<select value={agent.allowed_tools[0]} onChange={e => setAgent({
              ...agent,
              allowed_tools: [e.target.value]
            })}><option>notes.read</option><option>notes.delete</option><option>infra.deploy</option></select></label></> : <><label>{t("Agent")}<select required value={delegation.agent_id} onChange={e => setDelegation({
              ...delegation,
              agent_id: e.target.value
            })}>{broker.agents.map(a => <option key={a.agent_id}>{a.agent_id}</option>)}</select></label><label>{t("Delegator ID")}<input required minLength={1} maxLength={256} value={delegation.user_id} onChange={e => setDelegation({
              ...delegation,
              user_id: e.target.value
            })} placeholder="user-or-workload-subject" /></label><label>{t("Task ID")}<input required pattern="[a-zA-Z0-9_-]{2,60}" value={delegation.task_id} onChange={e => setDelegation({
              ...delegation,
              task_id: e.target.value
            })} placeholder="ticket-review" /></label><label>{t("Delegation purpose")}<textarea required minLength={3} maxLength={160} value={delegation.purpose} onChange={e => setDelegation({
              ...delegation,
              purpose: e.target.value
            })} /></label><label>{t("Validity")}<select value={delegation.ttl_seconds} onChange={e => setDelegation({
              ...delegation,
              ttl_seconds: Number(e.target.value)
            })}><option value={900}>{t("15 minutes")}</option><option value={3600}>{t("1 hour")}</option><option value={86400}>{t("24 hours")}</option></select></label><p className="td-note">{t("Permissions are limited to the selected agent's allowed tools and resources.")}</p></>}<button className="td-btn primary" disabled={busy}><Plus size={15} />{form === 'agent' ? t("Register") : t("Create delegation")}</button></form></Drawer>}</>;
}
