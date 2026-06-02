"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, GitBranch, Loader2, Search, ShieldCheck, Sparkles } from "lucide-react";
import AnalysisProgressBubble from "@/components/AnalysisProgressBubble";
import { RunPreflight, RunStatus, createRun, getRunStatus, preflightRun } from "@/lib/api";

type Scope = "broad" | "focused" | "repo_specific" | "ambiguous";

const EXAMPLE_GROUPS = [
  {
    title: "Explore broadly",
    description: "Explore multiple opportunity directions.",
    icon: Sparkles,
    tone: "border-sky-100 bg-sky-50/60 text-sky-700",
    chipTone: "hover:border-sky-300 hover:bg-sky-50 hover:text-sky-800",
    examples: ["Developer productivity tools", "Self-hosted SaaS tools", "Security and compliance tools"],
  },
  {
    title: "Validate a specific pain",
    description: "Focus on one production workflow pain.",
    icon: ShieldCheck,
    tone: "border-emerald-100 bg-emerald-50/60 text-emerald-700",
    chipTone: "hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-800",
    examples: [
      "Self-hosted deployment is too complex",
      "Managing permissions in open-source tools",
      "Debugging flaky CI failures",
    ],
  },
  {
    title: "Analyze one repo",
    description: "Inspect issues from one GitHub repository.",
    icon: GitBranch,
    tone: "border-violet-100 bg-violet-50/60 text-violet-700",
    chipTone: "hover:border-violet-300 hover:bg-violet-50 hover:text-violet-800",
    examples: ["supabase/supabase", "n8n-io/n8n", "grafana/grafana"],
  },
];

const PUBLIC_BETA_ENABLED = process.env.NEXT_PUBLIC_PUBLIC_BETA_ENABLED === "true";

function detectScope(query: string): Scope {
  const trimmed = query.trim();
  const lower = trimmed.toLowerCase();
  const words = lower.split(/\s+/).filter(Boolean);
  const repoPattern = /^[a-z0-9_.-]+\/[a-z0-9_.-]+$/i;
  const vagueTerms = new Set(["agent", "agents", "tool", "tools", "framework", "frameworks", "ai", "mcp", "rag"]);
  const focusedSignals = [
    " for ",
    "deployment",
    "deploy",
    "production",
    "auth",
    "authentication",
    "debug",
    "debugging",
    "evaluation",
    "permission",
    "permissions",
    "regression",
    "testing",
    "observability",
    "security",
    "before deployment",
  ];

  if (!trimmed) {
    return "broad";
  }
  if (repoPattern.test(trimmed)) {
    return "repo_specific";
  }
  if (words.length <= 1 || vagueTerms.has(lower)) {
    return "ambiguous";
  }
  if (focusedSignals.some((signal) => lower.includes(signal))) {
    return "focused";
  }
  return "broad";
}

function scopePreview(scope: Scope) {
  if (scope === "focused") {
    return "Focused validation mode · This will prioritize precise GitHub evidence for a specific production workflow.";
  }
  if (scope === "repo_specific") {
    return "Repo-specific analysis · This will analyze one GitHub repository.";
  }
  if (scope === "ambiguous") {
    return "Too broad to analyze well · Try a more specific query.";
  }
  return "Broad exploration mode · This will explore multiple opportunity directions.";
}

function refinementSuggestions(query: string) {
  const lower = query.trim().toLowerCase();
  if (lower.includes("mcp")) {
    return [
      "MCP tools enterprise auth permissions audit logs",
      "MCP server self-hosted deployment blockers",
      "modelcontextprotocol/servers",
    ];
  }
  if (lower.includes("rag")) {
    return [
      "RAG regression testing before deployment",
      "RAG production debugging observability workflow",
      "langfuse/langfuse",
    ];
  }
  if (lower.includes("tool")) {
    return [
      "developer tools enterprise permissions audit logs",
      "developer tools self-hosted deployment blockers",
      "n8n-io/n8n",
    ];
  }
  return [
    "AI agent framework observability for production debugging",
    "AI agent framework enterprise auth permissions",
    "AI agent framework self-hosted deployment blockers",
    "langfuse/langfuse",
  ];
}

function fitBadge(preflight: RunPreflight) {
  if (preflight.opportunity_fit === "high") {
    return "High signal";
  }
  if (preflight.opportunity_fit === "medium") {
    return "Medium signal";
  }
  if (preflight.opportunity_fit === "needs_refinement") {
    return "Needs refinement";
  }
  return "Not enough validated evidence yet";
}

function recoveryLabel(action: string) {
  return action
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function isAbortError(error: unknown) {
  return (
    (error instanceof DOMException && error.name === "AbortError") ||
    (error instanceof Error && error.name === "AbortError")
  );
}

export default function TopicInput({ initialTopic = "" }: { initialTopic?: string }) {
  const router = useRouter();
  const abortControllerRef = useRef<AbortController | null>(null);
  const [topic, setTopic] = useState(initialTopic);
  const [inviteCode, setInviteCode] = useState("");
  const [isChecking, setIsChecking] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [analysisStartedAt, setAnalysisStartedAt] = useState<number | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [preflight, setPreflight] = useState<RunPreflight | null>(null);
  const scope = detectScope(topic);
  const showPreview = topic.trim().length > 0;
  const suggestions = scope === "ambiguous" ? refinementSuggestions(topic) : [];

  useEffect(() => {
    if (!activeRunId) {
      setProgress(0);
      return;
    }

    let cancelled = false;
    let pollTimer: number | undefined;
    let openTimer: number | undefined;

    async function poll() {
      if (!activeRunId) {
        return;
      }
      try {
        const signal = abortControllerRef.current?.signal;
        const status = await getRunStatus(activeRunId, { signal });
        if (cancelled) {
          return;
        }
        const nextProgress = Math.max(1, Math.min(100, Math.round(status.progress || 1)));
        setRunStatus(status);
        setProgress(nextProgress);

        if (status.status === "completed" || status.status === "completed_with_errors") {
          setProgress(100);
          setIsRunning(false);
          setAnalysisStartedAt(null);
          abortControllerRef.current = null;
          setRunStatus({ ...status, progress: 100, message: "Run complete. Opening report..." });
          openTimer = window.setTimeout(() => {
            router.push(`/runs/${activeRunId}`);
          }, 700);
          return;
        }

        if (status.status === "failed") {
          setError(status.error || "Run failed.");
          setIsRunning(false);
          setAnalysisStartedAt(null);
          abortControllerRef.current = null;
          setActiveRunId(null);
          return;
        }

        pollTimer = window.setTimeout(poll, 1500);
      } catch (err) {
        if (isAbortError(err) || abortControllerRef.current?.signal.aborted) {
          return;
        }
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to check run progress.");
          setIsRunning(false);
          setAnalysisStartedAt(null);
          abortControllerRef.current = null;
          setActiveRunId(null);
        }
      }
    }

    void poll();

    return () => {
      cancelled = true;
      if (pollTimer) {
        window.clearTimeout(pollTimer);
      }
      if (openTimer) {
        window.clearTimeout(openTimer);
      }
    };
  }, [activeRunId, router]);

  function beginAnalysis() {
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setIsRunning(true);
    setAnalysisStartedAt(Date.now());
    setProgress(2);
    setRunStatus(null);
    setActiveRunId(null);
    setNotice(null);
    setError(null);
    return controller;
  }

  function stopAnalysis() {
    // P0 cancellation only aborts the client request. Server-side cancellation
    // can be added later with /runs/{run_id}/cancel.
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsRunning(false);
    setIsChecking(false);
    setActiveRunId(null);
    setRunStatus(null);
    setProgress(0);
    setAnalysisStartedAt(null);
    setNotice("Analysis stopped. You can refine your topic and try again.");
  }

  async function startRun(trimmed: string, preflightId?: string | null, controller?: AbortController) {
    const currentController = controller || beginAnalysis();
    setIsRunning(true);
    setError(null);
    setNotice(null);
    setProgress((value) => Math.max(2, value));
    setRunStatus(null);
    setActiveRunId(null);
    setPreflight(null);
    try {
      const run = await createRun(trimmed, true, {
        preflightId,
        runMode: "standard",
        inviteCode: PUBLIC_BETA_ENABLED ? inviteCode.trim() : undefined,
        signal: currentController.signal,
      });
      setRunStatus({
        run_id: run.run_id,
        topic: trimmed,
        dynamic_search: true,
        status: run.status,
        progress: 2,
        current_node: "queued",
        message: "Queued",
      });
      setActiveRunId(run.run_id);
    } catch (err) {
      if (isAbortError(err) || currentController.signal.aborted) {
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to create run.");
      setIsRunning(false);
      setAnalysisStartedAt(null);
      abortControllerRef.current = null;
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = topic.trim();
    if (!trimmed) {
      setError("Enter a topic, production pain, or GitHub repo.");
      return;
    }
    const controller = beginAnalysis();
    setPreflight(null);
    setIsChecking(true);
    try {
      const result = await preflightRun(trimmed, true, {
        inviteCode: PUBLIC_BETA_ENABLED ? inviteCode.trim() : undefined,
        signal: controller.signal,
      });
      setPreflight(result);
      if (result.should_run) {
        setIsChecking(false);
        await startRun(trimmed, result.preflight_id, controller);
        return;
      }
      setIsRunning(false);
      setAnalysisStartedAt(null);
      abortControllerRef.current = null;
      setIsChecking(false);
    } catch (err) {
      if (isAbortError(err) || controller.signal.aborted) {
        return;
      }
      setIsChecking(false);
      setIsRunning(false);
      setAnalysisStartedAt(null);
      abortControllerRef.current = null;
      setError(err instanceof Error ? err.message : "Failed to check opportunity signal.");
    }
  }

  return (
    <div className="space-y-5">
      <form onSubmit={onSubmit} className="surface-card rounded-xl p-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="min-w-0 flex-1">
            <label htmlFor="topic" className="sr-only">
              GitHub opportunity topic
            </label>
            <input
              id="topic"
              value={topic}
              onChange={(event) => {
                setTopic(event.target.value);
                setPreflight(null);
                setNotice(null);
              }}
              placeholder="Try a topic, production pain, or repo..."
              className="h-12 w-full rounded-lg border border-transparent bg-muted px-4 text-base font-medium text-foreground transition placeholder:font-normal placeholder:text-muted-foreground focus:border-primary focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/15"
              disabled={isRunning || isChecking}
            />
          </div>

          <button
            type="submit"
            disabled={isRunning || isChecking}
            className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-lg bg-primary px-5 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRunning || isChecking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            {isChecking ? "Checking signal" : isRunning ? "Analyzing" : "Analyze GitHub"}
          </button>
        </div>

        <div className="mt-3 flex flex-col gap-2 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>Mode is auto-detected from your input.</span>
          {showPreview ? <span className="font-medium text-foreground">{scopePreview(scope)}</span> : null}
        </div>

        {PUBLIC_BETA_ENABLED ? (
          <div className="mt-3 rounded-lg border border-border bg-white/80 p-3">
            <label htmlFor="invite-code" className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Public beta invite code
            </label>
            <input
              id="invite-code"
              value={inviteCode}
              onChange={(event) => setInviteCode(event.target.value)}
              placeholder="Enter your invite code"
              className="mt-2 h-10 w-full rounded-md border border-border bg-background px-3 text-sm font-medium text-foreground transition placeholder:font-normal placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/15"
              disabled={isRunning || isChecking}
            />
            <p className="mt-2 text-xs leading-5 text-muted-foreground">
              Public beta is rate-limited to control GitHub API and LLM cost.
            </p>
          </div>
        ) : null}

        {suggestions.length ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">Try:</span>
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => {
                  setTopic(suggestion);
                  setError(null);
                  setNotice(null);
                  setPreflight(null);
                }}
                disabled={isRunning || isChecking}
                className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs font-medium text-amber-950 transition hover:border-amber-300 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {suggestion}
              </button>
            ))}
          </div>
        ) : null}

        {preflight && !isRunning ? (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-950">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold">{fitBadge(preflight)}</p>
                    <span className="rounded-full border border-amber-300 bg-white/60 px-2 py-0.5 text-[11px] font-semibold uppercase">
                      {preflight.query_scope.replace("_", " ")}
                    </span>
                    <span className="rounded-full border border-amber-300 bg-white/60 px-2 py-0.5 text-[11px] font-semibold">
                      {preflight.evidence_count} evidence · {preflight.strong_evidence_count} strong
                    </span>
                  </div>
                  <p className="mt-1 text-sm leading-6">{preflight.reason}</p>
                  {preflight.signal_diagnostics ? (
                    <div className="mt-3 grid gap-2 text-xs sm:grid-cols-4">
                      <span className="rounded-md border border-amber-200 bg-white/70 px-2 py-1.5">
                        {preflight.signal_diagnostics.raw_issues_count} GitHub issues found
                      </span>
                      <span className="rounded-md border border-amber-200 bg-white/70 px-2 py-1.5">
                        {preflight.signal_diagnostics.high_value_issues_count} high-value signals
                      </span>
                      <span className="rounded-md border border-amber-200 bg-white/70 px-2 py-1.5">
                        {preflight.signal_diagnostics.opportunity_cards_count} opportunity hypotheses
                      </span>
                      <span className="rounded-md border border-amber-200 bg-white/70 px-2 py-1.5">
                        Stage: {preflight.signal_diagnostics.low_signal_stage.replaceAll("_", " ")}
                      </span>
                    </div>
                  ) : null}
                  {preflight.signal_diagnostics?.suggested_recovery_actions?.length ? (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {preflight.signal_diagnostics.suggested_recovery_actions.slice(0, 4).map((action) => (
                        <span
                          key={action}
                          className="rounded-full border border-amber-300 bg-white/70 px-2 py-1 text-[11px] font-medium"
                        >
                          {recoveryLabel(action)}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  <p className="mt-1 text-xs text-amber-900/80">
                    Full analysis estimated cost: {preflight.estimated_cost}. Runtime: {preflight.estimated_runtime}.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => void startRun(topic.trim(), preflight.preflight_id)}
                className="inline-flex shrink-0 items-center justify-center rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs font-semibold text-amber-950 transition hover:bg-amber-100"
              >
                {preflight.opportunity_fit === "medium" ? "Run full analysis" : "Run anyway"}
              </button>
            </div>
            {preflight.suggested_queries.length ? (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-amber-950">Try instead:</span>
                {preflight.suggested_queries.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => {
                      setTopic(suggestion);
                      setPreflight(null);
                      setError(null);
                      setNotice(null);
                    }}
                    className="rounded-full border border-amber-300 bg-white px-2.5 py-1.5 text-xs font-medium text-amber-950 transition hover:bg-amber-100"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {notice ? <p className="mt-3 text-sm text-primary">{notice}</p> : null}
        {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}
      </form>

      <AnalysisProgressBubble
        isRunning={isRunning}
        startedAt={analysisStartedAt}
        progress={progress}
        onStop={stopAnalysis}
      />

      <section>
        <div>
          <p className="section-kicker">Query shape</p>
          <h2 className="mt-1 text-xl font-semibold text-foreground">Start with a topic, pain, or repo</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Start broad for exploration, or get precise when you already know the workflow pain.
          </p>
        </div>
        <div className="mt-3 grid gap-3">
          {EXAMPLE_GROUPS.map((group) => {
            const Icon = group.icon;
            return (
              <div key={group.title} className="rounded-lg border border-border bg-white/90 p-3 shadow-sm transition hover:border-primary/20 hover:shadow-md">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-start gap-2">
                    <span className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border ${group.tone}`}>
                      <Icon className="h-4 w-4" />
                    </span>
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">{group.title}</h3>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">{group.description}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 sm:justify-end">
                    {group.examples.map((example) => (
                      <button
                        key={example}
                        type="button"
                        onClick={() => {
                          setTopic(example);
                          setError(null);
                          setNotice(null);
                          setPreflight(null);
                        }}
                        disabled={isRunning || isChecking}
                        className={`rounded-full border border-border bg-white px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition disabled:cursor-not-allowed disabled:opacity-60 ${group.chipTone}`}
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
