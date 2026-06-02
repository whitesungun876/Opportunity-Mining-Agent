# GitHub Opportunity Miner Frontend

Minimal local dashboard for the GitHub Opportunity Miner backend.

## What It Does

The dashboard supports the Phase 5 local demo loop:

```text
enter topic
-> create run
-> view validated opportunity cards
-> open GitHub evidence drawer
-> preview and copy markdown report
```

The run detail page now uses an opportunity-result hierarchy:

```text
Report header
-> Query scope banner
-> Run intelligence summary
-> Top opportunity cards
-> Fusion discovery
-> Advanced intelligence
```

Query scope explains whether the run is broad, focused, repo-specific, or ambiguous. Run intelligence stays compact and only surfaces user-facing counts such as validated cards, evidence links, fusion candidates, capabilities, and research support.

When strict validation returns zero cards, the result page shows Low Signal Diagnostics instead of a generic low-signal message. It explains the bottleneck stage, shows issue/evidence/high-value/opportunity counts, offers recovery actions, and keeps weak opportunity hypotheses in a clearly marked collapsed section.

Fusion discovery is the Phase 6 product layer. It separates the three evidence roles:

```text
GitHub evidence = user pain
Repo capability = implementation pattern
Research = technical feasibility, not market proof
```

Capabilities, research support, and evidence graph node/edge details live under collapsed Advanced Intelligence so the result page stays focused on opportunity judgment.

Run creation is asynchronous:

```text
POST /runs/preflight
-> checks query fit and returns preflight_id
POST /runs
-> returns run_id immediately
-> homepage polls GET /runs/{run_id}/status while showing progress
-> completed runs load cards, evidence, fusion, and report data
```

High and medium preflight signals run automatically. Low or ambiguous signals pause to show refinement suggestions before spending a full LLM run.

When `preflight_id` is available, the frontend passes it into `POST /runs`. The backend can then warm-start the graph from the already ranked evidence and skip duplicate GitHub search. The default frontend run mode is `standard`, which keeps the product path fast by skipping the deeper fusion/research chain unless an API caller explicitly requests `deep`.

This keeps the UI responsive while live GitHub and LLM analysis runs in the background.

Current scope is intentionally small:

```text
No login
No payment
No deployment flow
No background queue UI
No graph visualization
No complex charts
```

## Configuration

Copy the example env file if you need to change the backend URL:

```bash
cp .env.local.example .env.local
```

Default:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Run Locally

Start the backend:

```bash
cd ../backend
uv run uvicorn app.main:app --reload
```

Start the frontend:

```bash
cd ../frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Checks

```bash
npm run lint
```

`npm run lint` runs TypeScript type checking for the minimal dashboard.

## API Used

```text
POST /runs
POST /runs/preflight
GET /runs
GET /runs/{run_id}/status
GET /runs/{run_id}
GET /runs/{run_id}/summary
GET /runs/{run_id}/opportunities
GET /runs/{run_id}/report
GET /opportunities/{opportunity_id}/evidence
```

## Next Steps

Later phases can add auth, hosted deployment, distributed workers, richer filters, and model/version comparison views.
