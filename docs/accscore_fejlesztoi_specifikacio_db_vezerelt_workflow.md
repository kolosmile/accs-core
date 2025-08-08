# Cél és összkép

**ACCScore** egy könnyű, újra‑felhasználható Python könyvtár (lib), amely az ACCS-rendszer DB‑vezérelt workflow‑ját támogatja. A libet a **Scheduler**, a **Builder daemon** és a **Service Node Agent** importálja. A cél:

- Egységes **adatmodellek** (Pydantic) és **SQL‑műveletek** a job / task életciklushoz.
- **Globális job-sorrend** és **konkurencia** kezelés (service‑enként, node‑onként).
- **Append‑only idővonal** (task\_events) + „jelen állapot” táblák (jobs, job\_tasks).
- **MinIO** és **logger→DB** segédek.
- Opcionális **LISTEN/NOTIFY** és **Node Wake** absztrakció.

A rendszer REST‑mentes (belső indítás), minden irányítás a **Postgres** DB‑n megy keresztül. A service‑ek a DB‑ből **pullolnak** és lokálisan futnak.

---

# Komponensek és felelősségek

- **Scheduler**: workflow sablonok létrehozása (`workflows`), jobok ütemezése (`jobs.scheduled_at`, `jobs.options`).
- **Builder daemon**: figyeli a `jobs`-ot; időzítéskor **példányosítja** a job taskokat a `workflows.steps` alapján; ébreszti a szükséges node‑okat; diszpécselési szabályok (globális sorrend, retry/backoff, max concurrency); opcionális NOTIFY a service‑eknek.
- **Service Node Agent**: node regisztráció/heartbeat; **claimel** `job_tasks` sorokat; elindítja/figyeli a szolgáltatás konténert; állapotot/előzményt/artefaktot ír a DB‑be; tiszteletben tartja a kapacitást.
- **ACCScore (ez a lib)**: közös sémák, DB‑helper API-k, ordering és backoff algoritmusok, MinIO/Logging/Notify/Wake segédek.

---

# Adatmodell (SQL DDL – irányadó)

> **Megjegyzés:** a konkrét DDL Alembic migrációban készül; alább a kötelező mezők és indexek.

## `workflows`

```
id UUID PK
name TEXT
version INT
is_active BOOL DEFAULT true
steps JSONB              -- l. WorkflowStep schema
created_at timestamptz
updated_at timestamptz
UNIQUE(name, version)
```

### `steps` JSONB – példa

```json
[
  {"key":"ingest","service":"ingest","depends_on":[],"default_params":{"source":"s3://..."}},
  {"key":"audio","service":"audio-norm","depends_on":["ingest"],"default_params":{"lufs":-16}},
  {"key":"render","service":"renderer","depends_on":["audio"],"default_params":{"preset":"1080p30"}},
  {"key":"upload","service":"yt-upload","depends_on":["render"],"default_params":{}}
]
```

## `jobs`

```
id UUID PK
workflow_id UUID FK -> workflows(id)
status TEXT CHECK (status IN ('queued','running','done','error'))
progress NUMERIC
current_task_key TEXT
priority INT DEFAULT 0
order_seq BIGINT NOT NULL         -- globális sorrend (sequenceből)
options JSONB                     -- scheduler által adott beállítások
scheduled_at timestamptz
error_code TEXT, error_message TEXT
created_at timestamptz
started_at timestamptz
finished_at timestamptz
updated_at timestamptz
INDEX(status, scheduled_at)
INDEX(order_seq)
```

## `job_tasks`

```
id UUID PK
job_id UUID FK -> jobs(id)
task_key TEXT                         -- workflow.steps[].key
service_name TEXT                     -- workflow.steps[].service
status TEXT CHECK (status IN ('queued','starting','running','done','error','skipped'))
depends_on TEXT[] DEFAULT '{}'        -- a steps[] alapján kitöltve
attempt INT DEFAULT 0
max_attempts INT DEFAULT 3
next_attempt_at timestamptz
priority INT DEFAULT 0
progress NUMERIC
params JSONB                          -- default_params a workflowból (override nélkül)
results JSONB
assigned_node TEXT NULL               -- stickiness opcionális
claimed_by TEXT NULL
claimed_at timestamptz
started_at timestamptz
finished_at timestamptz
updated_at timestamptz
INDEX(service_name, status)
INDEX(job_id, status)
```

## `task_events` (append‑only idővonal)

```
id BIGSERIAL PK
job_id UUID FK -> jobs(id)
job_task_id UUID NULL FK -> job_tasks(id)
ts timestamptz NOT NULL
source TEXT             -- 'builder' | 'agent:renderer' | 'service:audio' ...
level TEXT CHECK (level IN ('debug','info','warn','error'))
type  TEXT              -- 'status'|'progress'|'log'|'artifact'|'heartbeat'|'retry'|...
message TEXT
data JSONB
INDEX(job_id, ts DESC)
INDEX(job_task_id, ts DESC)
PARTITION BY RANGE (ts)   -- havi particionálás ajánlott
```

## `task_artifacts`

```
id BIGSERIAL PK
job_id UUID FK
job_task_id UUID NULL FK
kind TEXT CHECK (kind IN ('input','output','log'))
bucket TEXT
key TEXT
size_bytes BIGINT
content_type TEXT
checksum TEXT
created_at timestamptz
INDEX(job_id)
INDEX(job_task_id)
```

## `nodes` (opcionális, ha van Node Agent + ébresztés)

```
name TEXT PK
labels JSONB                   -- pl. {"gpu": true, "zone": "eu"}
last_seen timestamptz
awake_state TEXT CHECK (awake_state IN ('unknown','awake','sleep'))
wake_method TEXT               -- 'wol'|'provider'|'script'
mac TEXT, provider_ref TEXT, script TEXT
max_concurrency JSONB          -- pl. {"renderer":2, "audio":4}
```

---

# Pydantic sémák (irányadó)

- **WorkflowDef**: `name, version, steps: list[WorkflowStep]`\
  **WorkflowStep**: `key: str, service: str, depends_on: list[str], default_params: dict`
- **Job**: `id: UUID, workflow_id: UUID, status: Status, progress: float|None, current_task_key: str|None, priority: int, order_seq: int, options: dict, scheduled_at: datetime|None, ...`
- **JobTask**: `id, job_id, task_key, service_name, status, depends_on: list[str], attempt, max_attempts, next_attempt_at, priority, progress, params: dict, results: dict, assigned_node, claimed_by, ...`
- **TaskEvent**: `job_id, job_task_id|None, ts, source, level, type, message, data`
- **TaskArtifact**: `job_id, job_task_id|None, kind, bucket, key, size_bytes, content_type, checksum, created_at`
- **Node**: `name, labels: dict, last_seen, awake_state, wake_method, mac|provider_ref|script, max_concurrency: dict`
- Enumok: `Status`, `Level`, `EventType`.

> A service‑specifikus paraméter‑sémák (pl. `RenderParams`, `NormalizeParams`) külön modulban opcionálisak; validálásra használhatók, de a DB‑ben **JSONB** marad.

---

# Ordering és claimelés (globális sorrend)

**Cél:** minden service ugyanazt a job‑sorrendet kövesse. A `jobs.order_seq` monoton nő (sequence). A claimelés rendezése **mindig** `ORDER BY jobs.order_seq ASC, jt.created_at ASC`.

**Runnable feltétel:** `jt.status='queued'` és **nincs** olyan `depends_on` task ugyanazon jobban, ami `status!='done'`.

**Biztonságos kiválasztás (pszeudo‑SQL):**

```
WITH c AS (
  SELECT jt.id
  FROM job_tasks jt
  JOIN jobs j ON j.id = jt.job_id
  WHERE jt.service_name = :service
    AND jt.status = 'queued'
    AND (jt.next_attempt_at IS NULL OR jt.next_attempt_at <= now())
    AND NOT EXISTS (
      SELECT 1 FROM job_tasks dep
      WHERE dep.job_id = jt.job_id
        AND dep.task_key = ANY(jt.depends_on)
        AND dep.status <> 'done'
    )
  ORDER BY j.order_seq ASC, jt.created_at ASC, jt.id ASC
  FOR UPDATE SKIP LOCKED
  LIMIT :capacity
)
UPDATE job_tasks t
SET status='starting', claimed_by=:agent, claimed_at=now()
FROM c
WHERE t.id = c.id
RETURNING t.*;
```

**Megjegyzések:**

- service‑enként `capacity = max_concurrency(service) - running(service)`
- opcionális „stickiness”: ha szeretnéd, `assigned_node`‑ot is feltöltheted claimkor

---

# Retry / backoff / stuck detektálás

- Hiba esetén: `attempt += 1`; ha `attempt < max_attempts`: `status='queued'`, `next_attempt_at = now() + backoff(attempt)`; különben `status='error'`.
- **Exponenciális backoff**: `base_sec * 2^(attempt-1)` (max cap)
- **Heartbeat**: service/agent 60–120 mp‑ként eventet ír (`type='heartbeat'`), vagy frissíti `job_tasks.updated_at`‑ot. Ha X percig nincs frissítés: `stuck` → retry.

---

# Builder daemon – referenciaváz (pszeudo)

- **Tick 1 – Job példányosítás**

  - `SELECT jobs WHERE status='queued' AND scheduled_at <= now()`
  - minden sorra: beolvassa a `workflows.steps`‑et → `INSERT job_tasks` (params = `default_params`, `depends_on` kitöltve)
  - `UPDATE jobs SET status='running', started_at=now(), current_task_key=első_lépés`
  - (opcionális) `NOTIFY {service_name}` új runnable taskról

- **Tick 2 – Node wake**

  - közelgő (`<= 5 min`) jobokhoz tartozó service‑ekhez szükséges címkék → `nodes` alapján „awake?”; ha nem: `wake(node)`

- **Tick 3 – Diszpécselés (ha nincs Agent és a service push‑os)**

  - csak akkor, ha nem Agent‑modellt választunk. Agent‑modellnél a service‑ek maguk claimelnek.

- **Háttér – Cleanup / Stuck**

  - lejárt heartbeatek → retry
  - kész job → `jobs.status='done'`, `finished_at=now()`

---

# Service Node Agent – referenciaváz (pszeudo)

- **Boot**: `nodes.upsert_heartbeat(node_name, labels, max_concurrency)`
- **Loop**:
  - `capacity = max_concurrency(service) - running(service)`
  - ha `capacity>0`: `db.select_runnable(service, capacity)` → claim
  - ha nem fut a konténer: `docker compose up -d <service>` (lokál)
  - indítsd a service‑t lokálban `job_task_id`‑val (REST localhost vagy közvetlen hívás)
  - futás közben: `update_task_progress`, `append_task_event`, `record_task_artifact`
  - kész/hiba: `mark_task_done/error`; ha job kész → builder cleanup tick végzi a zárást
  - idle X perc → konténer stop (opcionális gép sleep)

---

# MinIO és kulcsképzés

**Konvenció:**

- input:  `inputs/{job_id}/{task_key}/...`
- output: `outputs/{job_id}/{task_key}/….[ext]`
- log:    `logs/{job_id}/{task_key}/….jsonl`

ACCScore `storage.build_key(job_id, task_key, kind, ext=None)` segéd függvény.

---

# Logging → DB (EventBridge)

Egységes JSON‑logger, amely opcionálisan a **task\_events**‑be is ír:

- `log_event(level, type, message, data=None, job_id=None, job_task_id=None, source='service:render')`
- stdout is megmarad (Docker log), de a DB‑ben a dashboard egyszerűen lekérdezi.

---

# LISTEN/NOTIFY (opcionális)

- Csatornák service‑enként (pl. `accs_render`, `accs_audio`).
- Builder `NOTIFY`‑t küld runnable task esetén; Agent **először** NOTIFY‑ra reagál, **másodsorban** időzített poll (robosztusság).

---

# Node Wake absztrakció (opcionális)

Interface: `WakeProvider.wake(node: Node) -> bool`

- `WakeOnLAN(mac, iface)`
- `ProviderAPI(provider_ref)`
- `ShellScript(path)`

Builder: „következő 5 percben induló jobokhoz kell‑e node?” — ha igen, wake.

---

# Környezeti változók (példa)

```
ACC_DB_URL=postgresql+psycopg://user:pass@host:5432/accs
ACC_MINIO_ENDPOINT=http://minio:9000
ACC_MINIO_ACCESS_KEY=...
ACC_MINIO_SECRET_KEY=...
ACC_NODE_NAME=gpu-node-1
ACC_NODE_LABELS=gpu=true,zone=eu
ACC_MAX_CONCURRENCY_RENDER=2
ACC_MAX_CONCURRENCY_AUDIO=4
ACC_BACKOFF_BASE_SEC=15
ACC_HEARTBEAT_TTL_SEC=120
ACC_NOTIFY_CHANNEL_PREFIX=accs_
```

---

# Könyvtárstruktúra (javasolt)

```
accscore/
  __init__.py
  settings.py
  schema/
    __init__.py
    workflow.py   # WorkflowDef, WorkflowStep
    job.py        # Job, JobTask, enums
    event.py      # TaskEvent
    artifact.py   # TaskArtifact
    node.py       # Node (opcionális)
  db/
    __init__.py
    jobs.py       # create/instantiate, maybe_finish_job
    tasks.py      # select_runnable, claim, mark_*, progress, results
    events.py     # append_event
    artifacts.py  # record_artifact
    notify.py     # listen/notify helper (opcionális)
  ordering.py     # next_ordered_task(), fairness
  backoff.py      # retry/backoff, stuck
  storage.py      # MinIO wrapper + build_key()
  logging.py      # JSON logger + EventBridge
  nodes/
    __init__.py
    wake.py       # WakeProvider és implementációk
  agents/
    builder.py    # tick váz
    service.py    # agent loop váz
  version.py
```

---

# Hibakezelés és idempotencia

- **Idempotens claim**: minden claim **egy tranzakcióban** történik (`FOR UPDATE SKIP LOCKED`).
- **Idempotens start**: ugyanarra a `job_task_id`‑ra többször meghívott service‑start **no‑op** legyen (lokális védelem is).
- **Kompakt státuszátmenetek**: `queued → starting → running → done|error`.
- **Kötelező eventek**: minden váltásnál `task_events` sor.

---

# Teljesítmény és indexelés

- Kritikus indexek: `jobs(order_seq)`, `job_tasks(service_name, status, job_id)`, `task_events(job_id, ts DESC)`.
- `task_events` havi particionálása; régi partíciók archiválása MinIO‑ba (JSONL).
- JSONB kulcsokra részindex, ha gyakran szűrsz (`params ->> 'preset'`).

---

# Tesztelhetőség

- Unit tesztek: ordering, claim, retry/backoff, stuck detektálás — **DB‑in‑container** (pytest + testcontainers).
- Contract tesztek: sémák (Pydantic) és DB‑DDL összhangja.
- Füstteszt: mini workflow (2 job × 2 task) → elvárt globális sorrend.

---

# SemVer és kiadás

- `0.1.x` – Settings, sémák, DB‑helpek, ordering/backoff, storage/logging, agents vázak.
- `0.2.x` – LISTEN/NOTIFY stabilizálás, WakeProvider, CLI segédek.
- `1.0.0` – fagyasztott kontraktus, doksi, példa‑projektek.

---

# Rövid „happy path” folyam

1. Scheduler: `INSERT workflows(...)`; `INSERT jobs(status='queued', order_seq=nextval, scheduled_at=...)`.
2. Builder: időben `instantiate_tasks(job_id)`; `jobs.status='running'`.
3. Agent (render): `select_runnable('renderer', cap)` → `claim` → futtat → `mark_task_running` → `append_event(progress)` → `record_artifact` → `mark_task_done`.
4. Builder cleanup: ha minden `job_tasks.status='done'` → `jobs.status='done'`.

E specifikáció alapján a „codex” képes a lib keretrészének megírására: modulok, publikus függvények, tranzakciós szabályok, és a szükséges SQL‑minták egyértelműen adottak.

