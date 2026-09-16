import InspectorSettings from './InspectorSettings';
import { t } from "./i18n";
import React, { useState } from 'react';
import { Network, Check, Save, Server, ArrowRight } from 'lucide-react';
import { Panel, Badge } from './components';
import { request, date } from './client';
export default function NetworkSettings({
  network,
  mutate,
  busy,
  editable = true
}) {
  const [draft, setDraft] = useState(network.applied),
    [validated, setValidated] = useState(false),
    [showAll, setShowAll] = useState(false);
  const applied = network.applied;
  const change = (key, value) => {
    setDraft({
      ...draft,
      [key]: value
    });
    setValidated(false);
  };
  const loopback = network.interfaces.find(i => i.kind === 'loopback');
  const ready = network.proxy_ready && network.inspector_ready && network.destination_ready;
  return <>
    <InspectorSettings status={network.inspectors} mutate={mutate} busy={busy} editable={editable} />
    <div className="td-callout"><Network size={20} /><div><strong>{t("Real Envoy proxy \xB7 explicit L7 deployment")}</strong><p>{t("Installed on one loopback interface. Synthetic HTTP requests traverse the proxy and gRPC inspector to a separate HTTP destination.")}</p></div><Badge value={ready ? 'allow' : 'block'}>{ready ? t("Path ready") : t("Check the path")}</Badge></div>
    <div className="td-connection-path"><span>{t("Trusted-hop simulator")}</span><ArrowRight size={16} /><span className="selected">Envoy :{applied.listen_port}</span><ArrowRight size={16} /><span>{t("Synthetic destination :18090")}</span></div>
    <div className="td-grid-2"><Panel title={t("Applied traffic path")} sub={t("Network v{0} \xB7 {1}", [applied.version, network.host_os])}><div className="td-form-body"><dl className="td-dl"><dt>{t("Deployment mode")}</dt><dd>{t("Explicit L7 · loopback")}</dd><dt>{t("Interface in use")}</dt><dd>{loopback?.name || t("Unavailable")} · 127.0.0.1</dd><dt>{t("Management API / UI")}</dt><dd>{window.location.host}{t("\xB7 same origin")}</dd><dt>{t("Proxy listener")}</dt><dd>127.0.0.1:{applied.listen_port}</dd><dt>{t("Inspector")}</dt><dd>{network.inspector_endpoint}</dd><dt>{t("Destination")}</dt><dd>{network.upstream_endpoint}</dd><dt>{t("Destination receipts")}</dt><dd>{network.destination_count ?? '—'}{t("requests \xB7 since destination startup")}</dd><dt>{t("Proxy")}</dt><dd><Badge value={network.proxy_ready ? 'allow' : 'block'}>{network.proxy_ready ? t("HTTP readiness confirmed") : t("No response")}</Badge></dd><dt>{t("Inspector")}</dt><dd><Badge value={network.inspector_ready ? 'allow' : 'block'}>{network.inspector_ready ? t("gRPC running") : t("Stopped")}</Badge></dd><dt>{t("Destination")}</dt><dd><Badge value={network.destination_ready ? 'allow' : 'block'}>{network.destination_ready ? t("HTTP readiness confirmed") : t("No response")}</Badge></dd><dt>{t("Failure behavior")}</dt><dd>{t("Inspector communication failure blocks traffic \xB7 no direct forwarding")}</dd></dl>{network.last_error && <p className="td-error">{t(network.last_error)}</p>}</div></Panel>
    <Panel title={editable ? t("Proxy path settings") : t("Deployment scope")} sub={editable ? t("Validate \u2192 apply \u2192 readiness check \xB7 restore previous settings on failure") : t("Supported and unsupported deployment paths are distinguished.")}><div className="td-form-body">{editable ? <><label>{t("Deployment profile")}<select value={draft.topology} onChange={e => change('topology', e.target.value)}><option value="explicit_loopback">{t("Explicit L7 \xB7 single loopback")}</option></select></label><label>{t("Listen address")}<input value="127.0.0.1" disabled /></label><label>{t("Listen port")}<input type="number" min={1024} max={65535} value={draft.listen_port} onChange={e => change('listen_port', Number(e.target.value))} /></label><label>{t("Request timeout (seconds)")}<input type="number" min={2} max={30} value={draft.request_timeout} onChange={e => change('request_timeout', Number(e.target.value))} /></label><label>{t("Body buffer limit (bytes)")}<input type="number" min={1024} max={1048576} value={draft.max_body_bytes} onChange={e => change('max_body_bytes', Number(e.target.value))} /></label><small>{t("Applied v")}{applied.version}{t("/ editing v")}{draft.version}{t("\xB7 applying briefly restarts the proxy.")}</small><div className="td-form-actions"><button className="td-btn" disabled={busy} onClick={async () => {
                if (await mutate(() => request('/network/validate', draft), t("Envoy configuration validation passed."))) setValidated(true);
              }}><Check size={15} />{t("Validate path")}</button><button className="td-btn primary" disabled={busy || !validated} onClick={async () => {
                const result = await mutate(() => request('/network', draft), t("The proxy path was applied and the new listener responded."));
                if (result) {
                  setDraft(result.applied);
                  setValidated(false);
                }
              }}><Save size={15} />{t("Apply path")}</button></div></> : null}<p className="td-note">{t("Physical NIC count and proxy topology are separate. This installation uses loopback only. Dual-NIC routing, transparent bridging and physical egress pinning are not supported. OS IP addresses and routes are not changed.")}</p><p className="td-note">{t("Agent identity is not connected to this synthetic traffic path. Console SSO is configured separately.")}</p></div></Panel></div>
    <Panel title={t("Detected host interfaces")} sub={t("Live OS addresses and link state \xB7 this is not a physical port count.")} action={<button className="td-btn" onClick={() => setShowAll(!showAll)}>{showAll ? t("IPv4 interfaces only") : t("Show all interfaces")}</button>}><div className="td-table-wrap"><table><thead><tr><th>{t("Interface")}</th><th>{t("Status")}</th><th>{t("Addresses")}</th><th>MTU</th><th>{t("Role in this installation")}</th></tr></thead><tbody>{network.interfaces.filter(i => showAll || i.addresses.some(a => /^\d+\./.test(a))).map(i => <tr key={i.name}><td className="td-mono">{i.name}</td><td><Badge value={i.up ? 'allow' : 'unknown'}>{i.up ? 'UP' : 'DOWN'}</Badge></td><td className="td-mono">{i.addresses.join(' · ') || t("Unassigned")}</td><td>{i.mtu ?? '—'}</td><td>{t(i.role)}</td></tr>)}</tbody></table></div></Panel>
  </>;
}
