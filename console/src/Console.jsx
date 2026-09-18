import { t, useLocale } from "./i18n";
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { LayoutDashboard, Activity, SlidersHorizontal, Network, KeyRound, ScrollText, Settings, Shield, RefreshCw, LogOut, Menu, X, FlaskConical, ArrowRight, CheckCircle2, AlertCircle } from 'lucide-react';
import { request } from './client';
import { EventDetail } from './components';
import { Overview, Events, Policies, Connections, Audit, Settings as SettingsView } from './views';
import Broker from './Broker';
import LanguageSelector from './LanguageSelector';
import NetworkSettings from './NetworkSettings';
import DeploymentSettings from './DeploymentSettings';
import Operations from './Operations';
import './demo.css';
const pages = [['overview', "Dashboard", LayoutDashboard, "Overview"], ['events', "Traffic / Events", Activity, "Request decisions and evidence"], ['policies', "Policies", SlidersHorizontal, "Inspection policy and execution boundaries"], ['connections', "Connections / System", Network, "Components and connectivity"], ['broker', 'Access Broker', KeyRound, "Agents \xB7 delegations \xB7 approvals"], ['audit', "Audit", ScrollText, "Operational changes and decisions"], ['settings', "Settings", Settings, "Installation \xB7 network \xB7 administrator"]];
export default function Console() {
  useLocale();
  const [auth, setAuth] = useState({enabled:false,local_login:false,synthetic:false});
  const [session, setSession] = useState(null),
    [checking, setChecking] = useState(true),
    [data, setData] = useState(null),
    [audit, setAudit] = useState([]),
    [page, setPage] = useState('overview'),
    [selected, setSelected] = useState(null),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(false),
    [notice, setNotice] = useState(null),
    [menu, setMenu] = useState(false),
    [login, setLogin] = useState({
      username: 'admin',
      password: ''
    }),
    [loginError, setLoginError] = useState('');
  const timer = useRef(null),
    mutation = useRef(false);
  const notify = (text, error = false) => {
    clearTimeout(timer.current);
    setNotice({
      text,
      error
    });
    timer.current = setTimeout(() => setNotice(null), 7000);
  };
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [next, logs] = await Promise.all([request('/overview'), request('/audit')]);
      setData(next);
      setAudit(logs);
    } catch (error) {
      if (error.status === 401) {
        setSession(null);
        setData(null);
      } else notify(error.message, true);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    document.title = 'TrapDefense — AI Security Gateway Console';
    request('/auth/config').then(setAuth).catch(() => setLoginError('Sign-in configuration unavailable.'));
    if (new URLSearchParams(window.location.search).get('signin') === 'failed') setLoginError('Entra sign-in failed. Check your assigned app role.');
    request('/session').then(setSession).catch(() => {}).finally(() => setChecking(false));
    return () => clearTimeout(timer.current);
  }, []);
  useEffect(() => {
    if (!session) return;
    load();
    const interval = setInterval(() => {
      if (!mutation.current) load();
    }, 30000);
    return () => clearInterval(interval);
  }, [session, load]);
  async function mutate(action, message) {
    if (mutation.current) return null;
    mutation.current = true;
    setBusy(true);
    try {
      const result = await action();
      if (message) notify(message);
      await load();
      return result;
    } catch (error) {
      notify(error.message, true);
      if (error.status === 401) {
        setSession(null);
        setData(null);
      }
      return null;
    } finally {
      mutation.current = false;
      setBusy(false);
    }
  }
  const readOnly = session?.role === 'viewer';
  async function run(name, approval_id) {
    const event = await mutate(() => request(`/scenarios/${name}`, {
      approval_id
    }), null);
    if (event) {
      setSelected(event);
      notify(t("Synthetic decision completed: {0}", [event.action]));
    }
    return event;
  }
  const navigate = key => {
    setPage(key);
    setMenu(false);
    setSelected(null);
  };
  const current = pages.find(p => p[0] === page) || pages[0];
  if (checking) return <div className="td-app td-loading"><Shield size={32} />{t("Checking your console session\u2026")}</div>;
  return <div className="td-app">{notice && <div className={`td-toast ${notice.error ? 'error' : ''}`} role={notice.error ? 'alert' : 'status'}>{notice.error ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}<span>{t(notice.text)}</span><button onClick={() => setNotice(null)} aria-label={t("Dismiss notification")}><X size={15} /></button></div>}{!session ? <div className="td-login"><div className="td-login-story"><div className="td-logo"><Shield size={24} /><strong>TrapDefense</strong><span>AI SECURITY GATEWAY</span></div><div className="td-login-title"><span className="td-eyebrow">{t("Control the point of action")}</span><h1>{t("Make agent actions")}<br />{t("visible and controlled.")}</h1><p>{t("Inspect requests, check permissions,")}<br />{t("and keep the evidence.")}</p><div className="td-login-path"><span>Agent</span><ArrowRight size={16} /><strong>AI Security Gateway</strong><ArrowRight size={16} /><span>Tool / API</span></div></div><small>{t("Open-source inspection · built-in agent authorization")}</small></div><div className="td-login-side"><div className="td-login-card"><LanguageSelector selfhost={auth.deployment}/><span className="td-tag"><FlaskConical size={13} />{auth.deployment ? t("Self-hosted AI Firewall") : t("Local demo")}</span><h2>{t("Sign in to the console")}</h2><p>{auth.deployment ? t("Use the administrator password chosen during setup.") : t("Explore policy and access control with synthetic data.")}</p>{auth.enabled && <div><button className="td-btn primary" disabled={busy} onClick={async () => { if (auth.origin && window.location.origin !== auth.origin) {window.location.assign(auth.origin);return;} setBusy(true); try { const result=await request('/auth/start',{}); window.location.assign(result.url); } catch(error) {setLoginError(error.message);setBusy(false);} }}>{t(auth.synthetic ? 'Sign in with Synthetic Entra' : 'Sign in with Microsoft Entra ID')}</button><p className="td-note">{t(auth.synthetic ? 'Synthetic identity demo. No Microsoft account is used.' : 'Use your assigned organization account.')}</p></div>}{loginError && <div className="td-error" role="alert">{t(loginError)}</div>}{auth.local_login && <><form onSubmit={async e => {
            e.preventDefault();
            setLoginError('');
            setBusy(true);
            try {
              const user = await request('/login', login);
              setSession(user);
              setLogin({
                ...login,
                password: ''
              });
            } catch (error) {
              setLoginError(error.message);
            } finally {
              setBusy(false);
            }
          }}><label>{t("Username")}<input autoComplete="username" required value={login.username} onChange={e => setLogin({
                ...login,
                username: e.target.value
              })} /></label><label>{t("Password")}<input type="password" autoComplete="current-password" required value={login.password} onChange={e => setLogin({
                ...login,
                password: e.target.value
              })} /></label>{loginError && <div className="td-error" role="alert">{t(loginError)}</div>}<button className="td-btn primary" disabled={busy}>{busy ? t("Checking\u2026") : t("Sign in")}<ArrowRight size={16} /></button></form><div className="td-demo-credential"><strong>{t("On first installation")}</strong><span>{auth.deployment ? t("No default password") : "admin / 1234"}</span><small>{t("Use your new password if you have changed it.")}</small></div></>}<p className="td-note">{t("Console sign-in and agent authorization use separate identity boundaries.")}</p></div></div></div> : <><aside className={`td-sidebar ${menu ? 'open' : ''}`}><div className="td-logo"><Shield size={25} /><strong>TrapDefense</strong><button className="td-icon td-mobile" onClick={() => setMenu(false)} aria-label={t("Close menu")}><X size={18} /></button></div><div className="td-workspace"><span className="td-workspace-icon">T</span><div><strong>{t("Local Workspace")}</strong><small>{data ? 'Open Source' : '—'}</small></div><span className="td-online" /></div><nav>{pages.map(([key, label, Icon], index) => <React.Fragment key={key}>{[0, 4, 6].includes(index) && <span className="td-nav-label">{index === 0 ? t("Security operations") : index === 4 ? t("Access control") : t("Administration")}</span>}<button className={page === key ? 'active' : ''} onClick={() => navigate(key)}><Icon size={18} /><span>{t(label)}</span>{key === 'broker' && data?.broker?.approvals.some(a => a.status === 'pending' && new Date(a.expires_at) > new Date()) && <i className="td-nav-dot" />}</button></React.Fragment>)}</nav><div className="td-sidebar-bottom"><FlaskConical size={18} /><div><strong>{data?.deployment ? t("Self-hosted AI Firewall") : t("Synthetic scenario environment")}</strong><small>{data?.deployment ? t("Configured destination only") : t("No external business tools")}</small></div></div></aside>{menu && <div className="td-menu-shade" onClick={() => setMenu(false)} />}<div className="td-workarea"><header className="td-topbar"><div className="td-inline"><button className="td-icon td-mobile" onClick={() => setMenu(true)} aria-label={t("Open menu")}><Menu size={20} /></button><span className="td-breadcrumb">{t("Security operations")}<span>/</span> {t(current[1])}</span></div><div className="td-inline"><LanguageSelector selfhost={auth.deployment}/><span className="td-tag demo">{data?.deployment ? t("Deployment traffic") : t("Synthetic data")}</span><span className="td-user-avatar">A</span><span className="td-user" title={session.username}>{t(session.role === 'viewer' ? 'Viewer' : 'Administrator')}</span><button className="td-icon" aria-label={t("Sign out")} title={t("Sign out")} disabled={busy} onClick={async () => {
              const result = await mutate(() => request('/logout', {}));
              if (result) {
                setSession(null);
                setData(null);
              }
            }}><LogOut size={17} /></button></div></header><main className="td-content"><div className="td-page-heading"><div><span className="td-eyebrow">TRAPDEFENSE / OPERATIONS</span><h1>{t(current[1])}</h1><p>{t(current[3])}</p></div><button className="td-btn" disabled={loading || busy} onClick={load}><RefreshCw size={15} className={loading ? 'td-spin' : ''} />{loading ? t("Loading") : t("Refresh")}</button></div>{readOnly && <div className="td-password-banner">{t('Read-only access: settings and scenario execution are disabled.')}</div>}{!session.password_changed && <div className="td-password-banner"><KeyRound size={15} /><span>{t("The default demo password is still in use.")}</span><button onClick={() => navigate('settings')}>{t("Change in Settings \u2192")}</button></div>}{!data ? <div className="td-loading">{t("Loading operational data\u2026")}</div> : <>{page === 'overview' && <Overview data={data} navigate={navigate} onSelect={setSelected} run={run} busy={busy || readOnly} />} {page === 'events' && <Events synthetic={data.synthetic} events={data.events} onSelect={setSelected} />} {page === 'policies' && <fieldset disabled={readOnly} style={{border:0,padding:0,minWidth:0}}><Policies deployment={data.deployment} brokerEnabled={data.capabilities?.broker} integrated={data.integrated} policy={data.policy} mutate={mutate} busy={busy || readOnly} /></fieldset>} {page === 'connections' && (data.deployment ? <><DeploymentSettings deployment={data.deployment} network={data.network}/><Operations policy={data.policy} readOnly={readOnly}/></> : data.integrated ? <NetworkSettings network={data.network} mutate={mutate} busy={busy || readOnly} editable={false} /> : <Connections data={data} />)} {page === 'broker' && (data.capabilities?.broker===false?<section className="td-panel"><div className="td-form-body"><h2>{t('Access Broker disabled')}</h2><p>{t('Enable Access Broker with verified JWT identity claims in deployment.yaml.')}</p><p>{t('Console SSO authenticates operators. Proxy source verification does not establish agent identity.')}</p><LanguageSelector selfhost={auth.deployment}/></div></section>:<Broker localCredentials={data.capabilities?.local_agent_credentials} broker={data.broker} mutate={mutate} busy={busy || readOnly} run={run} synthetic={data.synthetic} />)} {page === 'audit' && <Audit records={audit} />} {page === 'settings' && <>{data.deployment && <><DeploymentSettings deployment={data.deployment} network={data.network}/><Operations policy={data.policy} readOnly={readOnly}/></>} {data.integrated && <NetworkSettings network={data.network} mutate={mutate} busy={busy || readOnly} editable={!readOnly} />}<section className="td-panel"><div className="td-form-body"><h2>{t('Console identity')}</h2><p>{session.username}</p><p>{t(session.role === 'viewer' ? 'Viewer' : 'Administrator')} · {session.authentication}</p><p>{t('Console sign-in and agent authorization use separate identity boundaries.')}</p></div></section>{session.authentication === 'local' && <SettingsView deployment={data.deployment} mutate={mutate} busy={busy || readOnly} session={session} onChanged={() => {
                setSession(null);
                setData(null);
              }} />}</>}</>}<footer className="td-footer"><span>TrapDefense AI Security Gateway</span><span>{data?.deployment ? t("Only routed traffic is inspected. Target-service permissions still apply.") : t("Local synthetic demo \xB7 production performance and real IAM unverified")}</span></footer></main></div>{selected && <EventDetail event={selected} onClose={() => setSelected(null)} />}</>}</div>;
}
