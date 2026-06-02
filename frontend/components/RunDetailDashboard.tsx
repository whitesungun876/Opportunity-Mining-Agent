"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, AlertCircle, Loader2 } from "lucide-react";
import {
  AgentReview,
  ClassifiedIssue,
  CommercialValidation,
  EvidenceItem,
  EvidenceReason,
  FinalDecision,
  OpportunityCardData,
  PainPoint,
  RunState,
  RunStatus,
  RunSummary,
  SignalDiagnostics,
  getRun,
  getRunOpportunities,
  getRunSummary,
  getRunStatus,
} from "@/lib/api";
import AdvancedIntelligencePanel from "./AdvancedIntelligencePanel";
import EvidenceDrawer from "./EvidenceDrawer";
import FusionDiscoveryPanel from "./FusionDiscoveryPanel";
import OpportunityCard from "./OpportunityCard";
import QueryScopeBanner from "./QueryScopeBanner";
import RunIntelligenceSummary from "./RunIntelligenceSummary";

type Props = {
  runId: string;
};

function evidenceKey(item: ClassifiedIssue | PainPoint) {
  return item.evidence_id || item.issue_id || item.evidence_ids?.[0] || "";
}

function repoLabel(item: EvidenceItem) {
  if (item.repo_owner || item.repo_name) {
    return `${item.repo_owner || ""}/${item.repo_name || ""}`.replace(/^\/|\/$/g, "");
  }
  return item.repo_url || "Unknown project";
}

function quoteFrom(item: EvidenceItem, pain?: PainPoint) {
  const quote = pain?.supporting_quote || item.body || "";
  if (quote.length <= 220) {
    return quote;
  }
  return `${quote.slice(0, 220)}...`;
}

function parseRankReason(raw?: string) {
  const value = raw || "";
  const pick = (name: string) => {
    const match = value.match(new RegExp(`${name}=(\\d+)`));
    return match ? Number(match[1]) : undefined;
  };
  return {
    matched: pick("matched"),
    comments: pick("comments"),
    reactions: pick("reactions"),
    negatives: pick("negatives"),
  };
}

function evidenceStrength(item: EvidenceItem) {
  const parsed = parseRankReason(item.rank_reason);
  const out: string[] = [];
  if (parsed.matched !== undefined) {
    out.push(`Matched ${parsed.matched} relevant production/commercial signals`);
  }
  const comments = parsed.comments ?? item.comment_count;
  if (comments) {
    out.push(`${comments} comments indicate active discussion`);
  }
  if (item.reaction_count) {
    out.push(`${item.reaction_count} reactions from users`);
  }
  return out;
}

function whyIssueMatters(issue?: ClassifiedIssue, pain?: PainPoint) {
  if (pain?.complaint) {
    const painText = humanizeUserPain(pain.complaint)?.replace(/\.$/, "");
    if (painText?.toLowerCase().startsWith("teams ")) {
      return `${painText}, which directly supports this opportunity.`;
    }
    return `Teams are struggling with ${painText?.toLowerCase()}, which directly supports this opportunity.`;
  }
  const category = issue?.category || issue?.reason;
  if (category) {
    return "This issue matters because it describes a repeatable production workflow gap, not a one-off support request.";
  }
  return "This issue is linked to a validated opportunity and has relevant production or workflow evidence.";
}

function painCategory(issue?: ClassifiedIssue, pain?: PainPoint) {
  return pain?.pain_type || issue?.category || issue?.reason || "this workflow gap";
}

function cardCommercialSignal(card: OpportunityCardData, issue?: ClassifiedIssue, pain?: PainPoint) {
  const productForm = card.product_form || card.best_product_form;
  const category = painCategory(issue, pain);
  if (productForm) {
    return `This supports demand for a ${productForm} because the issue involves ${category} in a production workflow.`;
  }
  return `This supports demand for a productized workflow around ${category}, rather than a one-off library fix.`;
}

function humanizeUserPain(value?: string) {
  const text = (value || "").trim();
  const lower = text.toLowerCase();
  if (!text) {
    return undefined;
  }
  if (lower.startsWith("need observability for failing retrieval traces")) {
    return "Teams need a practical way to inspect failing retrieval traces and identify which query, document, or model step caused the problem.";
  }
  if (lower.startsWith("missing workflow for regression datasets")) {
    return "Teams lack a repeatable workflow for comparing regression datasets before shipping RAG changes.";
  }
  if (lower.startsWith("latency spikes at scale")) {
    return "Teams see latency spikes when replaying traces at scale but cannot isolate which pipeline step is responsible.";
  }
  if (lower.startsWith("need ")) {
    return `Teams need ${text.replace(/^Need\s+/i, "").replace(/\.$/, "")}.`;
  }
  return text;
}

function buildEvidenceReasons(card: OpportunityCardData, state: RunState | null): EvidenceReason[] {
  const evidenceById = new Map<string, EvidenceItem>();
  for (const item of state?.evidence_items || []) {
    evidenceById.set(item.evidence_id, item);
  }
  const issueByEvidence = new Map<string, ClassifiedIssue>();
  for (const issue of state?.classified_issues || []) {
    const key = evidenceKey(issue);
    if (key) {
      issueByEvidence.set(key, issue);
    }
  }
  const painByEvidence = new Map<string, PainPoint>();
  for (const pain of state?.pain_points || []) {
    const key = evidenceKey(pain);
    if (key) {
      painByEvidence.set(key, pain);
    }
  }

  const out: EvidenceReason[] = [];
  for (const evidenceId of card.evidence_ids || []) {
    const item = evidenceById.get(evidenceId);
    if (!item) {
      continue;
    }
    const issue = issueByEvidence.get(evidenceId);
    const pain = painByEvidence.get(evidenceId);
    const parsedRank = parseRankReason(item.rank_reason);
    out.push({
      evidence_id: evidenceId,
      repo_label: repoLabel(item),
      repo_url: item.repo_url,
      source_url: item.source_url,
      title: item.title || evidenceId,
      why_this_matters: whyIssueMatters(issue, pain),
      user_pain: humanizeUserPain(pain?.complaint || item.title),
      commercial_signal: cardCommercialSignal(card, issue, pain),
      evidence_strength: evidenceStrength(item),
      quote: quoteFrom(item, pain),
      labels: item.labels || [],
      matched_signals: item.matched_signals || [],
      debug: {
        raw_ranking_reason: item.rank_reason,
        matched_count: parsedRank.matched,
        comments: parsedRank.comments ?? item.comment_count,
        reactions: parsedRank.reactions ?? item.reaction_count,
        negatives: parsedRank.negatives,
        classifier_category: issue?.category,
        internal_evidence_score: item.evidence_quality_score,
        raw_state_fields: {
          evidence_id: item.evidence_id,
          source_type: item.source_type,
          value_level: issue?.value_level,
          pain_id: pain?.pain_id,
          issue_id: issue?.issue_id,
        },
      },
    });
  }
  return out;
}

function toReportTitleCase(value: string) {
  const acronyms = new Set(["ai", "api", "ci", "crm", "llm", "mcp", "rag", "sdk", "sso", "ui"]);
  return value
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => {
      const lower = word.toLowerCase();
      if (acronyms.has(lower)) {
        return lower.toUpperCase();
      }
      return `${lower.slice(0, 1).toUpperCase()}${lower.slice(1)}`;
    })
    .join(" ");
}

function formatReportTitle(topic?: string | null) {
  const raw = (topic || "GitHub").trim();
  const lower = raw.toLowerCase();
  if (lower === "ai agent framework" || lower === "ai agent frameworks") {
    return "Opportunities in AI Agent Frameworks";
  }
  if (lower === "rag evaluation") {
    return "RAG Evaluation Opportunity Report";
  }
  return `${toReportTitleCase(raw)} Opportunity Report`;
}

function evidenceUrls(cards: OpportunityCardData[], state: RunState | null) {
  return [
    ...cards.flatMap((card) => card.evidence_urls || []),
    ...((state?.evidence_items || []).map((item) => item.source_url).filter(Boolean) as string[]),
  ];
}

function hasMockData(cards: OpportunityCardData[], state: RunState | null) {
  const evidence = state?.evidence_items || [];
  return (
    evidence.some((item) => item.is_mock || item.repo_owner === "mock-org" || item.repo_name?.includes("mock-org")) ||
    evidenceUrls(cards, state).some((url) => url.includes("mock-org"))
  );
}

function sourceStatusLabel(cards: OpportunityCardData[], state: RunState | null) {
  if (hasMockData(cards, state)) {
    return "Demo Data";
  }
  const urls = evidenceUrls(cards, state);
  if (urls.length > 0 && urls.every((url) => url.includes("github.com"))) {
    return "Real GitHub Sources";
  }
  return "Source Links";
}

function validationMode(cards: OpportunityCardData[]) {
  return (cards.find((card) => card.validation?.validation_mode)?.validation?.validation_mode || "strict").toLowerCase();
}

function MetricChip({ label }: { label: string }) {
  return (
    <span className="inline-flex w-fit items-center rounded-full border border-border bg-white px-2.5 py-1 text-xs font-semibold text-muted-foreground shadow-sm">
      {label}
    </span>
  );
}

function zeroValidatedReasons(summary: RunSummary, state: RunState | null) {
  if (isEvidenceScattered(summary, state)) {
    return ["We found GitHub activity, but the pain signals are spread across multiple unrelated clusters. Try focusing on one workflow."];
  }
  if (state?.signal_diagnostics?.low_signal_reason) {
    return [state.signal_diagnostics.low_signal_reason];
  }
  const reasons: string[] = [];
  const rejectedClusters = state?.rejected_pain_clusters?.length || 0;
  const painClusters = state?.pain_clusters?.length || 0;
  const generatedCards = summary.opportunity_cards_count || state?.opportunity_cards?.length || 0;
  const rejectedCards = summary.rejected_cards_count || state?.rejected_cards?.length || 0;
  if (summary.evidence_items_count > 0) {
    reasons.push("GitHub evidence was found, but strict validation requires repeated source-backed pain before a card is accepted.");
  }
  if (rejectedClusters > 0 && painClusters === 0) {
    reasons.push(`${rejectedClusters} pain clusters were filtered before card generation because they did not have enough supporting evidence.`);
  }
  if (generatedCards > 0 && rejectedCards > 0) {
    reasons.push(`${rejectedCards} generated cards were rejected because they lacked enough valid GitHub evidence links.`);
  }
  if (!reasons.length) {
    reasons.push("The quick evidence pool did not produce a strong enough production pain cluster for opportunity generation.");
  }
  return reasons;
}

function actionLabel(action: string) {
  return action
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function diagnosticMetricLabel(label: string, value?: number) {
  return (
    <div className="rounded-lg border border-amber-200 bg-white/70 p-3">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-900/80">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums text-amber-950">{value ?? 0}</p>
    </div>
  );
}

function recoveryQueries(state: RunState | null) {
  const topic = String(state?.canonical_topic || state?.user_query || "developer tools").trim();
  return {
    expand: `${topic} production debugging observability workflow`,
    broad: `${topic} self-hosted SaaS deployment blockers`,
    focused: `${topic} enterprise auth permissions audit logs`,
  };
}

function recoveryHref(query: string) {
  return `/?q=${encodeURIComponent(query)}`;
}

function zeroValidatedSuggestions(state: RunState | null) {
  if (isEvidenceScattered(undefined, state)) {
    return [
      "enterprise authentication and RBAC",
      "audit logs and compliance reporting",
      "CI security false positives",
      "deployment pain for self-hosted security tools",
    ];
  }
  const scope = typeof state?.query_scope?.scope === "string" ? state.query_scope.scope : "broad";
  if (scope === "focused") {
    return [
      "Broaden the query to the adjacent category.",
      "Add a production workflow such as deployment, observability, auth, or debugging.",
      "Try a related repo-specific analysis if you already know where the pain appears.",
    ];
  }
  if (scope === "repo_specific") {
    return [
      "Search the repo plus one concrete workflow pain.",
      "Try a broader ecosystem topic if this repository has limited repeated pain.",
      "Use smoke validation only for link testing, not quality judgment.",
    ];
  }
  return [
    "Make the query more specific by adding a production pain.",
    "Use technology + workflow + blocker, for example: MCP auth permissions for production teams.",
    "Try a repo-specific query when you know the source project.",
  ];
}

function isEvidenceScattered(summary: RunSummary | undefined, state: RunState | null) {
  const diagnostics = state?.signal_diagnostics;
  if (diagnostics?.low_signal_type === "evidence_scattered") {
    return true;
  }
  const evidenceCount = diagnostics?.evidence_items_count ?? summary?.evidence_items_count ?? state?.evidence_items?.length ?? 0;
  const filteredClusters = diagnostics?.filtered_pain_clusters_count ?? state?.rejected_pain_clusters?.length ?? 0;
  const totalClusters = diagnostics?.pain_clusters_count ?? (state?.pain_clusters?.length || 0) + filteredClusters;
  const validatedCount = diagnostics?.validated_cards_count ?? summary?.validated_cards_count ?? 0;
  return evidenceCount >= 30 && totalClusters >= 10 && validatedCount === 0;
}

function clusterTheme(cluster: Record<string, unknown>) {
  return String(cluster.theme || cluster.topic || cluster.cluster_id || "Specific workflow pain");
}

function clusterEvidenceCount(cluster: Record<string, unknown>) {
  const ids = Array.isArray(cluster.evidence_ids) ? cluster.evidence_ids : [];
  return Number(cluster.evidence_count || ids.length || 0);
}

function clusterRepoCount(cluster: Record<string, unknown>) {
  if (typeof cluster.repo_count === "number") {
    return cluster.repo_count;
  }
  const repos = Array.isArray(cluster.repo_ids) ? cluster.repo_ids : [];
  return repos.length;
}

function clusterSignals(cluster: Record<string, unknown>) {
  const raw = cluster.matched_signals || cluster.signals || cluster.positive_signals || [];
  const items = Array.isArray(raw) ? raw.map(String) : [];
  if (!items.length && cluster.pain_type) {
    items.push(String(cluster.pain_type).replaceAll("_", " "));
  }
  return items.slice(0, 4);
}

function clusterFocusedQuery(state: RunState | null, cluster: Record<string, unknown>) {
  const theme = clusterTheme(cluster)
    .replace(/\s+/g, " ")
    .split(" ")
    .slice(0, 12)
    .join(" ");
  const painType = String(cluster.pain_type || "")
    .replaceAll("_", " ")
    .trim();
  const signals = clusterSignals(cluster).slice(0, 3);
  const scopedTerms = [theme, painType, ...signals, "production workflow"]
    .filter(Boolean)
    .join(" ");
  return scopedTerms || String(state?.canonical_topic || state?.user_query || "production workflow pain");
}

function FilteredClusterChooser({ state }: { state: RunState | null }) {
  const clusters = [...(state?.rejected_pain_clusters || [])]
    .sort((left, right) => clusterEvidenceCount(right) - clusterEvidenceCount(left))
    .slice(0, 5);
  if (!clusters.length) {
    return null;
  }
  return (
    <section className="mt-4 rounded-lg border border-amber-200 bg-white/70 p-3">
      <h4 className="text-sm font-semibold text-amber-950">Choose a pain cluster to investigate</h4>
      <p className="mt-1 text-sm leading-6 text-amber-900">
        These clusters were filtered before card generation. Pick one to rerun as a focused workflow query.
      </p>
      <div className="mt-3 grid gap-2">
        {clusters.map((cluster) => {
          const theme = clusterTheme(cluster);
          const signals = clusterSignals(cluster);
          return (
            <Link
              key={String(cluster.cluster_id || theme)}
              href={recoveryHref(clusterFocusedQuery(state, cluster))}
              className="rounded-md border border-amber-100 bg-amber-50/70 p-3 transition hover:border-amber-300 hover:bg-amber-100"
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-amber-950">{theme}</p>
                  <p className="mt-1 text-xs text-amber-900/80">
                    {clusterEvidenceCount(cluster)} evidence links · {clusterRepoCount(cluster)} repos
                  </p>
                </div>
                {signals.length ? (
                  <div className="flex flex-wrap gap-1 sm:justify-end">
                    {signals.map((signal) => (
                      <span key={signal} className="rounded-full border border-amber-200 bg-white px-2 py-0.5 text-[11px] text-amber-900">
                        {signal}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

function WeakOpportunityHypotheses({ state }: { state: RunState | null }) {
  const weakCards = [...(state?.opportunity_cards || []), ...(state?.rejected_cards || [])].filter(
    (card, index, all) => all.findIndex((item) => item.opportunity_id === card.opportunity_id) === index,
  );
  if (!weakCards.length) {
    return null;
  }
  return (
    <details id="weak-opportunity-hypotheses" className="mt-4 rounded-lg border border-amber-200 bg-white/70 p-3">
      <summary className="cursor-pointer text-sm font-semibold text-amber-950">
        Weak opportunity hypotheses
      </summary>
      <p className="mt-2 text-sm leading-6 text-amber-900">
        These did not pass strict evidence validation. Use them as search directions, not validated startup opportunities.
      </p>
      <div className="mt-3 space-y-2">
        {weakCards.slice(0, 5).map((card) => (
          <div key={card.opportunity_id} className="rounded-md border border-amber-100 bg-amber-50/70 p-3">
            <p className="text-sm font-semibold text-amber-950">{card.title || card.opportunity_id}</p>
            <p className="mt-1 line-clamp-2 text-sm leading-5 text-amber-900">
              {card.pain_summary || card.commercial_gap || "Weak hypothesis without enough evidence detail."}
            </p>
            <p className="mt-1 text-xs text-amber-900/80">
              {(card.evidence_ids || []).length} evidence ids · strict validation did not accept this card
            </p>
          </div>
        ))}
      </div>
    </details>
  );
}

function ZeroValidatedDiagnosis({ summary, state }: { summary: RunSummary; state: RunState | null }) {
  const reasons = zeroValidatedReasons(summary, state);
  const suggestions = zeroValidatedSuggestions(state);
  const diagnostics: SignalDiagnostics | undefined = state?.signal_diagnostics;
  const queries = recoveryQueries(state);
  const isScattered = isEvidenceScattered(summary, state);
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-amber-950 shadow-sm">
      <div className="flex items-start gap-2">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <h3 className="text-base font-semibold">
            {isScattered
              ? "Many signals found, but they are too scattered to validate a strong opportunity."
              : "Not enough validated evidence yet"}
          </h3>
          <p className="mt-2 text-sm leading-6 text-amber-900">
            {isScattered
              ? "We found GitHub activity, but the pain signals are spread across multiple unrelated clusters. Try focusing on one workflow."
              : "We found signals, but not enough evidence to validate strong opportunities."}
          </p>
        </div>
      </div>

      {diagnostics ? (
        <div className="mt-4 grid gap-2 sm:grid-cols-4">
          {diagnosticMetricLabel("GitHub issues found", diagnostics.raw_issues_count)}
          {diagnosticMetricLabel("High-value signals", diagnostics.high_value_issues_count)}
          {diagnosticMetricLabel("Opportunity hypotheses", diagnostics.opportunity_cards_count)}
          {diagnosticMetricLabel("Validated cards", diagnostics.validated_cards_count)}
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-amber-200 bg-white/65 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">
            {diagnostics ? `Stopped at ${diagnostics.low_signal_stage.replaceAll("_", " ")}` : "Why it stopped"}
          </p>
          <ul className="mt-2 space-y-1.5 text-sm leading-6">
            {reasons.map((reason) => (
              <li key={reason}>- {reason}</li>
            ))}
          </ul>
          {diagnostics?.suggested_recovery_actions?.length ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {diagnostics.suggested_recovery_actions.slice(0, 5).map((action) => (
                <span key={action} className="rounded-full border border-amber-300 bg-amber-50 px-2 py-1 text-[11px] font-medium">
                  {actionLabel(action)}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <div className="rounded-lg border border-amber-200 bg-white/65 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">Recovery flow</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {!isScattered ? (
              <Link href={recoveryHref(queries.expand)} className="rounded-md border border-amber-300 bg-white px-2.5 py-1.5 text-xs font-semibold hover:bg-amber-100">
                Expand search
              </Link>
            ) : null}
            <a href="#weak-opportunity-hypotheses" className="rounded-md border border-amber-300 bg-white px-2.5 py-1.5 text-xs font-semibold hover:bg-amber-100">
              Show weak signals
            </a>
            {!isScattered ? (
              <Link href={recoveryHref(queries.broad)} className="rounded-md border border-amber-300 bg-white px-2.5 py-1.5 text-xs font-semibold hover:bg-amber-100">
                Try a broader topic
              </Link>
            ) : null}
            <Link href={recoveryHref(queries.focused)} className="rounded-md border border-amber-300 bg-white px-2.5 py-1.5 text-xs font-semibold hover:bg-amber-100">
              Try a focused query
            </Link>
          </div>
          <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-amber-900">Suggested refinements</p>
          <ul className="mt-2 space-y-1.5 text-sm leading-6">
            {suggestions.map((suggestion) => (
              <li key={suggestion}>- {suggestion}</li>
            ))}
          </ul>
        </div>
      </div>
      {isScattered ? <FilteredClusterChooser state={state} /> : null}
      <WeakOpportunityHypotheses state={state} />
    </div>
  );
}

function isTerminalStatus(status?: string) {
  return status === "completed" || status === "completed_with_errors";
}

function RunProgressScreen({ runId, status }: { runId: string; status: RunStatus | null }) {
  const progress = Math.max(1, Math.min(100, Math.round(status?.progress ?? 5)));
  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <Link href="/" className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition hover:text-foreground">
        <ArrowLeft className="h-4 w-4" />
        Back
      </Link>

      <section className="mt-8 rounded-xl border border-border bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase text-primary">Analysis in progress</p>
            <h1 className="mt-2 text-2xl font-semibold text-foreground">
              {status?.topic ? formatReportTitle(status.topic) : "Preparing Opportunity Report"}
            </h1>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              The backend is running GitHub search, LLM extraction, validation, and report generation in the background.
            </p>
          </div>
          <span className="w-fit rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary">
            {status?.status || "queued"}
          </span>
        </div>

        <div className="mt-5">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-foreground">{status?.message || "Starting run"}</p>
            <span className="text-sm font-semibold text-primary">{progress}%</span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-primary/10">
            <div className="h-full rounded-full bg-primary transition-all duration-700 ease-out" style={{ width: `${progress}%` }} />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
          <span className="rounded-full border border-border bg-background px-2.5 py-1">Run {runId.slice(0, 8)}</span>
          {status?.current_node ? (
            <span className="rounded-full border border-border bg-background px-2.5 py-1">
              {status.current_node.replaceAll("_", " ")}
            </span>
          ) : null}
          <span className="rounded-full border border-border bg-background px-2.5 py-1">
            {status?.dynamic_search ? "Dynamic search" : "Benchmark profile"}
          </span>
        </div>
      </section>
    </main>
  );
}

export default function RunDetailDashboard({ runId }: Props) {
  const [summary, setSummary] = useState<RunSummary | null>(null);
  const [cards, setCards] = useState<OpportunityCardData[]>([]);
  const [state, setState] = useState<RunState | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [selectedOpportunityId, setSelectedOpportunityId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    let timer: number | undefined;

    async function loadCompletedRun() {
      const [summaryPayload, opportunityPayload, statePayload] = await Promise.all([
        getRunSummary(runId),
        getRunOpportunities(runId),
        getRun(runId),
      ]);
      if (!ignore) {
        setSummary(summaryPayload);
        setCards(opportunityPayload.opportunities || []);
        setState(statePayload);
        setIsLoading(false);
      }
    }

    async function pollStatus() {
      try {
        const statusPayload = await getRunStatus(runId);
        if (ignore) {
          return;
        }
        setRunStatus(statusPayload);
        if (isTerminalStatus(statusPayload.status)) {
          await loadCompletedRun();
          return;
        }
        if (statusPayload.status === "failed") {
          setError(statusPayload.error || "Run failed.");
          setIsLoading(false);
          return;
        }
        setIsLoading(false);
        timer = window.setTimeout(pollStatus, 1500);
      } catch (err) {
        try {
          await loadCompletedRun();
        } catch {
          if (!ignore) {
            setError(err instanceof Error ? err.message : "Failed to load run.");
            setIsLoading(false);
          }
        }
      }
    }

    setIsLoading(true);
    setError(null);
    void pollStatus();
    return () => {
      ignore = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [runId]);

  const decisionsByOpportunity = useMemo(() => {
    const map = new Map<string, FinalDecision>();
    for (const decision of state?.final_decisions || []) {
      map.set(decision.opportunity_id, decision);
    }
    return map;
  }, [state?.final_decisions]);

  const reviewsByOpportunity = useMemo(() => {
    const map = new Map<string, AgentReview[]>();
    for (const review of state?.agent_reviews || []) {
      const current = map.get(review.opportunity_id) || [];
      current.push(review);
      map.set(review.opportunity_id, current);
    }
    return map;
  }, [state?.agent_reviews]);

  const evidenceReasonsByOpportunity = useMemo(() => {
    const map = new Map<string, EvidenceReason[]>();
    for (const card of cards) {
      map.set(card.opportunity_id, buildEvidenceReasons(card, state));
    }
    return map;
  }, [cards, state]);

  const commercialValidationByOpportunity = useMemo(() => {
    const map = new Map<string, CommercialValidation>();
    for (const card of cards) {
      const opportunityId = card.opportunity_id;
      map.set(opportunityId, {
        buyer: (state?.buyer_hypotheses || []).find((item) => item.opportunity_id === opportunityId),
        wtpSignals: (state?.wtp_signals || []).filter((item) => item.opportunity_id === opportunityId),
        alternatives: (state?.competitor_alternatives || []).filter((item) => item.opportunity_id === opportunityId),
        outreachTargets: (state?.outreach_targets || []).filter((item) => item.opportunity_id === opportunityId),
        validationPlan: (state?.validation_plans || []).find((item) => item.opportunity_id === opportunityId),
        startupMemo: (state?.startup_memos || []).find((item) => item.opportunity_id === opportunityId),
      });
    }
    return map;
  }, [
    cards,
    state?.buyer_hypotheses,
    state?.competitor_alternatives,
    state?.outreach_targets,
    state?.startup_memos,
    state?.validation_plans,
    state?.wtp_signals,
  ]);

  const selectedCard = cards.find((card) => card.opportunity_id === selectedOpportunityId);
  const selectedEvidenceReasons = selectedOpportunityId
    ? evidenceReasonsByOpportunity.get(selectedOpportunityId) || []
    : [];
  const isMockReport = hasMockData(cards, state);
  const modeLabel = summary?.dynamic_search ? "Dynamic Search" : "Benchmark Profile";
  const validationLabel = validationMode(cards) === "strict" ? "Strict Validation" : "Smoke Validation";
  const fusionCandidates = state?.validated_fusion_candidates || state?.fusion_candidates || [];

  if (!summary && runStatus && ["queued", "running"].includes(runStatus.status)) {
    return <RunProgressScreen runId={runId} status={runStatus} />;
  }

  if (isLoading) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-7xl items-center px-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading run
        </div>
      </main>
    );
  }

  if (error || !summary) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-8">
        <Link href="/" className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
        <div className="mt-8 rounded-lg border border-border bg-white p-4 text-sm text-destructive shadow-sm">
          {error || "Run not found."}
        </div>
      </main>
    );
  }

  return (
    <main className="soft-grid-bg min-h-dvh px-4 py-5 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1440px]">
      <div className="mb-3">
        <Link href="/" className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          Back to runs
        </Link>
      </div>

      <section className="surface-card mb-4 overflow-hidden rounded-xl px-5 py-5">
        <div className="mb-4 h-1.5 w-24 rounded-full bg-gradient-to-r from-primary via-accent to-warning" />
        <div>
          <p className="section-kicker">Opportunity report</p>
          <h1 className="mt-2 section-title sm:text-4xl">
            {formatReportTitle(summary.canonical_topic || summary.topic)}
          </h1>
          <p className="body-copy mt-2 max-w-3xl text-sm">
            {isMockReport
              ? "Demo opportunity report generated from sample data."
              : "Evidence-backed opportunity report generated from GitHub issues."}
          </p>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <MetricChip label={`${summary.validated_cards_count} Validated`} />
          <MetricChip label={`${summary.evidence_items_count} Evidence`} />
          <MetricChip label={modeLabel} />
          <MetricChip label={sourceStatusLabel(cards, state)} />
          <MetricChip label={validationLabel} />
        </div>
      </section>

      <QueryScopeBanner queryScope={state?.query_scope} />
      <RunIntelligenceSummary summary={summary} state={state} fusionCandidates={fusionCandidates} />

      {state?.errors?.length ? (
        <section className="mt-4 rounded-lg border border-destructive/25 bg-red-50 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-destructive">
            <AlertCircle className="h-4 w-4" />
            Errors summary
          </div>
          <ul className="mt-2 space-y-1 text-sm text-destructive">
            {state.errors.slice(0, 5).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="mt-4 max-w-5xl">
        <section className="space-y-4">
          <div className="flex flex-col gap-1 border-b border-border pb-3">
            <p className="section-kicker">Ranked result</p>
            <h2 className="section-title text-2xl">Top opportunities</h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Validated opportunities ranked by evidence strength and commercial potential.
            </p>
          </div>

          {cards.length === 0 ? (
            <ZeroValidatedDiagnosis summary={summary} state={state} />
          ) : (
            cards.map((card) => (
              <OpportunityCard
                key={card.opportunity_id}
                card={card}
                decision={decisionsByOpportunity.get(card.opportunity_id)}
                reviews={reviewsByOpportunity.get(card.opportunity_id) || []}
                evidenceReasons={evidenceReasonsByOpportunity.get(card.opportunity_id) || []}
                commercialValidation={commercialValidationByOpportunity.get(card.opportunity_id)}
                onOpenEvidence={setSelectedOpportunityId}
              />
            ))
          )}
        </section>
      </div>

      <FusionDiscoveryPanel candidates={fusionCandidates} />
      <AdvancedIntelligencePanel state={state} />

      <EvidenceDrawer
        open={selectedOpportunityId !== null}
        opportunityId={selectedOpportunityId}
        opportunityTitle={selectedCard?.title}
        opportunity={selectedCard}
        evidenceReasons={selectedEvidenceReasons}
        reviews={selectedOpportunityId ? reviewsByOpportunity.get(selectedOpportunityId) || [] : []}
        decision={selectedOpportunityId ? decisionsByOpportunity.get(selectedOpportunityId) : undefined}
        onClose={() => setSelectedOpportunityId(null)}
      />
      </div>
    </main>
  );
}
