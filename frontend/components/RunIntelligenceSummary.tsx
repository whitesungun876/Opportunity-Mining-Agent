import { FusionCandidate, RepoCapability, ResearchEvidence, RunState, RunSummary } from "@/lib/api";
import { ReactNode } from "react";

type Props = {
  summary: RunSummary;
  state: RunState | null;
  fusionCandidates: FusionCandidate[];
};

function scopeLabel(state: RunState | null) {
  const scope = typeof state?.query_scope?.scope === "string" ? state.query_scope.scope : "broad";
  if (scope === "repo_specific") {
    return "Repo-specific scope";
  }
  return `${scope.replace("_", " ")} scope`.replace(/^\w/, (letter) => letter.toUpperCase());
}

function countCapabilities(items?: RepoCapability[]) {
  return items?.length || 0;
}

function countResearch(items?: ResearchEvidence[]) {
  return items?.length || 0;
}

function Chip({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "teal" | "blue" | "violet" | "amber" | "emerald" }) {
  const tones = {
    neutral: "border-border bg-white text-muted-foreground",
    teal: "border-teal-100 bg-teal-50 text-teal-800",
    blue: "border-blue-100 bg-blue-50 text-blue-800",
    violet: "border-violet-100 bg-violet-50 text-violet-800",
    amber: "border-amber-100 bg-amber-50 text-amber-800",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-800",
  };
  return (
    <span className={`inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${tones[tone]}`}>
      {children}
    </span>
  );
}

export default function RunIntelligenceSummary({ summary, state, fusionCandidates }: Props) {
  return (
    <section className="mb-4 max-w-5xl rounded-xl border border-border bg-white/85 px-4 py-3 shadow-sm">
      <div className="flex flex-col gap-2">
        <div>
          <p className="section-kicker">Run intelligence</p>
          <p className="mt-1 text-sm text-muted-foreground">Search scope, evidence volume, and advanced discovery signals.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Chip tone="teal">{scopeLabel(state)}</Chip>
          <Chip tone="emerald">{summary.validated_cards_count} validated cards</Chip>
          <Chip tone="blue">{summary.evidence_items_count} evidence links</Chip>
          <Chip tone="amber">{fusionCandidates.length} fusion candidates</Chip>
          <Chip tone="violet">{countCapabilities(state?.repo_capabilities)} capabilities</Chip>
          <Chip>{countResearch(state?.research_evidence)} research</Chip>
        </div>
      </div>
    </section>
  );
}
