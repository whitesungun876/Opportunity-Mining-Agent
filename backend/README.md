# GitHub Opportunity Miner Backend

Mock-first backend for mining commercial opportunities from GitHub open-source projects.

## Architecture

The backend uses LangGraph to orchestrate:

`query_rewrite -> query_scope_detect -> intent_detect -> search_plan_generate -> github_search_orchestrator -> evidence_quality_rank -> quality_gate -> issue_classify -> pain_extract -> topic_cluster -> commercial_gap -> opportunity_generate -> evidence_validate -> advanced intelligence or report_write -> debate -> final_judge -> report_write`

Context is controlled with `ContextPacket`, tools are described through `SkillRegistry`, and execution scaffolding lives in `harness/`.

## Search Architecture

The product path uses the Dynamic Search Planner, not hand-maintained query lists.

```text
user_query
-> query_rewrite
-> query_scope_detect
-> intent_detect
-> search_plan_generate
-> github_search_orchestrator
-> evidence_quality_rank
-> quality_gate
   -> issue_classify
   -> adaptive_query_expand -> github_search_orchestrator
-> opportunity pipeline
```

`query_rewrite` builds the plan for arbitrary topics through `app/search/`:

```text
app/search/schemas.py     SearchIntent and SearchPlan contracts
app/search/scope.py       broad / focused / repo_specific / ambiguous scope detection
app/search/intent.py      intent detection: topic, repo, org, technology, problem, market
app/search/planner.py     dynamic SearchPlan generation
app/search/templates.py   topic-agnostic production/commercial signal templates
app/search/scorer.py      EvidenceQualityRanker
app/search/expansion.py   AdaptiveQueryExpander
```

The graph state keeps both legacy `github_queries` and structured search fields:

```text
search_intent
search_plan
repo_search_queries
global_issue_queries
repo_issue_queries
discussion_queries
evidence_pool
ranked_evidence_items
query_expansions
query_scope
refinement_required
suggested_queries
```

`topic_profiles.yaml` is deliberately not the product search path. Profiles are only benchmark fixtures for repeatable evaluation runs.

Two-path rule:

```text
Product path:
Dynamic Search Planner accepts arbitrary user topics and builds bounded GitHub queries.

Eval path:
topic_profiles.yaml pins benchmark inputs for apples-to-apples quality audits.
```

Do not use `topic_profiles.yaml` as a product query configuration center.

## Fusion Architecture

Phase 6 adds a lightweight Opportunity Fusion Engine:

```text
GitHub pain evidence
-> typed evidence graph
-> mature repo capability discovery
-> curated research evidence retrieval
-> fusion candidate generation
-> fusion validation
```

Fusion code lives in `app/fusion/`:

```text
schemas.py              Graph, capability, research, and fusion schemas
graph_builder.py        Typed evidence graph builder
capability_miner.py     Deterministic transferable capability mining
research_retriever.py   Curated technical feasibility evidence
fusion_generator.py     Pain x capability x research candidate generation
fusion_validator.py     Grounding and overclaim checks
```

Research evidence is only technical feasibility support. It must not be used as proof of market demand or willingness to pay.

## Commercial Validation Layer

The backend now upgrades validated opportunity cards into startup validation memos.

After evidence validation, the graph can produce:

```text
buyer_hypotheses
wtp_signals
competitor_alternatives
outreach_targets
validation_plans
startup_memos
```

Commercial validation is deterministic in the current version. It does not claim that users will pay. It only forms hypotheses from evidence-backed pain, issue metadata, comments, and opportunity card fields.

Rules:

```text
GitHub evidence proves pain, not payment.
Payment remains a hypothesis until validated with real users.
Research support proves technical feasibility, not market demand.
Issue authors are source leads, not automatically economic buyers.
Outreach targets must include source_url and must not invent private contact details.
```

The report writer renders buyer hypothesis, willingness-to-pay signal, current alternatives, first users to contact, and a seven-day validation plan for each validated opportunity.

## Run

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

## Smoke Test

```bash
uv run --extra dev python -m pytest -q
```

## Current Mode

This MVP runs in mock mode by default. Real GitHub GraphQL, real LLM calls, deterministic validation, local caching, and optional Langfuse live-eval tracing are available behind environment flags.

## Phase 1 GitHub Data Mode

Real GitHub repository search and issue collection can be enabled without changing the mock smoke tests:

```bash
MOCK_MODE=false GITHUB_TOKEN=your_github_token uv run uvicorn app.main:app --reload
```

Phase 1 only uses real GitHub GraphQL for `repo_search` and `issue_collect`. LLM reasoning, clustering, opportunity generation, debate, and reports remain mock/deterministic.

GitHub-specific API details live in `app/services/github_graphql.py`; evidence normalization lives in `app/services/evidence_normalizer.py`.

## Phase 2A LLM Classifier and Extractor

Real LLM mode is optional and only enabled when `MOCK_MODE=false` and `LLM_API_KEY` is present.

```bash
MOCK_MODE=false \
GITHUB_TOKEN=your_github_token \
LLM_API_KEY=your_llm_key \
LLM_BASE_URL=https://api.openai.com/v1 \
LLM_MODEL=gpt-4o-mini \
uv run uvicorn app.main:app --reload
```

Phase 2A only wires real LLM calls for `issue_classify` and `pain_extract`. Clustering, commercial gap detection, opportunity generation, debate, and report writing remain mock/deterministic.

The OpenAI-compatible client lives in `app/services/llm_client.py`.

## Phase 2B Commercial Gap and Opportunity Cards

Phase 2B wires real LLM calls for:

```text
commercial_gap
opportunity_generate
```

`evidence_validate` is deterministic by default. It checks:

```text
evidence_ids exist in evidence_items
source_url exists
at least 3 valid evidence ids
pricing is phrased as a hypothesis
weak_card is rejected
```

Cards with fewer than 3 evidence ids are marked `weak_card=true`. They do not enter debate in strict real mode.

Validation is controlled by `VALIDATION_MODE`:

```text
strict: require at least 3 valid evidence URLs before a card enters validated_cards
smoke: require at least 1 valid evidence URL so live smoke can test downstream debate/report flow
```

The default is `strict`. Use `smoke` only for live chain testing; `strict` is the only mode intended for real opportunity quality judgment.

Run a live smoke with validation diagnostics:

```bash
MOCK_MODE=false \
VALIDATION_MODE=smoke \
GITHUB_TOKEN=your_github_token \
LLM_API_KEY=your_llm_key \
LLM_BASE_URL=https://api.deepseek.com \
LLM_MODEL=deepseek-v4-flash \
uv run python -m app.eval.live_smoke "RAG evaluation"
```

After `evidence_validate`, the smoke output prints one diagnostic JSON line per opportunity card with `opportunity_id`, `title`, `evidence_count`, `evidence_urls_count`, `weak_card`, `validation_status`, and `rejection_reasons`.

## Phase 2C Structured Review and Report

Phase 2C wires real LLM calls for:

```text
debate
final_judge
```

The debate is a single-pass structured review by PM, Engineer, Founder, and Skeptic agents. It is not a free-form multi-round conversation.

The report writer is deterministic and does not call an LLM. It renders validated cards, final decisions, agent reviews, evidence links, validation actions, risks, and error summaries into markdown.

Reports must not introduce new facts beyond existing cards, reviews, decisions, and evidence.

### Phase 2C-Finish Completion Standard

Debate reviews are schema-normalized before they enter state:

```text
opportunity_id
agent
score
key_argument
main_risk
recommendation
```

`recommendation` is always one of `build`, `validate`, `watch`, or `reject`. Each review is force-bound to the current validated opportunity card so a malformed LLM response cannot attach a review to the wrong card.

Final decisions are also schema-normalized:

```text
opportunity_id
decision
score
best_product_form
migration_cost
reason
top_risks
first_validation_action
decision_confidence
```

`decision` is always one of `build`, `validate`, `watch`, or `reject`. Every `final_decision` must map to one `validated_card`; if there are no validated cards, `final_decisions` is empty and the graph does not fail.

The report is template-based, not a free-form LLM report. It only renders:

```text
validated_cards
final_decisions
agent_reviews
evidence_items
errors
```

Unvalidated and rejected cards are omitted from the report. Evidence sections must include GitHub `source_url` links from `evidence_items`.

## Phase 3 Embedding Clustering and Dedup

Phase 3 replaces the simplified topic clustering step with embedding-backed pain clustering and adds deduplication before evidence validation.

Embedding configuration:

```env
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_CACHE_ENABLED=true
EMBEDDING_CACHE_PATH=./data/embedding_cache.sqlite
```

If no embedding API key is configured, `EmbeddingClient` falls back to deterministic text-similarity embeddings. This keeps local tests and mock runs stable without an external provider.

Pain clustering flow:

```text
pain_points
-> coarse group by pain_type
-> embedding clustering inside each group
-> cluster dedup
-> pain_clusters
```

Each cluster includes `cluster_id`, `topic`, `theme`, `pain_type`, `pain_ids`, `evidence_ids`, `evidence_count`, `repo_count`, `severity_score`, `repetition_score`, `summary`, and `example_quotes`.

Opportunity dedup now runs before evidence validation:

```text
commercial_gap
-> opportunity_generate
-> opportunity_dedup
-> evidence_validate
```

Duplicate opportunities are detected by title, pain summary, commercial gap, and evidence overlap. The merged card preserves all evidence ids and records `merged_from`.

## Phase 4 SQLite Run Store

Phase 4 persists completed runs to SQLite so results can be queried and replayed by the API and future frontend.

Configure the database with:

```env
DATABASE_URL=sqlite:///./github_opportunity_miner.db
```

The MVP store keeps a full `state_json` for replay and also writes key outputs to queryable tables:

```text
runs
repos
evidence_items
classified_issues
pain_points
pain_clusters
commercial_gaps
opportunity_cards
validated_cards
rejected_cards
agent_reviews
final_decisions
reports
errors
```

Run the API:

```bash
uv run uvicorn app.main:app --reload
```

Create an async run:

```bash
curl -X POST http://127.0.0.1:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"topic":"RAG evaluation","dynamic_search":true}'
```

Check progress:

```bash
curl http://127.0.0.1:8000/runs/<run_id>/status
```

API endpoints:

```text
POST /runs
GET /runs/{run_id}/status
GET /runs
GET /runs/{run_id}
GET /runs/{run_id}/summary
GET /runs/{run_id}/opportunities
GET /runs/{run_id}/report
GET /opportunities/{opportunity_id}
GET /opportunities/{opportunity_id}/evidence
```

`POST /runs` returns `run_id` and `status` immediately. The MVP uses an in-process background job manager that records current graph node, progress, message, and errors. Completed runs are persisted to SQLite. A production worker such as Celery, RQ, or Dramatiq can replace the in-process manager later without changing the frontend contract.

`GET /runs` returns recent runs with topic, created time, status, validated card count, and error count.

Clear the local database:

```bash
rm -f github_opportunity_miner.db
```

If you use a custom `DATABASE_URL`, remove that SQLite file instead.

## Phase 5 Minimal Frontend Dashboard

The frontend is a local demo dashboard for creating runs and inspecting stored results.

Backend:

```bash
uv run uvicorn app.main:app --reload
```

Frontend:

```bash
cd ../frontend
npm install
npm run dev
```

Frontend API base URL:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

The dashboard supports:

```text
topic input with dynamic_search
run progress polling
validated opportunity cards
final decision and review summary
evidence drawer
markdown report preview and copy
```

It is intentionally minimal: no login, no payment, no deployment UI, and no distributed worker queue yet.

## Performance Architecture

Real LLM mode is optimized with bounded concurrency, HTTP connection reuse, and a local SQLite response cache.

Key controls:

```env
MAX_LLM_CONCURRENCY=4
MAX_GITHUB_CONCURRENCY=3
LLM_CACHE_ENABLED=true
LLM_CACHE_PATH=./data/llm_cache.sqlite
```

What runs concurrently:

```text
issue_classify:
Independent issue classification calls.

pain_extract:
Independent high-value issue extraction calls.

commercial_gap:
Independent pain cluster analysis calls.

opportunity_generate:
Independent commercial gap to card calls.

debate:
Independent card × agent review calls.

final_judge:
Independent card decision calls.

issue_collect:
Independent repo issue collection calls.
```

The cache key includes model, base URL, prompt, schema, and system prompt. Re-running the same live quality test with unchanged prompts and evidence should reuse cached structured LLM outputs.

Recommended settings:

```text
Local quality test:
MAX_LLM_CONCURRENCY=4
MAX_GITHUB_CONCURRENCY=3
LLM_CACHE_ENABLED=true

If the provider rate-limits:
MAX_LLM_CONCURRENCY=2

If results must be fully regenerated:
LLM_CACHE_ENABLED=false
```

`VALIDATION_MODE=strict` remains the only mode for real opportunity quality judgment. `VALIDATION_MODE=smoke` is only for fast chain testing.

## P0 Fast Path

Live runs use early filtering so expensive LLM and fusion stages only see the strongest candidates.

Before creating a full run, the frontend can call:

```text
POST /runs/preflight
```

Preflight is a cheap signal check:

```text
query_scope_detect
search_plan_generate with rule-based seeds only
small GitHub evidence probe
evidence_quality_rank
```

It does not call the LLM and does not generate opportunity cards. It returns `opportunity_fit` (`high`, `medium`, `low`, or `needs_refinement`), `should_run`, evidence counts, cost/runtime estimates, and suggested query refinements. High and medium signals set `should_run=true`; medium means the run is worth trying, but strict validation may still return few cards. Low-signal queries should ask the user to refine before spending a full GitHub + LLM run.

Suggested refinements should raise entrepreneurial signal instead of merely expanding keywords. The preflight layer now prefers concrete commercial validation angles:

```text
self-hosted deployment blockers
enterprise auth, permissions, and audit logs
production debugging and observability workflows
team admin dashboard workflows
managed hosted alternatives
```

These suggestions are meant to steer users away from low-signal broad topics and toward GitHub evidence that can support buyer, WTP, and validation hypotheses.

Preflight also returns a short-lived `preflight_id`. If the user confirms the run from the frontend, `POST /runs` can send that id back:

```json
{
  "topic": "RAG regression testing before deployment",
  "dynamic_search": true,
  "preflight_id": "preflight-cache-id",
  "run_mode": "standard"
}
```

The backend then warm-starts the graph from the already collected evidence and skips duplicate GitHub search. This is intentionally process-local and short-lived; it is an interaction speedup, not a persistence layer.

Run modes:

```text
quick:
run search -> classify -> extract -> cards -> deterministic validation -> report.
Fastest path for checking whether a topic has usable evidence.

standard:
default product path. Runs opportunity generation, evidence validation, debate,
commercial validation, final judge, startup memo, and report. Skips slower
fusion/research intelligence.

deep:
full research path. Includes evidence graph, capability discovery, research
retrieval, fusion generation, and fusion validation before review/report.
Use this for deeper audits, not every search.
```

Scope-aware budgets:

```text
repo_specific: collect up to 40 issues, classify top 30 ranked evidence items, extract up to 12 pains
focused:       collect up to 50 issues, classify top 45 ranked evidence items, extract up to 16 pains
broad:         collect up to 80 issues, classify top 60 ranked evidence items, extract up to 20 pains
```

Additional gates:

```text
topic_cluster:
keep clusters with at least 3 evidence links and meaningful severity/repetition.

commercial_gap:
run the LLM only on the top cluster candidates by evidence count, repetition, and severity.

opportunity_generate:
run the LLM only on top commercial gaps with at least 3 evidence ids, and avoid weak high-migration consulting-like gaps.

evidence_validate:
if no cards pass strict validation, skip evidence graph, capability discovery, research retrieval, fusion, debate, and final judge; write the report immediately.

run_mode:
`quick` skips debate/commercial validation/final judge and writes a fast evidence report.
`standard` skips evidence graph/capability/research/fusion and continues to debate plus commercial validation.
`deep` runs the full advanced-intelligence chain.
```

This keeps the product path fast enough for local demos while preserving a fuller audit trail in `evidence_items`. The `ranked_evidence_items` field is the smaller LLM candidate set; `evidence_items` remains the larger evidence set used for audit links and report grounding.

Every graph node also appends `node_latency_summary` to state. The report includes a concise Performance Summary with the slowest nodes, which makes future optimization work measurable instead of guess-based.

## Low Signal Recovery

Low signal does not always mean no opportunity exists. It can mean the query is too broad, too narrow, evidence is sparse, or strict validation blocked weak cards.

After `evidence_validate`, the graph runs `signal_diagnostics` before deciding whether to continue into review or write the report. The diagnostics object records:

```text
raw_issues_count
evidence_items_count
ranked_evidence_count
selected_repos_count
repo_coverage_count
classified_issues_count
high_value_issues_count
low_value_issues_count
pain_points_count
pain_clusters_count
filtered_pain_clusters_count
commercial_gaps_count
opportunity_cards_count
validated_cards_count
rejected_cards_count
low_signal_type
low_signal_stage
low_signal_reason
suggested_recovery_actions
```

Low-signal types:

```text
evidence_sparse:
too little usable evidence. Broaden search, add synonyms, include discussions,
or increase issue limits.

evidence_scattered:
many evidence items but too many unrelated pain clusters. Narrow to one cluster
or one workflow instead of broadening.

classifier_too_strict:
evidence exists, but too few issues are treated as high-value production or workflow pain.

validator_too_strict:
opportunity hypotheses exist, but strict grounding rejects them.
```

Possible low-signal stages:

```text
repo_search
issue_collect
evidence_rank
issue_classify
pain_extract
cluster
opportunity_generate
evidence_validate
unknown
```

Recovery actions are stage-specific. For example:

```text
repo_search:
broaden_topic, add_synonyms, try_related_terms

issue_collect:
increase_issue_limit, include_discussions, use_global_issue_search

issue_classify:
broaden_high_value_definition, include_workflow_friction, include_repeated_feature_requests

evidence_validate:
expand_search, show_weak_signals, ask_for_more_specific_query

evidence_scattered:
narrow_to_cluster, choose_specific_workflow, merge_similar_clusters, try_focused_query
```

The frontend shows these diagnostics when a run has no validated cards. For evidence-scattered runs, it should show `Choose a pain cluster to investigate` and let users rerun a focused query from a filtered cluster. Weak cards can be displayed as weak opportunity hypotheses, but they stay separate from `validated_cards`.

### Search Quality Guards

The Dynamic Search Planner is the product path. It uses benchmark profiles only in eval mode, and applies these runtime guards:

```text
Stopword filtering:
keep the original query but avoid standalone low-information terms such as
and, tools, framework, platform, or system.

GitHub query translation:
convert commercial phrases into GitHub issue language. Examples:
security compliance -> SSO, RBAC, audit logs, SOC2, permission model, OAuth
AI agent framework -> LLM agent framework, agent orchestration, agent tracing
MCP auth -> authentication, authorization, access control, OAuth, token scope

Repo anchoring:
selected repository issues receive priority. Global issue search is capped
and penalized when it drifts away from selected repos.

Generated-noise filtering:
automated digest issues are filtered before evidence ranking.

Cluster drill-down:
filtered pain clusters retain matched signals so the frontend can rerun a
focused workflow query instead of broadening again.
```

## Live Quality Audit

Use `app.eval.live_quality` for reproducible real-data quality audits. Unlike `live_smoke`, this defaults to strict validation and saves review artifacts for later inspection.

Live quality audit is a three-layer evaluation stack:

```text
app/eval/topic_profiles.yaml
-> fixed benchmark inputs such as rag_evaluation, mcp_tools, ai_agent_framework

app/eval/live_quality.py
-> injects the selected profile into the main LangGraph run
-> runs real GitHub + real LLM + deterministic validator when MOCK_MODE=false

Langfuse
-> optional trace, node spans, scores, errors, and output links for version comparison
```

Live quality uses YAML benchmark profiles from `app/eval/topic_profiles.yaml`. These profiles pin query sets for regression testing; they should not be confused with the dynamic product `SearchPlan`.

The runner still executes the main LangGraph workflow. The profile is injected during `search_plan_generate` as `SearchPlan.source=eval_profile`, replacing only the benchmark issue-query set. Product runs continue to use dynamic query planning for arbitrary user input.

List benchmark profiles:

```bash
uv run python -m app.eval.live_quality --list-profiles
```

Profile mode uses fixed benchmark inputs:

```bash
MOCK_MODE=false \
VALIDATION_MODE=strict \
GITHUB_TOKEN=your_github_token \
LLM_API_KEY=your_llm_key \
LLM_BASE_URL=https://api.deepseek.com \
LLM_MODEL=deepseek-v4-flash \
MAX_LLM_CONCURRENCY=4 \
LLM_CACHE_ENABLED=true \
uv run python -m app.eval.live_quality "RAG evaluation" --profile rag_evaluation
```

Equivalent shorter profile command:

```bash
uv run python -m app.eval.live_quality --profile rag_evaluation
```

Dynamic mode uses the product `SearchPlan` for arbitrary topics:

```bash
MOCK_MODE=false \
VALIDATION_MODE=strict \
GITHUB_TOKEN=your_github_token \
LLM_API_KEY=your_llm_key \
LLM_BASE_URL=https://api.deepseek.com \
LLM_MODEL=deepseek-v4-flash \
uv run python -m app.eval.live_quality --topic "MCP tools" --dynamic-search true
```

For an uncurated benchmark topic, omit `--profile`; the runner falls back to the `generic` profile and renders `{topic}` into reusable queries.

Artifacts are written to:

```text
data/live_quality/<run_id>/
  summary.json
  state.json
  report.md
  search_plan.json
  validation_diagnostics.json
  opportunity_cards.json
  validated_cards.json
  rejected_cards.json
  agent_reviews.json
  final_decisions.json
  evidence_items.json
  errors.json
  artifacts.json
```

`summary.json` is the quickest pass/fail view. `validation_diagnostics.json` explains why each card passed or failed strict evidence validation. `report.md` is the deterministic final report with GitHub evidence links.

When strict validation rejects cards, the runner prints `BADCASE_SNIPPETS` that can be copied into a badcase YAML file after human review. It does not automatically write new badcases.

## Badcase Regression Dataset

Badcases are curated regression tests, not ordinary logs. They capture known failure modes that should not reappear as prompts, schemas, validators, and ranking logic evolve.

Badcase files live in:

```text
app/eval/badcases/
  issue_classify.yaml
  evidence_validate.yaml
  opportunity_generate.yaml
  final_judge.yaml
```

Each badcase uses this schema:

```yaml
id: bc_issue_classify_001
stage: issue_classify
failure_type: local_environment_noise
severity: high
input:
  title: "pip install failed on my Windows machine"
  body: "..."
expected:
  value_level: low_value
  should_extract_pain: false
actual: null
fixed: false
notes: "Local environment install error should not become production pain."
```

Run all badcases:

```bash
uv run python -m app.eval.badcase_runner
```

Run one stage:

```bash
uv run python -m app.eval.badcase_runner --stage issue_classify
```

The runner writes `data/badcase_results.json`. If any badcase fails, it exits with code `1`.

## Langfuse Observability

Langfuse is optional. Install the observability extra and provide Langfuse project credentials:

```bash
uv sync --extra dev --extra observability
```

```env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_RELEASE=search-plan-v1
LANGFUSE_ENVIRONMENT=local
```

Run the same benchmark with Langfuse enabled:

```bash
MOCK_MODE=false \
VALIDATION_MODE=strict \
LANGFUSE_ENABLED=true \
GITHUB_TOKEN=your_github_token \
LLM_API_KEY=your_llm_key \
LLM_BASE_URL=https://api.deepseek.com \
LLM_MODEL=deepseek-v4-flash \
uv run --extra observability python -m app.eval.live_quality --profile rag_evaluation
```

Each run creates one Langfuse trace with one span per LangGraph node. The runner also writes trace scores for `validated_cards`, `rejected_cards`, `validated_rate`, `high_value_issues`, `pain_points`, `error_count`, `strict_pass`, and `report_has_github`.

Use `LANGFUSE_RELEASE` to label prompt, planner, or validator versions so the Langfuse dashboard can compare runs across versions.
