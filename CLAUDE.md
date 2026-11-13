# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Two largely independent subsystems share this repo:

1. **`retrieval/` + `common/` + `corpus_sync/`** — a multilingual (Vietnamese/Chinese) medical-document
   retrieval pipeline built for a retrieval competition (code/comments refer to the organizers as "BTC").
   Chunking → embedding (BGE-M3 dense+sparse) → Qdrant indexing → hybrid search → rerank → doc/chunk
   selection → submission file.
2. **`product/`** — a separate FastAPI backend ("Family Health Assistant"): users, families, family
   members, connections, JWT auth, async SQLAlchemy/Postgres, plus an LLM agent (`product/apps/agent/`)
   whose `medical_retrieval_tool` imports `retrieval/` + `common/` to search the Qdrant collection.

Comments and CLI `--help` text in `retrieval/`, `corpus_sync/`, and `common/` are written in Vietnamese —
match that when editing those files rather than switching to English.

## Environment caveat (important)

`requirements.txt` pins the versions installed in the local `venv/`, which has both `product/` and
`retrieval/` dependencies (CPU-only torch). Indexing/search/the agent run here; chunking (`chonkie`,
`langchain-text-splitters`, not installed locally) and GPU embedding are meant for another machine.
Settings come from `.env` (template: `.env.example`): `PRODUCT_*` → `product/config.py::ProductEnv`,
unprefixed → `common/config/env.py::Env`. `git` is at `D:\Git\cmd\git.exe` and is not on this shell's PATH.

The machine has 16GB RAM and WSL2/Docker is capped at 10GB: the Qdrant collection (~3M points) uses
3–8GB, more while optimizing after bulk upserts (status `yellow`; searches can time out until `green`). Don't
run a second Qdrant container (`qdrant-r2ai`, an older copy of the same collection) alongside it.

## Commands

### `product/` (FastAPI backend — runnable here)

```powershell
# run the API (from repo root; needs postgres reachable at PRODUCT_DATABASE_URL / docker-compose below)
uvicorn product.apps.api.main:app --reload

# migrations (alembic.ini points script_location at product/db/migrations)
alembic revision --autogenerate -m "message"
alembic upgrade head
```

Config is `product/config.py` (`ProductEnv`, prefix `PRODUCT_`, reads `.env`). Note `alembic.ini` hardcodes
a sync `postgresql+psycopg2://...` URL for migrations, while the running app uses the async
`postgresql+asyncpg://...` URL from `ProductEnv.database_url` — these are deliberately different drivers
for the same database.

```powershell
docker-compose up -d     # qdrant on :6333, postgres on :5432 (user/pass/product)
```

### `retrieval/` + `corpus_sync/` (reference only in this sandbox — needs GPU/network elsewhere)

All entry points are `python -m ...` scripts under `retrieval/` and `corpus_sync/`, configured via
`common.config.Env` (`.env` at repo root) plus the YAML files in `configs/`:

```powershell
python -m corpus_sync.run_fetch --dry-run         # pull corpus/queries/precomputed chunks+vectors from HF
python -m retrieval.run_index --watch --interval 900   # chunk -> embed -> index, incrementally
python -m retrieval.run_embed --limit N
python -m retrieval.promote --min-points 1        # flip the Qdrant alias to the freshly built collection
python -m retrieval.run_queries --queries queries/query.parquet [--live] [--fresh]
python -m retrieval.run_select  # second pass over a candidate pool (tune thresholds without rerunning GPU work)
```

No test suite exists in this repo (no `tests/`, no pytest config) — don't invent test commands.

## Architecture: `retrieval/` pipeline

**Config system (`common/config/`)**: `Env` (pydantic-settings) reads `.env` for secrets/paths/HF+Qdrant
URLs. `Cfg` is a frozen, `extra="forbid"` pydantic base with a `.fingerprint()` (sha hash of its own JSON).
`load_cfg(name, Model, env)` reads `configs/<name>.yaml` and, if `env.r2ai_experiment` is set, deep-merges
`configs/exp/<experiment>/<name>.yaml` on top — that's how experiment variants are run without duplicating
whole config files.

**Fingerprint chaining (`retrieval/settings/loader.py` → `RetrievalSettings` in `bundle.py`)**: each stage's
hash *includes* the previous stage's hash: `h_chunk = chunk.fingerprint()`, `h_embed = chain(embed hash,
h_chunk)`, `h_index = chain(index hash, h_embed)`. These hashes name the on-disk/Qdrant artifacts:
- `derived/chunks/<chunk.ver>-<h_chunk[:6]>/...`
- `derived/vectors/<embed.ver>-<h_embed[:6]>/...`
- Qdrant collection `<collection_prefix>__<embed_tag>__<h_index[:4]>`

So editing any config (e.g. `configs/chunk.yaml`'s `target_tokens`) automatically produces a new directory
tree and a new Qdrant collection on the next run instead of silently mixing incompatible data — nothing is
mutated in place. `retrieval/settings/checks.py::check_compat` cross-validates configs at load time (e.g.
chunk token budget vs. embed/rerank `max_length`, `search.k_pool >= select.max_docs`).

**Incremental, shard-level processing**: corpus docs, chunks, and vectors live in shard files (parquet/
jsonl.zst). Each stage only processes shards not yet recorded as done — `retrieval/chunking` and
`retrieval/embedding` check what's missing under their respective `*_dir`, and `retrieval/index/manifest.py`
(`Manifest`, an append-only JSONL) tracks which `(collection, shard)` pairs are already upserted into Qdrant,
keyed by `(size, mtime)` file fingerprints (shards are treated as immutable, atomically-written files).
`retrieval/pipeline/cycle.py::run_cycle` runs chunk → embed → index for whatever's pending each call, and
lazy-loads the chunker/embedder model only if there's actual work (so `run_index --watch` doesn't reload
GPU models every idle poll).

**Query time (`retrieval/search/`)**: `Retriever.pools()` decomposes each query into subqueries
(`retrieval/search/decompose`, rule-based), encodes them, and runs `HybridSearcher` — a *single* Qdrant
`query_points` call per subquery using nested `Prefetch`: dense (`k_dense`) + sparse (`k_sparse`) branches
RRF-fused to `k_fuse`, then RRF-fused across subqueries to `k_pool` (`retrieval/search/fuse.py` has the
RRF math for the non-Qdrant-side merges). The pool is then reranked by a cross-encoder
(`retrieval/rerank/service.py`); only the top `rerank.top_n` chunks get a real rerank score, the remainder
keep the hybrid ordering with synthetically decaying scores appended below the reranked head so the final
sort stays well-defined. Final doc/chunk selection (`retrieval/select/`) is a separate, cheap, CPU-only pass
over an already-written candidate pool specifically so score thresholds can be tuned without rerunning
embedding/search.

**Blue-green indexing**: `retrieval.promote` only flips the `index.alias` Qdrant alias to point at the
collection named by the current config hash once it has enough points — the live alias is never written to
directly by the indexing pipeline.

**Shared contracts (`common/schema/`)**: `Doc`, `Chunk`, `Candidate`, `SparseVec` are the pydantic models
passed between stages. Comments call the crawler's doc output "contract C1" and the retrieval candidates
output "contract C2" — these are the stable interchange formats other pipeline pieces (and `corpus_sync`,
which fetches precomputed chunks/vectors from the HF dataset repo) depend on.

## Architecture: `product/` backend

Standard layered FastAPI app: `apps/api/<domain>/{router,service,schemas,deps}.py` per domain (`auth`,
`members`, `chat`, `documents`, `records`, `calendar`), SQLAlchemy models in `db/models/`, async session via `db/session.py`. Domain model: a `User`
owns a `Family`; a `Family` has `FamilyMember`s, some of which are linked to another `User` via a
`Connection` (pending/accepted/declined) rather than being purely dependent (e.g. a baby or elderly relative
with no account of their own) — `members/permissions.py::can_write_member` is the one place that encodes
"the owner manages unlinked members; a linked member manages themselves." Every member-scoped endpoint
(`/members/{member_id}/...`) takes `members/deps.py::readable_member` / `writable_member`, which return **404**
(not 403) both for unknown and forbidden members, and services return 404 for a `record_id`/`event_id` that
belongs to another member — so ids of other families can't be probed. Services raise `LookupError` (404),
`api/errors.py::ConflictError` (409) or `ValueError` (400); routers translate. Design doc:
`07_module_records_calendar.md` (deliberately without its `/api/v1` prefix — routes stay at the root).

**Proposal → confirm**: agent tools and attachment reading only create `medical_records`/`calendar_events` with
`confirmed_at=None`; only the `.../confirm` endpoints set it, and everything used for advice reads confirmed rows
only. Fields the image readers disagree on are written as `"a | b (cần kiểm tra)"` (`records/service.py::UNRESOLVED`,
also used in the system prompt); `confirm` returns 409 while any field still contains it. Recurring events are one
row with an RRULE, expanded per request by `calendar/recurrence.py` — the single place for timezone/RRULE logic,
shared by the API and `agent/tools/calendar_tool.py`.

**Agent (`apps/agent/`)**: LangChain `create_agent` over a local Ollama model (OpenAI-compatible endpoint);
`chat/service.py` calls it with `config={"configurable": {"member_id": ...}}` and tools read the member via
`tools/context.py::member_id_from(config)` — never from LLM arguments, so a prompt can't reach another
member's data. `propose_*` tools only write rows with `confirmed_at=None` (user must confirm). The chat
service prepends the member profile as a system message and appends sources if the model forgets to cite.
`vision_extract_tool` reads an uploaded `Document` with three independent readers (octochains `Engine`) and
`aggregate/consensus.py` votes per field; any disagreement → `needs_review`. Try a single image with
`python -m product.apps.agent.tools.vision_extract_tool.try_image <path>` (~3–4 min on CPU).
