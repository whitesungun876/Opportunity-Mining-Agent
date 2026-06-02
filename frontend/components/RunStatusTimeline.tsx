import { AlertTriangle, CheckCircle2, GitBranch, Layers3, ScrollText } from "lucide-react";
import { RunSummary } from "@/lib/api";

type Props = {
  summary: RunSummary;
};

export default function RunStatusTimeline({ summary }: Props) {
  const steps = [
    {
      label: "Evidence",
      value: summary.evidence_items_count,
      icon: GitBranch,
      tone: "text-blue-700",
    },
    {
      label: "Cards",
      value: summary.opportunity_cards_count,
      icon: Layers3,
      tone: "text-primary",
    },
    {
      label: "Validated",
      value: summary.validated_cards_count,
      icon: CheckCircle2,
      tone: "text-emerald-700",
    },
    {
      label: "Rejected",
      value: summary.rejected_cards_count,
      icon: ScrollText,
      tone: "text-amber-700",
    },
    {
      label: "Errors",
      value: summary.errors_count,
      icon: AlertTriangle,
      tone: summary.errors_count ? "text-destructive" : "text-muted-foreground",
    },
  ];

  return (
    <section className="rounded-lg border border-border bg-white/95 p-4 shadow-sm">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-foreground">Run quality snapshot</h2>
          <p className="text-sm text-muted-foreground">
            {summary.status} · {summary.validated_cards_count} validated opportunities from {summary.evidence_items_count} evidence items
          </p>
        </div>
        <span className="w-fit rounded-md border border-border bg-muted px-2.5 py-1 text-xs font-semibold text-muted-foreground">
          {summary.dynamic_search ? "Dynamic search" : "Static search"}
        </span>
      </div>

      <div className="grid gap-2 sm:grid-cols-5">
        {steps.map((step) => {
          const Icon = step.icon;
          return (
            <div key={step.label} className="rounded-md border border-border bg-gradient-to-b from-white to-background p-3">
              <div className={`flex h-8 w-8 items-center justify-center rounded-md border border-border bg-white ${step.tone}`}>
                <Icon className="h-4 w-4" />
              </div>
              <p className="mt-3 text-2xl font-semibold leading-none text-foreground">{step.value}</p>
              <p className="mt-1 text-xs font-medium uppercase text-muted-foreground">{step.label}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
