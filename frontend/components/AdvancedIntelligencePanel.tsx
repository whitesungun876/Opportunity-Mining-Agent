import { Beaker, ChevronDown, GitBranch, Network } from "lucide-react";
import { RepoCapability, ResearchEvidence, RunState } from "@/lib/api";

type Props = {
  state: RunState | null;
};

function pct(value?: number) {
  return `${Math.round((value || 0) * 100)}`;
}

function graphCounts(state: RunState | null) {
  const graph = state?.opportunity_graph || {};
  const nodes = Array.isArray(graph.nodes) ? graph.nodes.length : state?.graph_nodes?.length || 0;
  const edges = Array.isArray(graph.edges) ? graph.edges.length : state?.graph_edges?.length || 0;
  return { nodes, edges };
}

function CapabilityRow({ capability }: { capability: RepoCapability }) {
  return (
    <article className="rounded-md border border-border bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold text-foreground">{capability.name || "Capability"}</h4>
          <p className="mt-1 text-xs text-muted-foreground">Source repo: {capability.source_repo || "Unknown repo"}</p>
        </div>
        <span className="rounded-full border border-border bg-background px-2 py-1 text-xs font-medium text-muted-foreground">
          Maturity {pct(capability.maturity_score)}
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{capability.description}</p>
      <p className="mt-2 text-xs text-muted-foreground">
        Evidence: {(capability.evidence_ids || []).length} linked issue{(capability.evidence_ids || []).length === 1 ? "" : "s"}
      </p>
    </article>
  );
}

function ResearchRow({ research }: { research: ResearchEvidence }) {
  return (
    <article className="rounded-md border border-border bg-white p-3">
      <div className="flex items-start gap-2">
        <Beaker className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        <div>
          {research.url ? (
            <a href={research.url} target="_blank" rel="noreferrer" className="text-sm font-semibold text-foreground underline-offset-2 hover:underline">
              {research.title || "Research support"}
            </a>
          ) : (
            <h4 className="text-sm font-semibold text-foreground">{research.title || "Research support"}</h4>
          )}
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{research.claim_summary}</p>
          <p className="mt-2 text-xs font-medium text-amber-800">
            Research support indicates technical feasibility, not market demand.
          </p>
        </div>
      </div>
    </article>
  );
}

export default function AdvancedIntelligencePanel({ state }: Props) {
  const capabilities = state?.repo_capabilities || [];
  const research = state?.research_evidence || [];
  const graph = graphCounts(state);

  if (!capabilities.length && !research.length && !graph.nodes) {
    return null;
  }

  return (
    <details className="mb-5 max-w-5xl rounded-lg border border-border bg-white shadow-sm">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3">
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4 text-primary" />
          <div>
            <h2 className="text-sm font-semibold text-foreground">Advanced intelligence</h2>
            <p className="text-xs text-muted-foreground">Capabilities, research support, and evidence graph details.</p>
          </div>
        </div>
        <ChevronDown className="h-4 w-4 text-muted-foreground" />
      </summary>

      <div className="space-y-4 border-t border-border bg-background px-4 py-4">
        <section>
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-foreground">Discovered capabilities</h3>
          </div>
          <div className="mt-3 grid gap-2 lg:grid-cols-2">
            {capabilities.slice(0, 6).map((capability) => (
              <CapabilityRow key={capability.capability_id || `${capability.source_repo}-${capability.name}`} capability={capability} />
            ))}
          </div>
        </section>

        <section>
          <div className="flex items-center gap-2">
            <Beaker className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-foreground">Research support</h3>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Research support indicates technical feasibility, not market demand.
          </p>
          <div className="mt-3 grid gap-2">
            {research.slice(0, 4).map((item) => (
              <ResearchRow key={item.paper_id || item.title} research={item} />
            ))}
          </div>
        </section>

        <section className="rounded-md border border-border bg-white p-3">
          <h3 className="text-sm font-semibold text-foreground">Evidence graph details</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {graph.nodes} nodes · {graph.edges} edges
          </p>
        </section>
      </div>
    </details>
  );
}
