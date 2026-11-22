"""Durable EL checkpoints shared by API processes and the server worker.

Uses the same persistent storage volume as project uploads. No browser tokens
are stored. SQLite transactions serialize control requests and worker claims.
"""
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException
from app.core.config import settings

TERMINAL = {'COMPLETED'}


class RunStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(settings.UPLOAD_DIR).resolve().parent / 'el_runs.sqlite3'

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('''CREATE TABLE IF NOT EXISTS el_runs (
            id TEXT PRIMARY KEY, owner INTEGER NOT NULL, project INTEGER NOT NULL,
            request_id TEXT NOT NULL, status TEXT NOT NULL, pause INTEGER NOT NULL DEFAULT 0,
            payload TEXT NOT NULL, checkpoint TEXT NOT NULL, result TEXT, error TEXT,
            lease TEXT, lease_until REAL NOT NULL DEFAULT 0, created REAL NOT NULL, updated REAL NOT NULL,
            UNIQUE(owner, project, request_id))''')
        db.execute('CREATE INDEX IF NOT EXISTS idx_el_runs_owner_proj_created ON el_runs(owner, project, created DESC)')
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def decode(row):
        if row is None:
            return None
        row = dict(row)
        for key in ('payload', 'checkpoint', 'result'):
            row[key] = json.loads(row[key]) if row[key] else None
        return row

    def get(self, run_id, owner=None, project=None):
        with self.connect() as db:
            row = self.decode(db.execute('SELECT * FROM el_runs WHERE id=?', (run_id,)).fetchone())
        if not row or (owner is not None and row['owner'] != owner) or (project is not None and row['project'] != project):
            raise HTTPException(404, 'Không tìm thấy tác vụ EL của bạn.')
        return row

    def latest(self, owner, project):
        with self.connect() as db:
            return self.decode(db.execute('SELECT * FROM el_runs WHERE owner=? AND project=? ORDER BY created DESC LIMIT 1', (owner, project)).fetchone())

    def create(self, owner, project, request_id, payload):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT * FROM el_runs WHERE owner=? AND project=? AND request_id=?', (owner, project, request_id)).fetchone()
            if prior:
                return self.decode(prior), False
            active = db.execute("SELECT id FROM el_runs WHERE owner=? AND project=? AND status NOT IN ('COMPLETED','FAILED')", (owner, project)).fetchone()
            if active:
                raise HTTPException(409, 'Dự án còn lượt EL đang chạy hoặc tạm dừng. Hãy tiếp tục lượt đó.')
            run_id, now = uuid.uuid4().hex, time.time()
            db.execute('INSERT INTO el_runs (id,owner,project,request_id,status,payload,checkpoint,created,updated) VALUES (?,?,?,?,?,?,?,?,?)',
                       (run_id, owner, project, request_id, 'QUEUED', json.dumps(payload, ensure_ascii=False), '{}', now, now))
        return self.get(run_id), True

    def control(self, run_id, owner, project, action):
        self.get(run_id, owner, project)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self.decode(db.execute('SELECT * FROM el_runs WHERE id=?', (run_id,)).fetchone())
            dispatch = False
            if row['status'] != 'COMPLETED':
                if action == 'pause':
                    status = 'PAUSING' if row['lease_until'] > time.time() else 'PAUSED'
                    db.execute('UPDATE el_runs SET pause=1,status=?,updated=? WHERE id=?', (status, time.time(), run_id))
                elif row['lease_until'] > time.time():
                    db.execute("UPDATE el_runs SET pause=0,status='RUNNING',updated=? WHERE id=?", (time.time(), run_id))
                else:
                    active = db.execute("SELECT id FROM el_runs WHERE owner=? AND project=? AND id<>? AND status NOT IN ('COMPLETED','FAILED')", (owner, project, run_id)).fetchone()
                    if active:
                        raise HTTPException(409, 'Dự án đang xử lý lượt EL khác. Hãy chờ lượt đó hoàn tất.')
                    dispatch = True
                    checkpoint = row['checkpoint'] or {}
                    if checkpoint.get('phase') == 'planning':
                        checkpoint['phase'] = 'ready'
                    db.execute('UPDATE el_runs SET checkpoint=? WHERE id=?', (json.dumps(checkpoint, ensure_ascii=False), run_id))
                    db.execute("UPDATE el_runs SET pause=0,status='QUEUED',error=NULL,updated=? WHERE id=?", (time.time(), run_id))
        return self.get(run_id), dispatch

    def claim(self, run_id, lease):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self.decode(db.execute('SELECT * FROM el_runs WHERE id=?', (run_id,)).fetchone())
            if not row or row['status'] in ('COMPLETED', 'FAILED', 'PAUSED'):
                return None
            if row['lease_until'] > time.time():
                return 'BUSY'
            if row['pause']:
                db.execute("UPDATE el_runs SET status='PAUSED',lease=NULL,lease_until=0 WHERE id=?", (run_id,))
                return None
            db.execute("UPDATE el_runs SET status='RUNNING',lease=?,lease_until=?,updated=? WHERE id=?", (lease, time.time()+120, time.time(), run_id))
        return self.get(run_id)

    def save(self, run_id, lease, checkpoint=None, status=None, result=None, error=None):
        assignments, values = ['updated=?'], [time.time()]
        for key, value in (('checkpoint', checkpoint), ('status', status), ('result', result), ('error', error)):
            if value is not None:
                assignments.append(key+'=?')
                values.append(json.dumps(value, ensure_ascii=False, default=str) if key in ('checkpoint', 'result') else value)
        if status in ('PAUSED', 'FAILED', 'COMPLETED'):
            assignments.extend(['lease=NULL', 'lease_until=0'])
        else:
            assignments.append('lease_until=?')
            values.append(time.time()+120)
        with self.connect() as db:
            changed = db.execute('UPDATE el_runs SET '+','.join(assignments)+' WHERE id=? AND lease=?', (*values, run_id, lease)).rowcount
        if not changed:
            raise RuntimeError('EL worker no longer owns this run')

    def dispatch_failed(self, run_id):
        with self.connect() as db:
            db.execute("UPDATE el_runs SET status='FAILED',error=?,updated=? WHERE id=? AND status='QUEUED'",
                       ('Chưa gửi được tác vụ đến worker. Bạn có thể tiếp tục để thử lại.', time.time(), run_id))


def public_run(row):
    if not row:
        return None
    state = row['checkpoint'] or {}
    return {k: row[k] for k in ('id', 'project', 'status', 'error', 'created', 'updated')} | {
        'message': row['payload']['message'], 'activities': state.get('activities', []),
        'result': row['result'], 'pause_requested': bool(row['pause'])}
