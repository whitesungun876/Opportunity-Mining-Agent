# Demo Report: Hosted Retrieval Trace Debugging Dashboard

This is a sanitized demo report. It uses sample repositories and sample evidence to show the report shape without exposing private scans, paid research, or customer data.

## Summary

Opportunity:

```text
Hosted Retrieval Trace Debugging Dashboard
```

Target user:

```text
AI engineering teams building RAG applications in production.
```

Thesis:

```text
Teams can often detect that retrieval quality is failing, but they struggle to trace which query, document, prompt, model call, or reranking step caused the failure.
```

## Evidence Summary

```text
10 sample GitHub evidence items across 5 sample projects support this opportunity.
Evidence strength: Strong
```

Sample evidence sources:

```text
https://github.com/mock-org/rag-evaluation-workflow-kit/issues/101
https://github.com/mock-org/rag-prod-observer/issues/18
https://github.com/mock-org/rag-debugging-dashboard/discussions/7
```

These links are intentionally mock-style examples. A paid or live report should replace them with real GitHub source URLs.

## User Pain

AI engineering teams running RAG systems in production need a practical way to inspect failing retrieval traces and identify which query, document, prompt, model step, or evaluation case caused the problem.

## Commercial Gap

Open-source RAG stacks provide logs, evaluation primitives, and tracing hooks, but teams still need a hosted workflow to replay failures, compare regressions, share debugging evidence, and track quality across releases.

## Product Form

```text
Hosted SaaS
```

## MVP Features

```text
Trace ingestion from LangChain and LlamaIndex
Failed retrieval replay with query, document, and prompt context
Cost and latency breakdown by pipeline step
Regression dataset comparison for recurring failures
Team dashboard for shared debugging sessions
```

## Validation Actions

```text
Contact 10 GitHub issue authors and ask how they currently debug failed retrieval traces.
Offer a free trace audit using their existing RAG logs.
Build a clickable dashboard mockup and ask if they would connect traces to it.
Post a short demo in relevant GitHub discussions and measure replies.
```

## Risks

```text
Existing observability vendors may add RAG-specific workflows.
Teams may prefer self-hosted infrastructure for sensitive traces.
The first product scope can become too broad if it tries to support every framework.
```

## Final Decision

```text
Decision: validate
Score: 74
Migration cost: low
Best product form: Hosted SaaS
```

Reason:

```text
The pain is repeated, production-oriented, and can be tested with a lightweight workflow around existing traces. The next step is demand validation with real teams.
```

## Open-Core Boundary

This demo is safe to publish because it is sanitized and does not include:

```text
private live quality artifacts
premium benchmark profiles
customer data
full paid-report details
proprietary scoring weights
```

For the commercial boundary, see:

```text
docs/OPEN_CORE.md
```
