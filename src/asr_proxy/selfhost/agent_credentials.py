"""Local opaque agent credentials. Only high-entropy token hashes are persisted."""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import secrets
import sqlite3
import time
from uuid import uuid4


class AgentCredentials:
  def __init__(self, path, broker, tenant_id):
    self.path=Path(path)
    self.broker,self.tenant_id=broker,tenant_id
    self.path.parent.mkdir(parents=True,exist_ok=True)
    # Create privately before SQLite opens it; never expose credential digests.
    self.path.touch(mode=0o600,exist_ok=True)
    self.path.chmod(0o600)
    with self.connect() as db:
      db.execute('CREATE TABLE IF NOT EXISTS credentials (id TEXT PRIMARY KEY, tenant TEXT NOT NULL, agent TEXT NOT NULL, digest TEXT UNIQUE NOT NULL, created REAL NOT NULL, expires REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)')

  @contextmanager
  def connect(self):
    db=sqlite3.connect(self.path,timeout=5)
    db.row_factory=sqlite3.Row
    try:
      with db:
        yield db
    finally:
      db.close()

  def _agent(self, agent_id):
    if self.broker is None:return None
    with self.broker.store.read_transaction():
      agent=self.broker.store.get_agent(agent_id)
      return agent if agent and agent.tenant_id==self.tenant_id and agent.enabled else None

  def issue(self,agent_id,ttl_seconds=86400,*,rotate_id=None):
    if type(ttl_seconds) is not int or not 60<=ttl_seconds<=2592000:
      raise ValueError('Credential lifetime must be between 60 seconds and 30 days.')
    if not self._agent(agent_id):raise ValueError('Enabled agent was not found.')
    token='td_agent_'+secrets.token_urlsafe(32)
    credential_id='key_'+uuid4().hex
    now=time.time()
    with self.connect() as db:
      db.execute('BEGIN IMMEDIATE')
      if rotate_id:
        row=db.execute('SELECT * FROM credentials WHERE id=? AND tenant=? AND agent=? AND revoked=0',
          (rotate_id,self.tenant_id,agent_id)).fetchone()
        if row is None:raise ValueError('Active credential was not found.')
        db.execute('UPDATE credentials SET revoked=1 WHERE id=?',(rotate_id,))
      db.execute('INSERT INTO credentials (id,tenant,agent,digest,created,expires) VALUES (?,?,?,?,?,?)',
        (credential_id,self.tenant_id,agent_id,hashlib.sha256(token.encode()).hexdigest(),now,now+ttl_seconds))
    return {'credential_id':credential_id,'agent_id':agent_id,'credential':token,'expires_at':now+ttl_seconds}

  def list(self,agent_id):
    with self.connect() as db:
      rows=db.execute('SELECT id,agent,created,expires,revoked FROM credentials WHERE tenant=? AND agent=? ORDER BY created DESC',
        (self.tenant_id,agent_id)).fetchall()
    return [{'credential_id':r['id'],'agent_id':r['agent'],'created_at':r['created'],
      'expires_at':r['expires'],'status':'revoked' if r['revoked'] else 'expired' if r['expires']<=time.time() else 'active'} for r in rows]

  def revoke(self,agent_id,credential_id):
    with self.connect() as db:
      result=db.execute('UPDATE credentials SET revoked=1 WHERE id=? AND tenant=? AND agent=?',
        (credential_id,self.tenant_id,agent_id))
      if not result.rowcount:raise ValueError('Credential was not found.')

  def authenticate(self,token):
    if not token.startswith('td_agent_') or len(token)!=52:return None
    with self.connect() as db:
      row=db.execute('SELECT agent FROM credentials WHERE digest=? AND tenant=? AND revoked=0 AND expires>?',
        (hashlib.sha256(token.encode()).hexdigest(),self.tenant_id,time.time())).fetchone()
    if row is None or not self._agent(row['agent']):return None
    return {'tenant_id':self.tenant_id,'agent_id':row['agent'],'authorization_mode':'agent'}
