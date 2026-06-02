"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Loader2, Square } from "lucide-react";

export const ANALYSIS_STEPS = [
  {
    key: "search",
    title: "Searching GitHub repositories...",
    description: "Finding active open-source projects related to your topic.",
    startMs: 0,
  },
  {
    key: "collect",
    title: "Reading issues and discussions...",
    description: "Collecting real developer feedback from GitHub.",
    startMs: 4_000,
  },
  {
    key: "filter",
    title: "Filtering low-value noise...",
    description: "Dropping one-off bugs, install errors, and vague support requests.",
    startMs: 10_000,
  },
  {
    key: "pain",
    title: "Extracting repeated pains...",
    description: "Looking for production workflow problems that appear across issues.",
    startMs: 16_000,
  },
  {
    key: "cluster",
    title: "Grouping similar signals...",
    description: "Merging related pain points into stronger opportunity themes.",
    startMs: 25_000,
  },
  {
    key: "validate",
    title: "Checking evidence strength...",
    description: "Making sure each opportunity is backed by real GitHub sources.",
    startMs: 35_000,
  },
  {
    key: "review",
    title: "Running structured review...",
    description: "Using PM, Engineer, Founder, and Skeptic reviews to challenge assumptions.",
    startMs: 45_000,
  },
  {
    key: "report",
    title: "Preparing your report...",
    description: "Turning validated opportunities into a readable report.",
    startMs: 60_000,
  },
] as const;

export function getAnalysisStepByElapsed(elapsedMs: number) {
  return [...ANALYSIS_STEPS].reverse().find((step) => elapsedMs >= step.startMs) || ANALYSIS_STEPS[0];
}

type Props = {
  isRunning: boolean;
  startedAt: number | null;
  progress?: number;
  onStop: () => void;
};

export default function AnalysisProgressBubble({ isRunning, startedAt, progress = 0, onStop }: Props) {
  const [now, setNow] = useState(() => Date.now());
  const [isMinimized, setIsMinimized] = useState(false);

  useEffect(() => {
    if (!isRunning) {
      return undefined;
    }
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [isRunning]);

  const elapsedMs = Math.max(0, now - (startedAt || now));
  const step = useMemo(() => getAnalysisStepByElapsed(elapsedMs), [elapsedMs]);
  const simulatedProgress = Math.round((elapsedMs / 75_000) * 92);
  const visibleProgress = Math.max(2, Math.min(98, Math.max(progress, simulatedProgress)));

  if (!isRunning) {
    return null;
  }

  return (
    <aside
      aria-live="polite"
      className="fixed bottom-4 right-4 z-50 w-[calc(100vw-2rem)] max-w-sm rounded-xl border border-primary/15 bg-white shadow-2xl shadow-slate-900/15 sm:bottom-5 sm:right-5"
    >
      <div className="border-l-4 border-primary bg-gradient-to-br from-white via-teal-50/40 to-blue-50/45">
        <div className="flex items-start justify-between gap-3 p-4">
          <div className="flex min-w-0 items-start gap-3">
            <span className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Loader2 className="h-4 w-4 animate-spin" />
            </span>
            <div className="min-w-0">
              <p className="section-kicker">Analyzing GitHub</p>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">{step.title}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setIsMinimized((value) => !value)}
            aria-label={isMinimized ? "Expand analysis progress" : "Minimize analysis progress"}
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border text-muted-foreground transition hover:border-primary/30 hover:text-foreground"
          >
            {isMinimized ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>

        {!isMinimized ? (
          <div className="px-4 pb-4">
            <p className="text-sm font-medium leading-6 text-slate-700">{step.description}</p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-primary/10">
              <div
                className="h-full rounded-full bg-primary transition-all duration-700 ease-out"
                style={{ width: `${visibleProgress}%` }}
              />
            </div>
            <div className="mt-3 flex items-center justify-between gap-3">
              <p className="text-xs text-muted-foreground">This can take a few minutes for live GitHub + LLM runs.</p>
              <button
                type="button"
                onClick={onStop}
                className="inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700"
              >
                <Square className="h-3.5 w-3.5" />
                Stop analysis
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
