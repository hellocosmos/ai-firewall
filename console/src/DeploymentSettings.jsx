import React from 'react';
import { t } from './i18n';
import { Panel } from './components';

export default function DeploymentSettings({deployment, network}) {
  return <Panel title={t('Self-hosted Community')} sub={t('Configured destination only')}>
    <div className="td-form-body">
      <div className="td-callout"><div><strong>{t('Client → TrapDefense → MCP / API')}</strong><p>{t('Only routed traffic is inspected. Target-service permissions still apply.')}</p></div></div>
      <dl className="td-dl">
        <dt>{t('Destination')}</dt><dd>{deployment.upstream}</dd>
        <dt>{t('Client authentication')}</dt><dd>X-TD-Client-Key</dd>
        <dt>{t('Destination authentication')}</dt><dd>{deployment.destination_auth}</dd>
        <dt>{t('Inspector')}</dt><dd>{network?.inspector_ready ? t('Ready') : t('Unavailable')}</dd>
        <dt>Envoy</dt><dd>{network?.proxy_ready ? t('Listener reachable') : t('Unavailable')}</dd>
        <dt>{t('Body limit')}</dt><dd>{deployment.max_body_bytes} bytes</dd>
      </dl>
      <p>{t('The connection key verifies deployment access, not agent or user identity.')}</p>
      <p>{t('JSON HTTP and stateless JSON MCP only. OAuth login brokering, sessions and long-lived SSE are not supported by this profile.')}</p>
      <h3>{t('Configured routes')}</h3>
      {deployment.routes.map(r=><p key={`${r.method}:${r.path}`}><code>{r.method} {r.path}</code> · {r.protocol} · {r.tools.join(', ')}</p>)}
      <p className="td-note">{t('Edit deployment.yaml for destinations and mappings, then recreate the stack. Policies and passwords are managed here.')}</p>
      <p className="td-note">{t('Listener checks do not prove destination authentication or successful inspection. Send a test request and inspect its decision record.')}</p>
    </div>
  </Panel>;
}
