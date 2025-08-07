# ACCS 2.1 – „Scheduler → Builder‑Core (4‑layer) → Micro‑services” architektúra

## 1  Rétegek és felelősségek

| Logikai réteg | Mi a dolga? | Tipikus konténer(ek) |
| ------------- | ----------- | -------------------- |
| **Scheduler** | Forrásfigyelés (SoundCloud‑scraper), ütemezési szabályok, kvóták, `POST /jobs`, UI‑trigger | `scheduler-api`, `sc-scraper`, `publish-planner` |
| **Builder‑Core = 4 komponens** | *a)* **Celery‑API** (vékony FastAPI: /jobs, chain‑build)<br>*b)* **Broker** (RabbitMQ / Redis)<br>*c)* **Worker‑flotta** (queue‑fogyasztók)<br>*d)* **Objektumtár + DB** (MinIO, Postgres) | `builder-api`, `rabbitmq`, `worker-cpu`, `worker-gpu`, `db`, `minio` |
| **Stateless micro‑service‑ek** | Egyetlen nehéz/független lépés (AI‑kép, GPU‑render, loudnorm) – REST/gRPC API‑val | `svc-normalize`, `svc-render-video`, `svc-generate-bg`, … |

---

## 2  Végigfutás egy trackre
```
Scheduler  --POST /jobs-->  Celery‑API (builder)
                                │  chain(ingest→normalize→render→upload)
                                ▼
                         RabbitMQ (broker)
                                │ queue: ingest
                         worker‑ingest  ──S3/DB──┐
                                │ publish normalize│
                         worker‑cpu (normalize)───┤ (HTTP) svc‑normalize
                                │ publish render  │
                         worker‑gpu (render)──────┤ (HTTP) svc‑render-video
                                │ publish upload  │
                         worker‑cpu (upload)──────┘  YouTube API
```
* 1 HTTP‑hívás után a Scheduler **azonnal** `{job_id}` választ kap.  
* A lánc minden további lépése a broker + workerek között mozog.  
* Állapot (`status`, S3‑key) a `jobs` táblában.

---

## 3  Builder‑Core részletei
| Al‑komponens | Fő processz | Példa indítás |
| ------------ | ----------- | -------------- |
| **Celery‑API** | FastAPI + `Celery(..)` *client* | `uvicorn api:app --host 0.0.0.0` |
| **Broker** | RabbitMQ / Redis | `rabbitmq:3-management` |
| **Worker** | `celery -A app worker -Q <queues> -c N` | `worker-cpu` (ingest,normalize,upload), `worker-gpu` (render) |
| **Storage** | Postgres + MinIO | `postgres:16`, `minio/minio` |

> **Egy image, több worker‑queue**: kis forgalomnál az ingest+normalize+upload futtatható egy `worker-cpu` konténerben (`-Q ingest,normalize,upload`).  
> GPU‑renderhez külön `worker-gpu` + `svc-render-video` konténer indítható.

---

## 4  Üzenet‑sorrend (Celery‑chain under the hood)
1. Celery‑API **publish** ⇒ `ingest` queue (üzenetben a `callbacks[]` teljes lánccal).  
2. `worker‑ingest` lefut → Celery‑runtime automatikusan publish `normalize` queue‑ba.  
3. `worker‑cpu` proxy‑task HTTP‑hívja `svc-normalize`‑t, visszaad → publish `render` queue.  
4. stb.  
A sorrend **csak** a `build_pipeline()` függvényben módosítható.

---

## 5  Fejlesztési / prod indító‑minták
**Fejlesztés (egyszerű):**
```yaml
services:
  builder:
    build: ./builder
    command: >
      bash -c "uvicorn api:app --port 8000 & \
               celery -A app worker -Q ingest,normalize,render,upload -c 4"
  broker: {image: rabbitmq:3-management}
  db:     {image: postgres:16}
  minio:  {image: minio/minio, command: "server /data --console-address ':9001'"}
```

**Prod (szétosztva):**
```yaml
  builder-api: {image: accs/builder-api}
  worker-cpu : {image: accs/worker-base, command: celery ... -Q ingest,normalize,upload -c 6}
  worker-gpu : {image: accs/worker-gpu , command: celery ... -Q render -c 1, deploy: {resources: {reservations: {devices: [{capabilities: ["gpu"]}]}}}}
  svc-render-video: {image: accs/svc-render-video-gpu}
```

---

## 6  Monitorozás, retry, idempotencia (magasan)
* **Celery acks\_late + retry** a worker‑taskban.  
* **Redis‑dedupe** kulcs = `task_id` (Scheduler generálja).  
* **Prometheus exporter** minden worker‑ és service‑konténerben, méri queue‑hossz, futásidő.

---

✴️ Ezzel a dokumentum már a véglegesített **Scheduler → Builder‑Core (4‑layer) → Micro‑service** felosztást mutatja, a minimális indulástól a későbbi skálázásig.

