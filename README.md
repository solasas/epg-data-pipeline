# EPG Parser & Pipeline

A daily data pipeline that downloads a public XMLTV Electronic Program Guide (TV
schedule) feed, cleans it, loads it into PostgreSQL, orchestrates the whole thing
on a schedule with Airflow, and serves it back out through a FastAPI service.

## The elevator pitch

Every day, a UK TV listings provider publishes an XMLTV file — hundreds of
channels, tens of thousands of scheduled programmes, refreshed continuously.
This project turns that raw feed into a queryable API:

```
extract.py  →  parse.py  →  transform.py  →  load.py  →  PostgreSQL  →  api.py
   (HTTP)      (XML→dict)   (clean w/ pandas)  (upsert)              (FastAPI)
```

Each arrow is a real pipeline boundary — a file gets written to disk and read
back by the next stage, the same shape Airflow later uses to run the whole
thing on a schedule. That's deliberate: it means every stage can be run,
tested, and debugged in isolation from the command line, with no orchestration
framework required to reason about it.

## Tech stack, and why each piece is here

| Layer | Choice | Why |
|---|---|---|
| Extraction | `requests` | Simple, synchronous HTTP GET — no async needed for a single daily download |
| Parsing | `lxml` | Faster and more forgiving of real-world malformed XML than the stdlib `xml.etree`; same API shape |
| Cleaning | `pandas` | Vectorized filtering/dedup/validation across 40k+ rows instead of manual loops |
| Storage | `PostgreSQL` | Relational integrity (foreign keys, uniqueness) matters here — programmes belong to channels, and "same channel + same start time" is a real constraint the DB should enforce, not just Python |
| DB driver | `psycopg2-binary` | Mature, synchronous Postgres driver; synchronous is fine since this is a batch pipeline, not a high-concurrency service |
| Orchestration | `Apache Airflow` (Docker Compose, `LocalExecutor`) | The pipeline needs to run on a schedule, retry on failure, and show run history — exactly Airflow's job. `LocalExecutor` (no Celery/Redis) because this runs on one machine |
| API | `FastAPI` + `uvicorn` | Type hints double as request validation and auto-generated OpenAPI docs, with no separate DTO/annotation layer |

## Project structure

```
extract.py                  # Downloads the XMLTV feed, saves raw_epg.xml
parse.py                    # lxml: raw_epg.xml -> (channels, programmes) list-of-dicts
transform.py                # pandas: clean, validate, dedup -> two DataFrames
load.py                     # psycopg2: upsert DataFrames into Postgres
api.py                      # FastAPI app: /channels, /schedule, /schedule/now
schema.sql                  # DDL for the channels/programmes tables
db/connection.py            # Shared psycopg2 connection helper (reads .env)
main.py                     # Entry point: runs the FastAPI app via uvicorn

airflow/dags/epg_pipeline.py  # DAG: extract -> transform -> load, daily at midnight
docker-compose.yaml            # Airflow webserver/scheduler + its own metadata Postgres
Dockerfile                     # Airflow image + this project's Python deps

requirements.txt             # Deps for running the scripts/API directly (host venv)
requirements-airflow.txt     # Same deps, installed inside the Airflow image
```

## Design decisions worth knowing (and defending)

**Natural keys instead of surrogate IDs.** `channels.channel_id` (e.g. `"5.uk"`)
is the primary key directly — no separate auto-incrementing `id` column.
`programmes` uses a *composite* primary key of `(channel_id, start_time)`,
because that pair genuinely is a programme's identity: two shows can't
legitimately start at the same instant on the same channel. A surrogate key
only earns its place when something else needs a compact, stable reference to
a row — nothing here does yet.

**Upsert, not insert.** `load.py` uses `INSERT ... ON CONFLICT (...) DO UPDATE`
because this pipeline runs daily against the *same* rolling feed. Without
upsert, every re-run would either crash on duplicate keys or double-insert
rows. The composite primary key above is exactly what makes `ON CONFLICT`
possible — the "why upsert" and "why that specific key" decisions support
each other.

**`TIMESTAMPTZ`, and UTC boundaries computed in Python, not `::date` casts.**
XMLTV timestamps carry explicit UTC offsets (`+0100`/`+0000`, BST vs. GMT).
Storing them as `TIMESTAMPTZ` preserves the correct instant regardless of
session timezone. The `/schedule?date=` filter in the API deliberately builds
explicit UTC day boundaries in Python rather than `start_time::date = %s` in
SQL — the latter would silently depend on the database session's timezone
setting, which isn't guaranteed to be UTC.

**Tasks hand data to each other via disk, not memory.** In the Airflow DAG,
`extract`, `transform`, and `load` are three separate task processes — even
under `LocalExecutor`, they don't share Python memory. `transform` pickles its
two DataFrames to `tmp/`; `load` reads them back. This mirrors the same
pattern `extract.py` already uses with `raw_epg.xml` for `parse.py` to read.

**`pandas==2.1.4`, pinned everywhere.** Airflow 2.10.3's own dependency
constraints require `pandas==2.1.4` — every current Airflow release does,
across Python versions. Rather than run two separate virtualenvs (one for the
API, one for Airflow), both `requirements.txt` and `requirements-airflow.txt`
pin the same version, so one dependency set works whether a script runs
directly on the host or inside the Airflow container.

**Docker only for Airflow, not for the data itself.** `epg_db` runs on a
locally-installed PostgreSQL, outside Docker. Airflow's webserver/scheduler
containers reach it via `host.docker.internal` (Docker Desktop's DNS name for
the host machine) rather than `localhost`, which inside a container would
mean the container itself. Airflow gets its own metadata Postgres container,
kept completely separate from the application's data.

## Getting started

```bash
# 1. Create and activate a virtualenv, install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Copy the env template and fill in real values
cp .env.example .env   # DB_USER, DB_PASSWORD, etc.

# 3. Create the database (once)
createdb epg_db

# 4. Run the pipeline manually, stage by stage
python extract.py     # -> raw_epg.xml
python parse.py       # sanity-check: prints a sample of parsed programmes
python transform.py   # sanity-check: prints cleaning summary
python load.py         # parses + transforms + upserts into epg_db, then verifies

# 5. Run the API
python main.py         # http://localhost:8000/docs for interactive Swagger UI
```

### Running the pipeline on a schedule (Airflow)

```bash
docker compose build
docker compose up airflow-init        # one-time: migrate DB, create admin user
docker compose up -d airflow-webserver airflow-scheduler
```

Open `http://localhost:8080` (`admin` / `admin`), unpause `epg_pipeline`, and
trigger a run — or let it run on its own at midnight daily.

## API reference

| Endpoint | Query params | Behavior |
|---|---|---|
| `GET /channels` | — | All channels |
| `GET /schedule` | `channel_id`, `date`, `category` (any combination, all optional) | Programmes matching the given filters, or all programmes if none are given |
| `GET /schedule/now` | — | Whatever is currently airing, across all channels |

Every endpoint returns **404** with a `{"detail": "..."}` message when a query
matches zero rows, rather than a silent empty `200` — so a typo'd
`channel_id` or an empty result is unambiguous to the caller.

## What I'd do next

- Pagination on `/schedule` (currently returns unbounded results — fine at
  ~45k rows locally, not fine at scale)
- Alerting on Airflow task failure (currently just relies on the UI/logs)
- A second XMLTV source, to prove the schema and upsert key generalize beyond
  one feed's quirks (e.g. this feed never populates `<category>`)
