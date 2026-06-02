"use client";

import { ChevronDown, ExternalLink, GitBranch, Info, MessageSquareText, Quote, Scale, ShieldAlert, Signal, X } from "lucide-react";
import { AgentReview, EvidenceReason, FinalDecision, OpportunityCardData } from "@/lib/api";

type Props = {
  opportunityId: string | null;
  opportunityTitle?: string;
  opportunity?: OpportunityCardData;
  evidenceReasons: EvidenceReason[];
  reviews?: AgentReview[];
  decision?: FinalDecision;
  open: boolean;
  onClose: () => void;
};

function groupedByRepo(items?: EvidenceReason[]) {
  const groups = new Map<string, EvidenceReason[]>();
  for (const item of items || []) {
    const current = groups.get(item.repo_label) || [];
    current.push(item);
    groups.set(item.repo_label, current);
  }
  return Array.from(groups.entries()).map(([repo, evidence]) => ({ repo, evidence }));
}

function displayOpportunityTitle(title?: string | null) {
  const value = (title || "").trim();
  const lower = value.toLowerCase();
  if (lower.includes("observability") && lower.includes("retrieval")) {
    return "Hosted Retrieval Trace Debugging Dashboard";
  }
  if (lower.includes("latency") && lower.includes("trace")) {
    return "RAG Trace Latency Diagnostics Service";
  }
  if (lower.includes("evaluation gates") || lower.includes("deployment")) {
    return "Production Evaluation Gate for RAG Deployments";
  }
  if (lower.startsWith("need ")) {
    return `Opportunity: ${value.replace(/^Need\s+/i, "")}`;
  }
  return value;
}

function evidenceStrengthLabel(evidenceCount: number, projectCount: number) {
  if (evidenceCount >= 8 && projectCount >= 3) {
    return "Strong";
  }
  if (evidenceCount >= 3 && projectCount >= 2) {
    return "Medium";
  }
  return "Weak";
}

function shortOpportunityThesis(opportunity?: OpportunityCardData, title?: string | null) {
  const source = `${opportunity?.pain_summary || ""} ${opportunity?.commercial_gap || ""} ${displayOpportunityTitle(title)}`.toLowerCase();
  if (source.includes("retrieval") || source.includes("trace")) {
    return "retrieval trace debugging and regression workflow gaps before shipping RAG systems";
  }
  if (source.includes("latency")) {
    return "latency diagnosis gaps during RAG evaluation and trace replay";
  }
  if (source.includes("deployment") || source.includes("evaluation gate")) {
    return "evaluation gates and regression checks before production deployment";
  }
  if (source.includes("permission") || source.includes("enterprise") || source.includes("rbac")) {
    return "enterprise permission, audit, and team-workflow gaps in production adoption";
  }
  if (source.includes("ci")) {
    return "CI workflow gaps for teams shipping RAG quality checks";
  }
  const fallback = opportunity?.pain_summary || opportunity?.commercial_gap || "a repeated production workflow gap";
  return fallback.replace(/\.$/, "").slice(0, 150);
}

function strengthClassName(strength: string) {
  if (strength === "Strong") {
    return "border-emerald-200 bg-emerald-50 text-emerald-900";
  }
  if (strength === "Medium") {
    return "border-blue-200 bg-blue-50 text-blue-900";
  }
  return "border-amber-200 bg-amber-50 text-amber-900";
}

function sourceClassName(isDemo: boolean, isEvidenceBacked: boolean) {
  if (isDemo) {
    return "border-amber-200 bg-amber-50 text-amber-900";
  }
  if (isEvidenceBacked) {
    return "border-emerald-200 bg-emerald-50 text-emerald-900";
  }
  return "border-border bg-background text-muted-foreground";
}

function sourceLabel(isDemo: boolean, isEvidenceBacked: boolean) {
  if (isDemo) {
    return "Demo Data";
  }
  if (isEvidenceBacked) {
    return "Real GitHub Sources";
  }
  return "Source Links";
}

function evidenceHeaderTitle(title?: string | null, opportunityId?: string | null) {
  const displayTitle = displayOpportunityTitle(title);
  if (displayTitle) {
    return `Evidence for ${displayTitle}`;
  }
  return opportunityId ? `Evidence for ${opportunityId}` : "Evidence for this opportunity";
}

function HeaderChip({ label, className = "" }: { label: string; className?: string }) {
  return (
    <span className={`inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-xs font-medium ${className || "border-border bg-background text-muted-foreground"}`}>
      {label}
    </span>
  );
}

function evidenceMetrics(item: EvidenceReason) {
  const matched = item.debug?.matched_count ?? item.matched_signals.length;
  const comments = item.debug?.comments ?? 0;
  return { matched, comments };
}

function evidenceItemStrength(item: EvidenceReason) {
  const { matched, comments } = evidenceMetrics(item);
  if (matched >= 6 || comments >= 8) {
    return "Strong";
  }
  if (matched >= 3 || comments >= 3) {
    return "Supporting";
  }
  return "Weak";
}

function itemStrengthLabel(strength: string) {
  if (strength === "Strong") {
    return "Strong evidence";
  }
  if (strength === "Supporting") {
    return "Supporting evidence";
  }
  return "Weak signal";
}

function itemStrengthClassName(strength: string) {
  if (strength === "Strong") {
    return "border-emerald-200 bg-emerald-50 text-emerald-900";
  }
  if (strength === "Supporting") {
    return "border-blue-200 bg-blue-50 text-blue-900";
  }
  return "border-amber-200 bg-amber-50 text-amber-900";
}

function hasOnlyRealGithubSources(items: EvidenceReason[]) {
  return (
    items.length > 0 &&
    items.every((item) => item.source_url?.startsWith("https://github.com/") && !item.source_url.includes("mock-org"))
  );
}

function hasDemoEvidence(items: EvidenceReason[]) {
  return items.some(
    (item) =>
      item.repo_label.includes("mock-org") ||
      item.repo_url?.includes("mock-org") ||
      item.source_url?.includes("mock-org"),
  );
}

function SectionLabel({ children, tone = "neutral" }: { children: string; tone?: "neutral" | "green" }) {
  const toneClass =
    tone === "green"
      ? "text-emerald-800"
      : "text-muted-foreground";
  return (
    <p className={`label-copy ${toneClass}`}>
      {children}
    </p>
  );
}

export default function EvidenceDrawer({
  opportunityId,
  opportunityTitle,
  opportunity,
  evidenceReasons,
  reviews = [],
  decision,
  open,
  onClose,
}: Props) {
  if (!open) {
    return null;
  }

  const groups = groupedByRepo(evidenceReasons);
  const evidenceCount = evidenceReasons.length;
  const projectCount = groups.length;
  const evidenceStrength = evidenceStrengthLabel(evidenceCount, projectCount);
  const isEvidenceBacked = hasOnlyRealGithubSources(evidenceReasons);
  const isDemo = hasDemoEvidence(evidenceReasons);
  const thesis = shortOpportunityThesis(opportunity, opportunityTitle);
  const headerTitle = evidenceHeaderTitle(opportunityTitle, opportunityId);

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        className="absolute inset-0 bg-foreground/30"
        onClick={onClose}
        aria-label="Close evidence drawer"
      />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-3xl flex-col bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-border bg-gradient-to-r from-white via-sky-50/55 to-teal-50/60 px-5 py-4">
          <div className="min-w-0">
            <p className="section-kicker">Opportunity evidence</p>
            <h2 className="mt-1 text-2xl font-bold leading-tight tracking-normal text-foreground">
              {headerTitle}
            </h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">GitHub source review for the opportunity thesis.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <HeaderChip label={`${projectCount} Projects`} />
              <HeaderChip label={`${evidenceCount} Evidence`} />
              <HeaderChip label={`${evidenceStrength} Signal`} className={strengthClassName(evidenceStrength)} />
              <HeaderChip label={sourceLabel(isDemo, isEvidenceBacked)} className={sourceClassName(isDemo, isEvidenceBacked)} />
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-border text-muted-foreground transition hover:bg-muted hover:text-foreground"
            aria-label="Close evidence drawer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          <section className="mb-4 rounded-xl border border-blue-100 bg-blue-50/45 px-4 py-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="label-copy text-blue-800">Evidence summary</p>
                <h3 className="mt-1 text-base font-semibold text-foreground">What the evidence supports</h3>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {evidenceCount} GitHub items across {projectCount} projects repeatedly support this opportunity: {thesis}.
                </p>
              </div>
            </div>
          </section>

          {groups.length === 0 ? (
            <p className="text-sm text-muted-foreground">No evidence returned for this opportunity.</p>
          ) : (
            <div className="space-y-4">
              {groups.map((group) => {
                const repoLabel = `Repo: ${group.repo}`;
                return (
                <section key={group.repo} className="overflow-hidden rounded-xl border border-border shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-50 px-4 py-3">
                    {group.evidence[0]?.repo_url ? (
                      <a
                        href={group.evidence[0].repo_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-2 text-sm font-semibold text-foreground underline-offset-2 hover:underline"
                      >
                        <GitBranch className="h-4 w-4 text-muted-foreground" />
                        {repoLabel}
                      </a>
                    ) : (
                      <p className="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                        <GitBranch className="h-4 w-4 text-muted-foreground" />
                        {repoLabel}
                      </p>
                    )}
                    <span className="rounded-md bg-white px-2 py-1 text-xs font-medium text-muted-foreground">
                      {group.evidence.length} item{group.evidence.length > 1 ? "s" : ""}
                    </span>
                  </div>

                  <div className="divide-y divide-border bg-white">
                    {group.evidence.map((item) => {
                      const strength = evidenceItemStrength(item);
                      const metrics = evidenceMetrics(item);
                      const visibleTags = item.matched_signals.slice(0, 4);
                      const hiddenTagCount = Math.max(0, item.matched_signals.length - visibleTags.length);
                      return (
                      <article key={item.evidence_id} className="px-4 py-4">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div className="min-w-0">
                            <h3 className="text-base font-bold leading-snug text-foreground">
                              {item.title}
                            </h3>
                            <p className="mt-1 text-xs font-medium text-muted-foreground">{item.repo_label}</p>
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {visibleTags.map((signal) => (
                                <span
                                  key={signal}
                                  className="rounded-md border border-border bg-muted px-2 py-1 text-xs font-medium text-muted-foreground"
                                >
                                  {signal}
                                </span>
                              ))}
                              {hiddenTagCount > 0 ? (
                                <span className="rounded-md border border-border bg-white px-2 py-1 text-xs font-medium text-muted-foreground">
                                  +{hiddenTagCount} more
                                </span>
                              ) : null}
                            </div>
                          </div>
                        </div>

                        <div className="mt-3 rounded-md border border-border bg-background px-3 py-3">
                          <p className="text-sm leading-6 text-foreground">{item.why_this_matters}</p>
                          <div className="mt-3 flex flex-wrap items-center gap-2">
                            <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${itemStrengthClassName(strength)}`}>
                              {itemStrengthLabel(strength)}
                            </span>
                            <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-white px-2 py-1 text-xs font-medium text-muted-foreground">
                              <Signal className="h-3.5 w-3.5" />
                              Matched {metrics.matched} signals
                            </span>
                            <span className="rounded-md border border-border bg-white px-2 py-1 text-xs font-medium text-muted-foreground">
                              {metrics.comments} comments
                            </span>
                          </div>
                        </div>

                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          {item.source_url ? (
                            <a
                              href={item.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex min-h-10 shrink-0 items-center justify-center gap-2 rounded-md border border-border bg-white px-3 text-sm font-semibold text-foreground transition hover:bg-muted"
                            >
                              <ExternalLink className="h-4 w-4" />
                              Open GitHub issue
                            </a>
                          ) : null}
                        </div>

                        <details className="mt-3 rounded-md border border-border bg-white">
                          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 text-sm font-semibold text-muted-foreground">
                            <span>Expand details</span>
                            <ChevronDown className="h-4 w-4" />
                          </summary>
                          <div className="grid gap-3 border-t border-border bg-background px-3 py-3">
                            {item.user_pain ? (
                              <div className="rounded-md border border-border bg-white px-3 py-3">
                                <SectionLabel>User pain</SectionLabel>
                                <p className="mt-2 text-sm leading-6 text-foreground">{item.user_pain}</p>
                              </div>
                            ) : null}
                            {item.commercial_signal ? (
                              <div className="rounded-md border border-emerald-100 bg-emerald-50/60 px-3 py-3">
                                <SectionLabel tone="green">Commercial signal</SectionLabel>
                                <p className="mt-2 text-sm leading-6 text-emerald-950">{item.commercial_signal}</p>
                              </div>
                            ) : null}
                            {item.quote ? (
                              <div className="flex gap-2 border-l-2 border-border pl-3 text-sm leading-6 text-muted-foreground">
                                <Quote className="mt-1 h-3.5 w-3.5 shrink-0" />
                                <p>{item.quote}</p>
                              </div>
                            ) : null}

                            <details className="rounded-md border border-border bg-white">
                              <summary className="cursor-pointer px-3 py-2 text-sm font-semibold text-muted-foreground marker:text-muted-foreground">
                                <span className="inline-flex items-center gap-2">
                                  <Info className="h-3.5 w-3.5" />
                                  Debug details
                                </span>
                              </summary>
                              <div className="space-y-2 border-t border-border px-3 py-3 text-xs text-muted-foreground">
                                <div className="flex items-start gap-2">
                                  <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                                  <div className="space-y-1">
                                    <p>Raw ranking reason: {item.debug?.raw_ranking_reason || "n/a"}</p>
                                    <p>Matched count: {item.debug?.matched_count ?? "n/a"}</p>
                                    <p>Reactions: {item.debug?.reactions ?? "n/a"}</p>
                                    <p>Negatives: {item.debug?.negatives ?? "n/a"}</p>
                                    <p>Classifier category: {item.debug?.classifier_category || "n/a"}</p>
                                    <p>Internal evidence score: {item.debug?.internal_evidence_score ?? "n/a"}</p>
                                    <pre className="mt-2 max-h-40 overflow-auto rounded-md bg-background p-2 text-[11px] leading-5 text-muted-foreground">
                                      {JSON.stringify(item.debug?.raw_state_fields || {}, null, 2)}
                                    </pre>
                                  </div>
                                </div>
                              </div>
                            </details>
                          </div>
                        </details>
                      </article>
                      );
                    })}
                  </div>
                </section>
                );
              })}
            </div>
          )}

          <section className="mt-4 rounded-lg border border-border bg-background">
            <div className="border-b border-border px-4 py-3">
              <div className="flex items-center gap-2">
                <MessageSquareText className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">AI review / Debate process</h3>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Structured review for this opportunity after inspecting the supporting evidence.
              </p>
            </div>

            <div className="space-y-3 px-4 py-4">
              {decision ? (
                <div className="rounded-md border border-emerald-100 bg-emerald-50/70 px-3 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase text-emerald-900">
                      <Scale className="h-3.5 w-3.5" />
                      Final judge
                    </div>
                    <span className="rounded-md bg-white px-2 py-1 text-xs font-semibold uppercase text-emerald-800">
                      {decision.decision} · {decision.score}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-emerald-950">
                    {decision.reason || "Final decision is based on the evidence and agent reviews for this opportunity."}
                  </p>
                  {decision.first_validation_action ? (
                    <p className="mt-2 text-sm leading-6 text-emerald-950">
                      Next: {decision.first_validation_action}
                    </p>
                  ) : null}
                </div>
              ) : null}

              {reviews.length ? (
                <div className="grid gap-2 sm:grid-cols-2">
                  {reviews.map((review) => (
                    <article key={`${review.opportunity_id}-${review.agent}`} className="rounded-md border border-border bg-white px-3 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="rounded-md bg-muted px-2 py-1 text-xs font-semibold text-foreground">
                            {review.agent}
                          </span>
                          <span className="text-xs font-medium text-muted-foreground">
                            {review.recommendation}
                          </span>
                        </div>
                        <span className="text-xs font-semibold text-muted-foreground">{review.score}/10</span>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-foreground">{review.key_argument}</p>
                      {review.main_risk ? (
                        <p className="mt-2 flex gap-2 text-sm leading-6 text-muted-foreground">
                          <ShieldAlert className="mt-1 h-3.5 w-3.5 shrink-0 text-amber-700" />
                          <span>{review.main_risk}</span>
                        </p>
                      ) : null}
                    </article>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No agent reviews recorded for this opportunity.</p>
              )}
            </div>
          </section>
        </div>
      </aside>
    </div>
  );
}
