import React, { useState } from 'react';
import { Panel, Badge } from './components';
import { request } from './client';
import { t } from './i18n';

export default function InspectorSettings({ status, mutate, busy, editable }) {
  const [replicas, setReplicas] = useState(status?.replicas?.length || 1);
  if (!status) return null;
  const run = action => mutate(() => request('/inspectors', { action, replicas }), t('Inspector operation completed.'));
  return <Panel title={t('Inspector processes')} sub={t('Same-host recovery; not cross-server HA.')}>
    <div className="td-form-body">
      <Badge value={status?.state === 'healthy' ? 'allow' : 'block'}>{t(status?.state || 'stopped')}</Badge>
      <p className="td-note">{t('New requests use the committed policy. Applying restarts the pool and proxy; traffic fails closed during the interruption.')}</p>
      {editable && <div className="td-form-actions">
        <label>{t('Process count')}<select value={replicas} disabled={busy} onChange={e => setReplicas(Number(e.target.value))}>{[1, 2, 4].map(n => <option key={n} value={n}>{n}</option>)}</select></label>
        <button className="td-btn primary" disabled={busy} onClick={() => run('apply')}>{t('Apply / start')}</button>
        <button className="td-btn" disabled={busy || status?.state === 'stopped'} onClick={() => run('stop')}>{t('Stop inspection')}</button>
      </div>}
      {status?.reason && <p className="td-error">{status.reason}</p>}
      <div className="td-table-wrap"><table><thead><tr><th>PID</th><th>{t('Status')}</th><th>{t('Restarts')}</th><th>gRPC</th></tr></thead><tbody>{(status?.replicas || []).map(member => <tr key={member.index}><td>{member.pid}</td><td>{t(member.state)}</td><td>{member.restarts}</td><td>{member.grpc_port}</td></tr>)}</tbody></table></div>
    </div>
  </Panel>;
}
