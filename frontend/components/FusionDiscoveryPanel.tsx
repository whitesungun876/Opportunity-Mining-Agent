import { Beaker, GitBranch, Lightbulb, Network, ShieldAlert } from "lucide-react";
import { FusionCandidate } from "@/lib/api";

type Props = {
  candidates: FusionCandidate[];
};

function pct(value?: number) {
  return `${Math.round((value || 0) * 100)}`;
}

function text(value: unknown, fallback = "Not enough structured information yet.") {
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  return fallback;
}

function painLabel(candidate: FusionCandidate) {
  const pain = candidate.pain || {};
  return text(pain.complaint || pain.pain_type, "GitHub pain evidence");
}

function capabilityLabel(candidate: FusionCandidate) {
  const capability = candidate.capability || {};
  return text(capability.name, "Repo capability");
}

function capabilityRepo(candidate: FusionCandidate) {
  const capability = candidate.capability || {};
  return text(capability.source_repo || candidate.repo_ids?.[0], "Unknown repo");
}

function firstResearchTitle(candidate: FusionCandidate) {
  const first = candidate.research_evidence?.[0];
  const title = first?.title;
  return typeof title === "string" && title ? title : undefined;
}

function riskText(candidate: FusionCandidate) {
  return candidate.risks?.[0] || "Fusion may be too close to an existing product or may require a narrower wedge.";
}

export default function FusionDiscoveryPanel({ candidates }: Props) {
  if (!candidates.length) {
    return null;
  }

  return (
    <section className="mb-5 max-w-5xl rounded-lg border border-border bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Network className="h-4 w-4 text-primary" />
            <h2 className="text-base font-semibold text-foreground">Fusion discovery</h2>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Cross-source opportunity hypotheses combining GitHub pain, mature repo capability, and research support.
          </p>
        </div>
        <span className="w-fit rounded-full border border-primary/15 bg-primary/5 px-2.5 py-1 text-xs font-medium text-primary">
          {candidates.length} fusion candidates
        </span>
      </div>

      <div className="mt-3 rounded-md border border-border bg-background px-3 py-2 text-xs leading-5 text-muted-foreground">
        <span className="font-semibold text-foreground">How to read this:</span> GitHub evidence = user pain · Repo capability = implementation pattern · Research = technical feasibility, not market proof.
      </div>

      <div className="mt-4 grid gap-3">
        {candidates.slice(0, 4).map((candidate) => (
          <article key={candidate.fusion_id} className="rounded-md border border-border bg-background p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold leading-snug text-foreground">{candidate.title}</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Score {pct(candidate.overall_score)} · Feasibility {pct(candidate.feasibility_score)}
                </p>
              </div>
              <span className="shrink-0 rounded-md border border-border bg-white px-2 py-1 text-xs font-semibold text-muted-foreground">
                Fusion
              </span>
            </div>

            <div className="mt-3">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Fusion thesis</p>
              <p className="mt-1 text-sm leading-6 text-foreground">{candidate.fusion_thesis}</p>
            </div>

            <div className="mt-3 grid gap-2 text-xs lg:grid-cols-3">
              <div className="rounded-md border border-border bg-white p-2">
                <div className="flex items-center gap-1.5 font-semibold text-muted-foreground">
                  <Lightbulb className="h-3.5 w-3.5" />
                  Pain evidence
                </div>
                <p className="mt-1 line-clamp-3 text-foreground">{painLabel(candidate)}</p>
              </div>
              <div className="rounded-md border border-border bg-white p-2">
                <div className="flex items-center gap-1.5 font-semibold text-muted-foreground">
                  <GitBranch className="h-3.5 w-3.5" />
                  Borrowed capability
                </div>
                <p className="mt-1 text-foreground">{capabilityLabel(candidate)}</p>
                <p className="mt-0.5 text-muted-foreground">{capabilityRepo(candidate)}</p>
              </div>
              <div className="rounded-md border border-border bg-white p-2">
                <div className="flex items-center gap-1.5 font-semibold text-muted-foreground">
                  <Beaker className="h-3.5 w-3.5" />
                  Research support
                </div>
                <p className="mt-1 line-clamp-2 text-foreground">{firstResearchTitle(candidate) || "Optional technical support"}</p>
                <p className="mt-0.5 text-muted-foreground">Not market proof</p>
              </div>
            </div>

            <div className="mt-3 grid gap-2 lg:grid-cols-[1.4fr_1fr]">
              <div className="rounded-md border border-border bg-white p-3">
                <p className="text-xs font-semibold uppercase text-muted-foreground">Why this combination matters</p>
                <p className="mt-1 text-sm leading-6 text-foreground">{candidate.why_combination_makes_sense}</p>
              </div>
              <div className="rounded-md border border-amber-100 bg-amber-50/70 p-3">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase text-amber-900">
                  <ShieldAlert className="h-3.5 w-3.5" />
                  Risk
                </div>
                <p className="mt-1 text-sm leading-6 text-amber-950">{riskText(candidate)}</p>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
