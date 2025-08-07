# ACCScore Library

## 1. Vízió

**ACCScore** egy központi, újra‑felhasználható Python‑csomag, amely az ACCS‑projekt minden komponense (Builder‑API, Celery‑workerek, feldolgozó FastAPI‑szolgáltatások) számára közös „ragasztókódot” biztosít.  Célja, hogy:

* **Egységesítse** a tároló‑, adatbázis‑ és üzenetküldő hívásokat.
* **Csökkentse** a duplikált kódot és konfigurációt.
* **Stabil kontraktust** (JSON‑sémák, segédfüggvények) nyújtson a belső modulok között.
* **Külső integrátoroknak** egyszerűen dokumentálható, moduláris szolgáltatásokat tegyen lehetővé.

## 2. Elhelyezkedés a rendszerben

```
Client ──► Builder‑API ──► RabbitMQ ──► Celery‑worker ──► FastAPI‑Service
            │               │                         │
            │╌╌ (accscore) ╌─┘╌╌╌╌╌╌╌╌╌╌ (accscore) ╌╌╌╌╌╌╌╌╌╌┘
                            ▼                         ▼
                         Postgres                 MinIO / S3
```

* **Builder‑API** – a kliensfelület.  ACCScore‑t használ az env‑betöltéshez, DB‑tranzakcióhoz.
* **Celery‑worker** – az orchestrátor.  ACCScore segíti a MinIO‑hívásokat, DB‑státuszfrissítést, retry‑logikát.
* **FastAPI‑Service** – a valódi feldolgozó modul (pl. normalizálás, render).  A “mode=accs” ágaon keresztül az ACCScore‑on át ír MinIO‑ba és Postgres‑be.

Így minden komponens ugyanazt a protokollt követi, miközben a service‑ek külső REST‑hívásokkal is használhatók („mode=generic”).

## 3. Fő tartalmi elemek

| Modul | Rövid szerep |
|-------|--------------|
| `settings.py` | Pydantic‑alapú környezeti változó‑loader.  Egy `.env`‑ből olvassa a MinIO, Postgres, RabbitMQ, Service‑URL‑eket. |
| `logging.py`  | Strukturált JSON‑logger, Trace‑ID beszúrással. |
| `storage.py`  | Magas szintű MinIO‑wrapper: `ensure_bucket`, `put_object`, `get_object`, `presign`. |
| `db.py`       | SQLAlchemy‑engine + `SessionLocal` context‑manager, egészség‑ellenőrző. |
| `schema/`     | Pydantic‑modellek (pl. `Job`, `JobStatus`, `AudioMeta`).  Ezek a REST‑válaszok és a DB‑rekordok *egy* forrását adják. |
| `celery_helpers.py` | Lánc‑építő, polling, retry/backoff dekorátor – hogy minden worker ugyanúgy kezelje a service‑feladatokat. |
| `version.py`  | Követhető semver: `0.1.0`, `0.2.x`, `1.x`. |

## 4. Fejlesztési és runtime előnyök

1. **DRY**: nincs nyolcszor
   ```python
   Minio(endpoint,key,secret)
   ```
   a kódban.
2. **Egy helyen frissíthető** JSON‑séma → kompatibilitási garancia.
3. **Mock‑barát**: a wrapper osztályok könnyen cserélhetők teszt‑időben.
4. **Önállóan publikálható** (pl. `pip install accscore==0.2.3`), így a service‑repo zálogra csak minimál függ.

## 5. Roadmap (semver)

* **0.1.x** – Settings, Storage, DB, alap Job‑schema.
* **0.2.x** – Celery‑helper, Trace‑ID logger, bucket‑névképzés.
* **1.0.0** – Stabilizált JSON‑kontraktusok, teljes Unit‑/Contract‑test coverage.

---

> **Röviden:**  az ACCScore a projekt *közös nyelvtana*: ugyanazt a környezeti konfigurációt olvassa minden komponens, ugyanazzal a MinIO‑/DB‑API‑val dolgozik, ugyanazokat a JSON‑modelleket cseréli.  Így a microservice‑ek lazák maradnak, de mégis **egy** konzisztens ökoszisztémát alkotnak.

