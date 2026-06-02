# Open-Core Boundary

GitHub Opportunity Miner is intended to be an open-source, evidence-first framework for finding startup opportunities from GitHub activity.

The open-source repository should make the system inspectable, runnable, and useful for local experimentation. The paid product can build on top of it with hosted scans, premium reports, curated datasets, and higher-quality operational workflows.

## Open-Source Core

The public repository may include:

```text
LangGraph workflow
FastAPI backend
local Next.js dashboard
mock mode and sample data
basic GitHub repository and issue collection
deterministic evidence validation
SQLite local run store
basic prompts
small example badcase dataset
basic live quality runner
documentation and architecture notes
```

This layer is meant to prove the product philosophy:

```text
GitHub evidence
-> repeated production pain
-> commercial gap
-> opportunity card
-> review
-> validation action
```

## Paid / Private Layer

The following assets should stay private or be published only in limited samples:

```text
premium benchmark profiles
high-quality topic_profiles.yaml entries
full badcase dataset
live quality artifacts
best-performing prompt variants
batch scanning strategy
commercial scoring weights
curated market maps
paid report templates
customer run data
Langfuse traces and evaluation dashboards
```

These are not just implementation details. They are accumulated operating knowledge, data quality, and research workflow.

## Commercial Offers

Possible paid offerings:

```text
hosted scans
scheduled monitoring
PDF / shareable reports
team dashboard
premium benchmark datasets
curated badcase regression set
custom opportunity research
DevTool / AI infra market scan reports
```

Early manual pricing can stay simple:

```text
$19 single opportunity report
$49 deeper report with validation plan
$199 custom research for one topic
$499+ AI infra / DevTool market scan
```

## Repository Policy

Before publishing the repository:

```text
Rotate all API keys that were ever pasted locally or in chat.
Do not commit .env files.
Do not commit SQLite databases.
Do not commit live quality artifacts.
Do not commit customer data or private reports.
Do not commit Langfuse traces.
Keep only sanitized examples in examples/.
```

## License

The open-source framework is released under Apache-2.0.

Commercial services, premium datasets, hosted dashboards, private benchmark profiles, and paid reports may be offered separately.
