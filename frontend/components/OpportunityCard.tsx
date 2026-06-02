import {
  ArrowRight,
  Banknote,
  CheckCircle2,
  FileSearch,
  Lightbulb,
  Search,
  ShieldCheck,
  Users,
  Wrench,
} from "lucide-react";
import { AgentReview, CommercialValidation, EvidenceReason, FinalDecision, OpportunityCardData } from "@/lib/api";

type Props = {
  card: OpportunityCardData;
  decision?: FinalDecision;
  reviews: AgentReview[];
  evidenceReasons: EvidenceReason[];
  commercialValidation?: CommercialValidation;
  onOpenEvidence: (opportunityId: string) => void;
};

function score(card: OpportunityCardData, decision?: FinalDecision) {
  if (decision?.score !== undefined) {
    return decision.score;
  }
  return card.score_json?.overall ?? 0;
}

function productForm(card: OpportunityCardData, decision?: FinalDecision) {
  return card.product_form || card.best_product_form || decision?.best_product_form || "Product";
}

function lowerTitle(card: OpportunityCardData) {
  return (card.title || "").toLowerCase();
}

function migrationCost(card: OpportunityCardData, decision?: FinalDecision) {
  return (card.migration_cost || decision?.migration_cost || "unknown").toLowerCase();
}

function isConsultingHighMigration(card: OpportunityCardData, decision?: FinalDecision) {
  return productForm(card, decision).toLowerCase() === "consulting" && migrationCost(card, decision) === "high";
}

function formatOpportunityTitle(card: OpportunityCardData, decision?: FinalDecision) {
  const title = card.title || "";
  const lower = title.toLowerCase();
  const form = productForm(card, decision);
  if (!title) {
    return "Opportunity needs more structured detail";
  }
  if (lower.includes("observability") && lower.includes("retrieval")) {
    return form.toLowerCase().includes("hosted")
      ? "Hosted Retrieval Trace Debugging Dashboard"
      : "Production Observability Layer for RAG Failures";
  }
  if (lower.includes("latency") && lower.includes("trace")) {
    return "RAG Trace Latency Diagnostics Service";
  }
  if (lower.includes("evaluation gates") || lower.includes("deployment")) {
    return "Production Evaluation Gate for RAG Deployments";
  }
  if (lower.includes("permission") || lower.includes("enterprise")) {
    return "Enterprise Permission Plugin for RAG Evaluation Workflows";
  }
  if (lower.includes("ci workflow") || lower.includes("integrating")) {
    return "CI Integration Plugin for RAG Evaluation Workflows";
  }
  if (lower.startsWith("need ")) {
    return `Opportunity: ${title.replace(/^Need /i, "")}`;
  }
  if (lower.startsWith("missing ") || lower.includes("users struggle") || lower.includes("lack of ")) {
    return `Opportunity: ${title}`;
  }
  return title;
}

function isGenericText(value?: string) {
  const text = (value || "").trim().toLowerCase();
  if (!text) {
    return true;
  }
  return [
    "open-source users need a production-ready layer around the project",
    "the repo has repeated production workflow issues across active users",
    "users have workflow issues",
    "not enough structured information yet",
  ].some((generic) => text.includes(generic));
}

function painSummary(card: OpportunityCardData) {
  if (!isGenericText(card.pain_summary)) {
    return card.pain_summary || "";
  }
  if (!isGenericText(card.problem)) {
    return card.problem || "";
  }
  const lower = lowerTitle(card);
  if (lower.includes("observability") && lower.includes("retrieval")) {
    return "AI engineering teams can see that retrieval quality is failing, but cannot quickly trace which query, document, prompt, or model step caused the failure.";
  }
  if (lower.includes("latency")) {
    return "Teams replaying RAG traces for evaluation hit latency spikes and cannot isolate whether the slowdown comes from retrieval, model calls, reranking, or logging overhead.";
  }
  if (lower.includes("evaluation gates") || lower.includes("deployment")) {
    return "Teams moving RAG systems into production lack a reliable gate that compares evaluation results before deployment and catches regressions early.";
  }
  if (lower.includes("permission") || lower.includes("enterprise")) {
    return "Enterprise teams evaluating RAG tooling need role-based permissions and auditability before they can safely roll it out across teams.";
  }
  if (lower.includes("ci workflow") || lower.includes("integrating")) {
    return "AI teams want RAG evaluations to run inside existing CI workflows, but wiring datasets, metrics, and failure reports into release checks is painful.";
  }
  return "Not enough structured information yet.";
}

function commercialGap(card: OpportunityCardData) {
  if (!isGenericText(card.commercial_gap)) {
    return card.commercial_gap || "";
  }
  if (!isGenericText(card.why_now)) {
    return card.why_now || "";
  }
  const lower = lowerTitle(card);
  if (lower.includes("observability") && lower.includes("retrieval")) {
    return "Open-source RAG stacks expose logs and evaluation primitives, but teams still need a hosted workflow to replay failures, compare regressions, and share debugging evidence.";
  }
  if (lower.includes("latency")) {
    return "Existing tools capture traces, but production teams lack a focused latency breakdown that ties slow runs to retrieval, model, and evaluation steps.";
  }
  if (lower.includes("evaluation gates") || lower.includes("deployment")) {
    return "RAG frameworks provide evaluation scripts, but not a deployment gate that turns regression checks into a shared release workflow.";
  }
  if (lower.includes("permission") || lower.includes("enterprise")) {
    return "Open-source tooling often lacks enterprise-grade RBAC, audit logs, and workspace controls that buyers need before organization-wide adoption.";
  }
  if (lower.includes("ci workflow") || lower.includes("integrating")) {
    return "Evaluation libraries can run locally, but teams need a packaged CI integration that produces clear pass/fail reports and links failures to traces.";
  }
  return "Not enough structured information yet.";
}

function projectCount(items?: EvidenceReason[]) {
  if (!Array.isArray(items)) {
    return 0;
  }
  return new Set(items.map((item) => item.repo_label)).size;
}

function productMvpFeatures(card: OpportunityCardData) {
  if (card.mvp_features?.length) {
    return card.mvp_features;
  }
  const lower = lowerTitle(card);
  if (lower.includes("observability") && lower.includes("retrieval")) {
    return [
      "Trace ingestion from LangChain and LlamaIndex",
      "Failed retrieval replay with query, document, and prompt context",
      "Cost and latency breakdown by pipeline step",
      "Regression dataset comparison for recurring failures",
    ];
  }
  if (lower.includes("latency")) {
    return [
      "Trace-level latency profiler for retrieval and generation steps",
      "Slow-run replay with model, retriever, and reranker timings",
      "Performance regression alerts for evaluation batches",
    ];
  }
  if (lower.includes("evaluation gates") || lower.includes("deployment")) {
    return [
      "CI/CD evaluation gate with configurable pass/fail thresholds",
      "Regression dataset comparison before deployment",
      "Release report showing failed queries and quality deltas",
    ];
  }
  if (lower.includes("permission") || lower.includes("enterprise")) {
    return [
      "RBAC for datasets, traces, and evaluation reports",
      "Audit logs for debugging and model-quality review sessions",
      "SSO-ready team workspace for RAG evaluation workflows",
    ];
  }
  if (lower.includes("ci workflow") || lower.includes("integrating")) {
    return [
      "GitHub Actions integration for RAG evaluation runs",
      "Pull-request quality summary with failed retrieval examples",
      "Dataset and metric configuration stored with the repo",
    ];
  }
  return ["Not enough structured information yet."];
}

function concreteValidationActions(card: OpportunityCardData) {
  if (card.validation_actions?.length) {
    return card.validation_actions;
  }
  const lower = lowerTitle(card);
  if (lower.includes("observability") || lower.includes("retrieval") || lower.includes("trace")) {
    return [
      "Contact 10 GitHub issue authors and ask how they currently debug failed retrieval traces.",
      "Offer a free trace audit using their existing RAG logs.",
      "Build a clickable dashboard mockup and ask if they would connect traces to it.",
    ];
  }
  if (lower.includes("deployment") || lower.includes("evaluation gates")) {
    return [
      "Ask 10 teams what quality checks block their RAG deployments today.",
      "Build a sample GitHub Action that fails a release on retrieval-regression examples.",
      "Post a short demo in relevant GitHub discussions and measure replies.",
    ];
  }
  if (lower.includes("permission") || lower.includes("enterprise")) {
    return [
      "Contact issue authors asking what permission model their company requires before adoption.",
      "Mock an RBAC settings screen and test whether teams would connect evaluation data to it.",
    ];
  }
  if (lower.includes("ci workflow") || lower.includes("integrating")) {
    return [
      "Contact teams asking how they run RAG quality checks in CI today.",
      "Ship a demo GitHub Action and measure whether maintainers try it on example datasets.",
    ];
  }
  return ["Not enough structured information yet."];
}

function targetUser(card: OpportunityCardData) {
  const value = (card.target_user || "").trim();
  const lowerValue = value.toLowerCase();
  const lower = lowerTitle(card);
  const isGeneric =
    !value ||
    lowerValue === "engineering teams adopting github oss in production" ||
    lowerValue.includes("open-source users") ||
    lowerValue.includes("github oss in production");

  if (!isGeneric) {
    return value;
  }
  if (lower.includes("observability") && lower.includes("retrieval")) {
    return "AI engineering teams debugging RAG retrieval failures in production";
  }
  if (lower.includes("latency")) {
    return "RAG platform teams investigating latency spikes during evaluation runs";
  }
  if (lower.includes("evaluation gates") || lower.includes("deployment")) {
    return "Teams shipping RAG updates that need regression checks before deployment";
  }
  if (lower.includes("permission") || lower.includes("enterprise")) {
    return "Enterprise AI platform teams rolling out RAG evaluation across shared workspaces";
  }
  if (lower.includes("ci workflow") || lower.includes("integrating")) {
    return "Engineering teams adding RAG quality checks to CI/CD release workflows";
  }
  return "Engineering teams trying to productionize an open-source AI workflow";
}

function opportunityThesis(card: OpportunityCardData, decision?: FinalDecision) {
  const lower = lowerTitle(card);
  if (!isGenericText(card.summary)) {
    return card.summary || "";
  }
  if (lower.includes("observability") && lower.includes("retrieval")) {
    return "A hosted trace debugging workflow can help RAG teams replay retrieval failures and identify regression sources before they ship.";
  }
  if (lower.includes("latency")) {
    return "A focused diagnostics layer can help RAG teams isolate latency spikes during evaluation and trace replay.";
  }
  if (lower.includes("evaluation gates") || lower.includes("deployment")) {
    return "A lightweight CI/CD gate can help RAG teams catch quality regressions before deployment.";
  }
  if (lower.includes("permission") || lower.includes("enterprise")) {
    return "An enterprise controls layer can help platform teams adopt RAG evaluation workflows across shared workspaces.";
  }
  if (lower.includes("ci workflow") || lower.includes("integrating")) {
    return "A packaged CI integration can turn RAG evaluation failures into clear pull-request release checks.";
  }
  const pain = painSummary(card);
  const gap = commercialGap(card);
  if (!isGenericText(pain) && !isGenericText(gap)) {
    return `${pain.replace(/\.$/, "")}; ${gap.charAt(0).toLowerCase()}${gap.slice(1)}`;
  }
  return `${productForm(card, decision)} opportunity for ${targetUser(card)} based on repeated GitHub production workflow pain.`;
}

function evidenceStrength(evidenceCount: number, projects: number) {
  if (evidenceCount >= 5 && projects >= 3) {
    return "Strong";
  }
  if (evidenceCount >= 3) {
    return "Medium";
  }
  return "Weak";
}

function strongestWtp(commercial?: CommercialValidation) {
  const order = { strong: 3, medium: 2, weak: 1 };
  return [...(commercial?.wtpSignals || [])].sort(
    (left, right) => order[right.strength] - order[left.strength],
  )[0];
}

function firstValidationAction(commercial?: CommercialValidation, decision?: FinalDecision, card?: OpportunityCardData) {
  return (
    commercial?.validationPlan?.seven_day_plan?.[0] ||
    decision?.first_validation_action ||
    card?.validation_actions?.[0] ||
    "Contact linked GitHub issue authors for workflow interviews."
  );
}

function SectionHeading({
  children,
  icon: Icon,
  tone = "teal",
}: {
  children: string;
  icon: typeof Search;
  tone?: "teal" | "blue" | "amber" | "emerald" | "violet";
}) {
  const toneClass = {
    teal: "text-primary",
    blue: "text-blue-700",
    amber: "text-amber-700",
    emerald: "text-emerald-700",
    violet: "text-violet-700",
  }[tone];
  return (
    <p className="label-copy flex items-center gap-1.5 text-foreground/75">
      <Icon className={`h-3.5 w-3.5 ${toneClass}`} />
      {children}
    </p>
  );
}

function MemoBlock({
  title,
  icon,
  tone = "teal",
  children,
}: {
  title: string;
  icon: typeof Search;
  tone?: "teal" | "blue" | "amber" | "emerald" | "violet";
  children: React.ReactNode;
}) {
  const toneClass = {
    teal: "border-teal-100 bg-teal-50/45",
    blue: "border-blue-100 bg-blue-50/45",
    amber: "border-amber-100 bg-amber-50/45",
    emerald: "border-emerald-100 bg-emerald-50/45",
    violet: "border-violet-100 bg-violet-50/45",
  }[tone];
  return (
    <section className={`min-w-0 rounded-lg border px-3 py-2.5 ${toneClass}`}>
      <SectionHeading icon={icon} tone={tone}>{title}</SectionHeading>
      <div className="mt-2 text-[15px] leading-6 text-foreground">{children}</div>
    </section>
  );
}

export default function OpportunityCard({ card, decision, evidenceReasons = [], commercialValidation, onOpenEvidence }: Props) {
  const evidenceCount = card.evidence_ids?.length ?? 0;
  const allMvpFeatures = productMvpFeatures(card);
  const allValidationActions = concreteValidationActions(card);
  const mvpFeatures = allMvpFeatures.slice(0, 3);
  const validationActions = allValidationActions.slice(0, 2);
  const mvpMoreCount = Math.max(0, allMvpFeatures.length - mvpFeatures.length);
  const validationMoreCount = Math.max(0, allValidationActions.length - validationActions.length);
  const rawDecisionLabel = decision?.decision || card.final_decision || "validate";
  const cautionOpportunity = isConsultingHighMigration(card, decision);
  const decisionLabel = cautionOpportunity && rawDecisionLabel === "validate" ? "validate carefully" : rawDecisionLabel;
  const projects = projectCount(evidenceReasons);
  const evidenceLabel = evidenceStrength(evidenceCount, projects);
  const wtpSignal = strongestWtp(commercialValidation);
  const buyer = commercialValidation?.buyer;
  const validationAction = firstValidationAction(commercialValidation, decision, card);

  return (
    <article className="overflow-hidden rounded-xl border border-border bg-white shadow-md shadow-slate-900/5">
      <div className="border-l-[3px] border-l-primary px-4 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex flex-wrap gap-1.5">
              <span
                className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase ${
                  cautionOpportunity
                    ? "border-amber-200 bg-amber-50 text-amber-900"
                    : "border-emerald-100 bg-emerald-50 text-emerald-800"
                }`}
              >
                {decisionLabel}
              </span>
              <span className="rounded-full border border-blue-100 bg-blue-50 px-2.5 py-1 text-[11px] font-semibold text-blue-800">
                {productForm(card, decision)}
              </span>
              <span className="rounded-full border border-violet-100 bg-violet-50 px-2.5 py-1 text-[11px] font-semibold text-violet-800">
                {migrationCost(card, decision)} migration
              </span>
          </div>
          <div
            className="flex h-12 w-14 shrink-0 flex-col items-center justify-center rounded-lg border border-primary/15 bg-primary/5"
            title="Score combines pain intensity, evidence strength, feasibility, and distribution."
          >
            <span className="text-lg font-bold leading-none text-primary">{score(card, decision)}</span>
            <span className="mt-0.5 text-[9px] font-bold uppercase text-primary/70">score</span>
          </div>
        </div>

        <h3 className="mt-3 text-xl font-bold leading-tight text-foreground">
          {formatOpportunityTitle(card, decision)}
        </h3>
        <p className="mt-2 line-clamp-2 text-[15px] font-medium leading-6 text-slate-700">
          {opportunityThesis(card, decision)}
        </p>
        <p className="mt-1.5 line-clamp-1 text-sm leading-6 text-muted-foreground">{targetUser(card)}</p>

        {cautionOpportunity ? (
          <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-sm leading-5 text-amber-950">
            Service-led opportunity: migration cost is high.
          </p>
        ) : null}

        <div className="mt-3 grid gap-2 border-t border-border pt-3 sm:grid-cols-2">
          <MemoBlock title="Pain" icon={Search} tone="amber">
            <p className="line-clamp-2">{painSummary(card)}</p>
          </MemoBlock>
          <MemoBlock title="Gap" icon={Lightbulb} tone="blue">
            <p className="line-clamp-2">{commercialGap(card)}</p>
          </MemoBlock>
        </div>

        {mvpFeatures.length || validationActions.length ? (
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {mvpFeatures.length ? (
              <MemoBlock title="Build" icon={Wrench} tone="teal">
                <ul className="space-y-1">
                  {mvpFeatures.map((feature) => (
                    <li key={feature} className="flex gap-1.5 text-[15px] leading-5 text-foreground">
                      <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                      <span className="line-clamp-1">{feature}</span>
                    </li>
                  ))}
                  {mvpMoreCount > 0 ? (
                    <li className="text-sm font-medium text-muted-foreground">+{mvpMoreCount} more</li>
                  ) : null}
                </ul>
              </MemoBlock>
            ) : null}
            {validationActions.length ? (
              <MemoBlock title="Validate" icon={ShieldCheck} tone="emerald">
                <ul className="space-y-1">
                  {validationActions.map((action) => (
                    <li key={action} className="flex gap-1.5 text-[15px] leading-5 text-foreground">
                      <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-700" />
                      <span className="line-clamp-1">{action}</span>
                    </li>
                  ))}
                  {validationMoreCount > 0 ? (
                    <li className="text-sm font-medium text-muted-foreground">+{validationMoreCount} more</li>
                  ) : null}
                </ul>
              </MemoBlock>
            ) : null}
          </div>
        ) : null}

        <details className="mt-2 rounded-lg border border-violet-100 bg-violet-50/40 px-3 py-2.5">
          <summary className="cursor-pointer list-none">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <SectionHeading icon={Banknote} tone="violet">Commercial validation</SectionHeading>
                <div className="mt-2 grid gap-1.5 text-sm leading-5 text-foreground">
                  <p className="flex gap-1.5">
                    <Users className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                    <span>
                      Buyer: {buyer?.economic_buyer || "Hypothesis: buyer needs validation"}
                    </span>
                  </p>
                  <p>
                    WTP signal: <span className="font-semibold">{wtpSignal?.strength || "weak"}</span>
                    {wtpSignal?.signal_type ? ` · ${wtpSignal.signal_type.replaceAll("_", " ")}` : ""}
                  </p>
                  <p className="line-clamp-1 text-muted-foreground">First action: {validationAction}</p>
                </div>
              </div>
              <span className="mt-1 text-xs font-semibold text-primary">Details</span>
            </div>
          </summary>
          <div className="mt-3 grid gap-3 border-t border-border pt-3 text-sm leading-6 text-foreground sm:grid-cols-3">
            <div>
              <p className="text-xs font-semibold uppercase text-muted-foreground">Alternatives</p>
              <ul className="mt-1 space-y-1">
                {(commercialValidation?.alternatives || []).slice(0, 3).map((item) => (
                  <li key={`${item.name}-${item.source || ""}`}>- {item.name}: {item.limitation}</li>
                ))}
                {commercialValidation?.alternatives?.length ? null : <li>- Hypothesis: current alternatives need discovery.</li>}
              </ul>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-muted-foreground">Outreach targets</p>
              <ul className="mt-1 space-y-1">
                {(commercialValidation?.outreachTargets || []).slice(0, 3).map((item) => (
                  <li key={item.source_url}>
                    - {item.github_user || "GitHub participant"} via {item.source_repo}
                  </li>
                ))}
                {commercialValidation?.outreachTargets?.length ? null : <li>- No source-linked outreach target yet.</li>}
              </ul>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-muted-foreground">7-day plan</p>
              <ul className="mt-1 space-y-1">
                {(commercialValidation?.validationPlan?.seven_day_plan || []).slice(0, 3).map((step) => (
                  <li key={step}>- {step}</li>
                ))}
                {commercialValidation?.validationPlan?.seven_day_plan?.length ? null : <li>- Build validation plan after card validation.</li>}
              </ul>
            </div>
          </div>
        </details>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border bg-gradient-to-r from-slate-50 via-teal-50/50 to-blue-50/50 px-4 py-3">
        <div className="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
          <FileSearch className="h-3.5 w-3.5" />
          <span>
            Evidence: {projects} projects · {evidenceCount} GitHub links · {evidenceLabel}
          </span>
        </div>
        <button
          type="button"
          onClick={() => onOpenEvidence(card.opportunity_id)}
          className="inline-flex min-h-9 items-center justify-center gap-2 rounded-md bg-primary px-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
        >
          View evidence
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </article>
  );
}
