# digime — your digital footprint, turned into a queryable memory

A local tool that consolidates your Google Workspace history and browsing activity
into a single Neo4j knowledge graph — one store for both the *relationships*
between things and the *semantic* search over them.

## What it ingests

| Source | How it's fetched | What you get |
|---|---|---|
| YouTube watch history | Google Takeout (`watch-history.json`) | Every video you've watched, timestamped |
| Google My Activity / search | Google Takeout (`My Activity/**/*.json`) | Searches, app usage, activity events |
| Gmail | Google Takeout (`Mail/*.mbox`) | Your emails as retrievable text |
| Browser history | Chrome `History` SQLite (read directly) | Pages visited, incl. YouTube, going forward |

### Why Takeout for YouTube/Activity?
There is **no official API** for YouTube watch history or Google "My Activity".
The YouTube Data API dropped watch-history access years ago. The only sanctioned
way to get *past* history is Google Takeout (an occasional manual export).

### Forward-looking coverage
To capture activity *from now on* without waiting for Takeout, the Chrome history
reader pulls YouTube/page visits directly from your profile. For richer, real-time
capture (watch duration, cross-device), the roadmap below adds a browser extension.

## How it works — a single store

```
Google Takeout (JSON/MBOX) ──┐
Chrome History (SQLite) ──────┤→ ingest → normalize → Memory records
                              │
                              ▼
                    embed (local ONNX MiniLM, 384-dim)
                              │
                              ▼
                         Neo4j (single DB)
              ┌───────────────┴───────────────┐
              │                               │
     graph: entities + edges           vector index: semantic search
     (:Person, :Channel, :Topic…)      (:Memory.embedding)
              │                               │
              ▼                               ▼
  graph query "who do I email most?"   ask "what did I watch about X?"
```

Every content record becomes a `(:Memory)` node (also carrying a type label —
`:Video`, `:Email`, `:Activity`, `:Browser`) with an `embedding` property, and is
connected to entity nodes (`:Person`, `:Channel`, `:Topic`) and the `(:Me)`
anchor. A Neo4j **vector index** on `(:Memory).embedding` powers semantic search,
so both questions — *relational* and *semantic* — are answered by the same
database.

## The knowledge graph

| Node | Meaning |
|---|---|
| `(:Me)` | you, the anchor |
| `(:Person)` | email correspondents |
| `(:Memory)` | every content record (has `embedding`) |
| `(:Video)` / `(:Email)` / `(:Activity)` / `(:Browser)` | type labels on `:Memory` |
| `(:Channel)` | YouTube channels |
| `(:Topic)` | keywords extracted from titles/subjects |

Relationships: `WATCHED`, `SEARCHED`, `SENT`/`RECEIVED`, `BY`, `ABOUT`,
`CORRESPONDS_WITH`.

## Setup

```bash
cd digime
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Start Neo4j 5.11+ (native vector index support) — or use AuraDB
export NEO4J_PASSWORD=change-me
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH="neo4j/${NEO4J_PASSWORD}" neo4j:5
```

Copy the example config. `config.yaml` is gitignored, so your paths and
credentials never leave your machine:

```bash
cp config.example.yaml config.yaml
```

```yaml
neo4j:
  uri: bolt://localhost:7687
  user: neo4j
  # Resolved from the environment — never commit a real password.
  password: ${NEO4J_PASSWORD}
  database: neo4j
  me_email: you@example.com

sources:
  takeout:
    enabled: true
    path: /path/to/unzipped/Takeout
  browser_history:
    enabled: true
    chrome_profile: "/Users/you/Library/Application Support/Google/Chrome/Default"
```

## Usage

```bash
digime ingest                 # pull Takeout + browser history into Neo4j (graph + vectors)
digime ask "videos I watched about neural networks"
digime ask "emails with landlord about the lease"

# graph queries
digime graph --query contacts      # people you email most
digime graph --query channels      # channels you watch most
digime graph --query topics        # topic frequency
digime graph --query stats         # node/edge counts
digime graph --query paths --param name neural   # shortest path me → topic
digime graph --cypher "MATCH (p:Person) RETURN p"
```

To get LLM-generated answers instead of raw matches, install Ollama and set in
`config.yaml`:

```yaml
llm:
  ollama_model: llama3.1
```

## Design notes

- **Embeddings**: computed locally with ONNX MiniLM (384-dim, via chromadb's
  embedding function, used purely as a model — the data lives only in Neo4j).
- **Re-ingesting is idempotent**: each `:Memory` node has a deterministic
  content-derived `id`, so `digime ingest` can run repeatedly without duplicates.
- **Everything is local.** Your data never leaves the machine unless you add an LLM API.

## Feasibility notes (the honest parts)

- **YouTube/Activity = Takeout only.** No live API, no Takeout automation. Manual refresh.
- **Gmail via Takeout = snapshot.** Live Gmail sync needs OAuth (Google API) — a clear next step.
- **The persona is retrieval + generation.** True "clone my voice/decisions" needs a
  style-tuning step on top of retrieval, which is a later, optional layer.

## Roadmap

1. **Live Gmail/Drive/Calendar** via Google OAuth (`google-api-python-client`).
2. **Browser extension** for real-time watch/activity capture with duration.
3. **Style clone** — fine-tune or few-shot on your writing to generate in your voice.
4. **Scheduled ingestion** — cron/daemon to keep the store fresh automatically.
5. **Hybrid search** — combine vector + full-text index for keyword-sensitive recall.
