"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, Clock3, ExternalLink, RefreshCw } from "lucide-react";
import { RunListItem, RunSummary, getRunSummary, listRuns } from "@/lib/api";

type HistoryRun = RunListItem & {
  evidence_items_count?: number;
  dynamic_search?: boolean;
};

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default function RunHistoryList() {
  const [runs, setRuns] = useState<HistoryRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadRuns() {
    setIsLoading(true);
    setError(null);
    try {
      const payload = await listRuns();
      const baseRuns = payload.runs || [];
      const summaries = await Promise.allSettled(baseRuns.slice(0, 8).map((run) => getRunSummary(run.run_id)));
      const summaryByRun = new Map<string, RunSummary>();
      summaries.forEach((result) => {
        if (result.status === "fulfilled") {
          summaryByRun.set(result.value.run_id, result.value);
        }
      });
      setRuns(
        baseRuns.map((run) => {
          const summary = summaryByRun.get(run.run_id);
          return {
            ...run,
            evidence_items_count: summary?.evidence_items_count,
            dynamic_search: summary?.dynamic_search ?? run.dynamic_search,
          };
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load runs.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadRuns();
  }, []);

  return (
    <section className="rounded-xl border border-border bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <h2 className="text-base font-semibold text-foreground">Recent runs</h2>
          <p className="text-sm text-muted-foreground">Saved locally for quick comparison.</p>
        </div>
        <button
          type="button"
          onClick={() => void loadRuns()}
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border text-muted-foreground transition hover:bg-muted hover:text-foreground"
          aria-label="Refresh runs"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {isLoading ? (
        <div className="flex min-h-32 items-center gap-2 px-4 text-sm text-muted-foreground">
          <Clock3 className="h-4 w-4" />
          Loading runs
        </div>
      ) : error ? (
        <div className="flex min-h-32 items-center gap-2 px-4 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      ) : runs.length === 0 ? (
        <div className="min-h-32 px-4 py-6 text-sm text-muted-foreground">
          No runs yet. Create one from the topic box above.
        </div>
      ) : (
        <div className="divide-y divide-border">
          {runs.map((run) => (
            <Link
              key={run.run_id}
              href={`/runs/${run.run_id}`}
              className="flex items-center justify-between gap-4 px-4 py-3 transition hover:bg-muted/70"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{run.topic}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatDate(run.created_at)} · {run.status}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3 text-xs text-muted-foreground">
                <span>{run.validated_cards_count} validated</span>
                {run.evidence_items_count !== undefined ? <span>{run.evidence_items_count} evidence</span> : null}
                <span>{run.dynamic_search ? "Dynamic" : "Benchmark"}</span>
                <span>{run.errors_count} errors</span>
                <ExternalLink className="h-4 w-4" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
