import React, {useEffect, useState} from 'react';
import {t, getLocale} from './i18n';
import {request} from './client';
import {Panel, Badge} from './components';

export default function AgentCredentials({agents, mutate, busy, synthetic}) {
  const [agentId,setAgentId]=useState(agents[0]?.agent_id || '');
  const [items,setItems]=useState([]), [fresh,setFresh]=useState(null), [error,setError]=useState('');
  const [revision,setRevision]=useState(0), [ttl,setTtl]=useState(86400);
  useEffect(()=>{
    let active=true;
    setItems([]);setFresh(null);setError('');
    if(agentId) request(`/agents/${encodeURIComponent(agentId)}/credentials`).then(result=>{
      if(active)setItems(result);
    }).catch(e=>{if(active)setError(e.message);});
    return ()=>{active=false;};
  },[agentId,revision]);
  const issue=async (rotateId)=>{
    setFresh(null);
    const result=await mutate(()=>request(`/agents/${encodeURIComponent(agentId)}/credentials`,{
      ttl_seconds:ttl, ...(rotateId ? {rotate_id:rotateId} : {})
    }),t('Credential issued. Save it now.'));
    if(result){
      setFresh(result);
      try { setItems(await request(`/agents/${encodeURIComponent(agentId)}/credentials`)); }
      catch(e) { setError(e.message); }
    }
  };
  return <Panel title={t('Agent credentials')} sub={t('Local agent identity')}>
    <div className="td-form-body">
      <p>{t('Connect with a gateway URL and an agent credential. Destination credentials remain separate.')}</p>
      {synthetic && <p className="td-callout">{t('Demo keys are local examples. Configure agent_key in your Docker gateway to use this connection model.')}</p>}
      <label>{t('Agent')}<select disabled={busy} value={agentId} onChange={e=>setAgentId(e.target.value)}>
        <option value="">{t('Select an agent')}</option>
        {agents.map(a=><option key={a.agent_id} value={a.agent_id}>{a.agent_id}{a.enabled?'':` (${t('Disabled')})`}</option>)}
      </select></label>
      <label>{t('Validity')}<select disabled={busy} value={ttl} onChange={e=>setTtl(Number(e.target.value))}>
        <option value={3600}>{t('1 hour')}</option><option value={86400}>{t('24 hours')}</option>
        <option value={2592000}>{t('30 days')}</option>
      </select></label>
      <button className="td-btn primary" disabled={busy || !agentId || !agents.find(a=>a.agent_id===agentId)?.enabled} onClick={()=>issue()}>{t('Issue credential')}</button>
      {error && <p role="alert">{error}</p>}
      {fresh && <div className="td-callout"><div><strong>{t('Shown once. Store this credential securely.')}</strong>
        <textarea readOnly aria-label={t('New agent credential')} value={fresh.credential} spellCheck={false} autoComplete="off"/>
        <button className="td-btn" onClick={()=>setFresh(null)}>{t('Hide credential')}</button></div></div>}
      <div className="td-table-wrap"><table><thead><tr><th>{t('Credential ID')}</th><th>{t('Status')}</th><th>{t('Expires at')}</th><th>{t('Actions')}</th></tr></thead>
        <tbody>{items.map(item=><tr key={item.credential_id}><td className="td-mono">{item.credential_id.slice(0,16)}…</td><td><Badge value={item.status}>{t({active:"Active",expired:"Expired",revoked:"Revoked"}[item.status])}</Badge></td><td>{new Date(item.expires_at*1000).toLocaleString(getLocale())}</td><td>{item.status==='active' && <div className="td-inline">
          <button className="td-btn" disabled={busy || !agents.find(a=>a.agent_id===agentId)?.enabled} onClick={()=>issue(item.credential_id)}>{t('Rotate')}</button>
          <button className="td-btn danger" disabled={busy} onClick={async()=>{
            const result=await mutate(()=>request(`/agents/${encodeURIComponent(agentId)}/credentials/${item.credential_id}/revoke`,{}),t('Credential revoked.'));
            if(result)setRevision(v=>v+1);
          }}>{t('Revoke')}</button></div>}</td></tr>)}</tbody></table></div>
      <p className="td-note">{t('Rotation immediately revokes the old credential. Update your client before its next request.')}</p>
      <h3>{t('Connection example')}</h3>
      <pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{'API base_url: https://gateway.example.com\nMCP URL: https://gateway.example.com/mcp\nAuthorization: Bearer <agent-credential>'}</pre>
      <p className="td-note">{t('Use your configured gateway hostname and mapped path. No credential belongs in a URL.')}</p>
    </div>
  </Panel>;
}
