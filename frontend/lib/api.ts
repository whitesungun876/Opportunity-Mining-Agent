export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export type RunListItem = {
  run_id: string;
  topic: string;
  canonical_topic?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  dynamic_search: boolean;
  validated_cards_count: number;
  errors_count: number;
};

export type RunSummary = {
  run_id: string;
  topic: string;
  canonical_topic?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  dynamic_search: boolean;
  evidence_items_count: number;
  opportunity_cards_count: number;
  validated_cards_count: number;
  rejected_cards_count: number;
  errors_count: number;
  search_plan?: Record<string, unknown>;
};

export type RunStatus = {
  run_id: string;
  topic?: string;
  dynamic_search?: boolean;
  run_mode?: "quick" | "standard" | "deep";
  status: string;
  progress: number;
  current_node?: string | null;
  message?: string;
  created_at?: string;
  updated_at?: string;
  error?: string | null;
  errors?: string[];
};

export type RunPreflight = {
  preflight_id?: string | null;
  topic: string;
  normalized_topic: string;
  query_scope: ScopeName;
  opportunity_fit: "high" | "medium" | "low" | "needs_refinement";
  should_run: boolean;
  reason: string;
  estimated_cost: string;
  estimated_runtime: string;
  evidence_count: number;
  strong_evidence_count: number;
  repo_count: number;
  suggested_queries: string[];
  search_plan?: Record<string, unknown>;
  signal_diagnostics?: SignalDiagnostics;
};

export type SignalDiagnostics = {
  raw_issues_count: number;
  evidence_items_count: number;
  ranked_evidence_count: number;
  selected_repos_count: number;
  repo_coverage_count: number;
  classified_issues_count: number;
  high_value_issues_count: number;
  low_value_issues_count: number;
  pain_points_count: number;
  pain_clusters_count: number;
  filtered_pain_clusters_count: number;
  commercial_gaps_count: number;
  opportunity_cards_count: number;
  validated_cards_count: number;
  rejected_cards_count: number;
  low_signal_type:
    | "evidence_sparse"
    | "evidence_scattered"
    | "classifier_too_strict"
    | "validator_too_strict"
    | "unknown";
  low_signal_stage:
    | "repo_search"
    | "issue_collect"
    | "evidence_rank"
    | "issue_classify"
    | "pain_extract"
    | "cluster"
    | "opportunity_generate"
    | "evidence_validate"
    | "unknown";
  low_signal_reason: string;
  suggested_recovery_actions: string[];
};

export type ScopeName = "broad" | "focused" | "repo_specific" | "ambiguous";

export type OpportunityCardData = {
  run_id?: string;
  opportunity_id: string;
  title: string;
  summary?: string;
  target_user?: string;
  pain_summary?: string;
  commercial_gap?: string;
  problem?: string;
  why_now?: string;
  migration_cost?: string;
  product_form?: string;
  best_product_form?: string;
  mvp_features?: string[];
  pricing_hypothesis?: string;
  first_users?: string[];
  validation_actions?: string[];
  risks?: string[];
  score_json?: Record<string, number>;
  evidence_ids?: string[];
  evidence_urls?: string[];
  weak_card?: boolean;
  final_decision?: string;
  validation?: {
    validation_mode?: string;
    validation_status?: string;
    evidence_count?: number;
    evidence_urls_count?: number;
  };
};

export type BuyerHypothesis = {
  opportunity_id: string;
  end_user: string;
  economic_buyer: string;
  buyer_persona: string;
  budget_source: string;
  buying_trigger: string;
  confidence: number;
  evidence_ids: string[];
};

export type WillingnessToPaySignal = {
  opportunity_id: string;
  signal_type: string;
  signal_summary: string;
  strength: "weak" | "medium" | "strong";
  reason: string;
  evidence_ids: string[];
};

export type CompetitorAlternative = {
  opportunity_id: string;
  name: string;
  type: string;
  how_users_use_it: string;
  limitation: string;
  confidence: number;
  source?: string | null;
};

export type OutreachTarget = {
  opportunity_id: string;
  github_user?: string | null;
  source_url: string;
  source_repo: string;
  pain_type: string;
  why_contact: string;
  outreach_angle: string;
};

export type ValidationPlan = {
  opportunity_id: string;
  goal: string;
  seven_day_plan: string[];
  success_criteria: string[];
  failure_criteria: string[];
  recommended_next_step: "build" | "validate" | "watch" | "reject";
};

export type StartupMemo = {
  opportunity_id: string;
  title: string;
  target_buyer: string;
  end_user: string;
  pain_summary: string;
  evidence_summary: string;
  commercial_gap: string;
  current_alternatives: string[];
  willingness_to_pay_hypothesis: string;
  mvp: string[];
  pricing_hypothesis: string;
  outreach_targets: string[];
  validation_plan: string[];
  risks: string[];
  final_decision: "build" | "validate" | "watch" | "reject";
};

export type CommercialValidation = {
  buyer?: BuyerHypothesis;
  wtpSignals: WillingnessToPaySignal[];
  alternatives: CompetitorAlternative[];
  outreachTargets: OutreachTarget[];
  validationPlan?: ValidationPlan;
  startupMemo?: StartupMemo;
};

export type EvidenceItem = {
  evidence_id: string;
  repo_owner?: string;
  repo_name?: string;
  repo_url?: string;
  source_type?: string;
  source_url?: string;
  title?: string;
  body?: string;
  labels?: string[];
  author_login?: string;
  comment_count?: number;
  reaction_count?: number;
  state?: string;
  is_mock?: boolean;
  matched_signals?: string[];
  rank_reason?: string;
  evidence_quality_score?: number;
};

export type AgentReview = {
  opportunity_id: string;
  agent: string;
  score: number;
  key_argument: string;
  main_risk: string;
  recommendation: string;
};

export type FinalDecision = {
  opportunity_id: string;
  decision: string;
  score: number;
  best_product_form?: string;
  migration_cost?: string;
  reason?: string;
  top_risks?: string[];
  first_validation_action?: string;
  decision_confidence?: number;
};

export type FusionCandidate = {
  fusion_id: string;
  title: string;
  user_query_anchor?: string;
  pain?: Record<string, unknown>;
  capability?: Record<string, unknown>;
  research_evidence?: Array<Record<string, unknown>>;
  fusion_thesis?: string;
  why_combination_makes_sense?: string;
  product_angle?: string;
  target_user?: string;
  evidence_ids?: string[];
  repo_ids?: string[];
  paper_ids?: string[];
  novelty_score?: number;
  feasibility_score?: number;
  evidence_strength?: number;
  commercial_potential?: number;
  overall_score?: number;
  risks?: string[];
  validation?: {
    is_valid?: boolean;
    validation_status?: string;
    rejection_reasons?: string[];
    warnings?: string[];
  };
};

export type RepoCapability = {
  capability_id?: string;
  name?: string;
  description?: string;
  source_repo?: string;
  maturity_score?: number;
  implementation_clues?: string[];
  related_methods?: string[];
  evidence_ids?: string[];
};

export type ResearchEvidence = {
  paper_id?: string;
  title?: string;
  url?: string;
  abstract?: string;
  claim_summary?: string;
  supports?: string[];
  limitation?: string;
  confidence?: number;
  evidence_role?: string;
};

export type RunState = {
  run_id: string;
  user_query?: string;
  canonical_topic?: string;
  query_scope?: Record<string, unknown>;
  search_plan?: Record<string, unknown>;
  refinement_required?: boolean;
  refinement_question?: string;
  suggested_queries?: string[];
  evidence_items?: EvidenceItem[];
  classified_issues?: ClassifiedIssue[];
  pain_points?: PainPoint[];
  pain_clusters?: Array<Record<string, unknown>>;
  rejected_pain_clusters?: Array<Record<string, unknown>>;
  commercial_gaps?: Array<Record<string, unknown>>;
  opportunity_cards?: OpportunityCardData[];
  rejected_cards?: OpportunityCardData[];
  buyer_hypotheses?: BuyerHypothesis[];
  wtp_signals?: WillingnessToPaySignal[];
  competitor_alternatives?: CompetitorAlternative[];
  outreach_targets?: OutreachTarget[];
  validation_plans?: ValidationPlan[];
  startup_memos?: StartupMemo[];
  signal_diagnostics?: SignalDiagnostics;
  final_decisions?: FinalDecision[];
  agent_reviews?: AgentReview[];
  opportunity_graph?: Record<string, unknown>;
  graph_nodes?: Array<Record<string, unknown>>;
  graph_edges?: Array<Record<string, unknown>>;
  repo_capabilities?: RepoCapability[];
  research_evidence?: ResearchEvidence[];
  fusion_candidates?: FusionCandidate[];
  validated_fusion_candidates?: FusionCandidate[];
  rejected_fusion_candidates?: FusionCandidate[];
  node_latency_summary?: Array<Record<string, unknown>>;
  errors?: string[];
};

export type ClassifiedIssue = {
  evidence_id?: string;
  evidence_ids?: string[];
  issue_id?: string;
  value_level?: string;
  category?: string;
  reason?: string;
  labels_matched?: string[];
  should_extract_pain?: boolean;
};

export type PainPoint = {
  pain_id?: string;
  evidence_id?: string;
  evidence_ids?: string[];
  issue_id?: string;
  pain_type?: string;
  complaint?: string;
  persona?: string;
  context?: string;
  severity?: number;
  business_signal?: string;
  supporting_quote?: string;
  workaround?: string;
};

export type EvidenceReason = {
  evidence_id: string;
  repo_label: string;
  repo_url?: string;
  source_url?: string;
  title: string;
  why_this_matters: string;
  user_pain?: string;
  commercial_signal?: string;
  evidence_strength: string[];
  quote?: string;
  labels: string[];
  matched_signals: string[];
  debug?: {
    raw_ranking_reason?: string;
    matched_count?: number;
    comments?: number;
    reactions?: number;
    negatives?: number;
    classifier_category?: string;
    internal_evidence_score?: number;
    raw_state_fields?: Record<string, unknown>;
  };
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function createRun(
  topic: string,
  dynamicSearch: boolean,
  options?: {
    preflightId?: string | null;
    runMode?: "quick" | "standard" | "deep";
    signal?: AbortSignal;
  },
) {
  return request<{ run_id: string; status: string }>("/runs", {
    method: "POST",
    signal: options?.signal,
    body: JSON.stringify({
      topic,
      dynamic_search: dynamicSearch,
      preflight_id: options?.preflightId || null,
      run_mode: options?.runMode || "standard",
    }),
  });
}

export async function preflightRun(topic: string, dynamicSearch: boolean, options?: { signal?: AbortSignal }) {
  return request<RunPreflight>("/runs/preflight", {
    method: "POST",
    signal: options?.signal,
    body: JSON.stringify({ topic, dynamic_search: dynamicSearch }),
  });
}

export async function getRunStatus(runId: string, options?: { signal?: AbortSignal }) {
  return request<RunStatus>(`/runs/${runId}/status`, { signal: options?.signal });
}

export async function listRuns() {
  return request<{ runs: RunListItem[] }>("/runs");
}

export async function getRun(runId: string) {
  return request<RunState>(`/runs/${runId}`);
}

export async function getRunSummary(runId: string) {
  return request<RunSummary>(`/runs/${runId}/summary`);
}

export async function getRunOpportunities(runId: string) {
  return request<{ run_id: string; count: number; opportunities: OpportunityCardData[] }>(
    `/runs/${runId}/opportunities`,
  );
}

export async function getRunReport(runId: string) {
  return request<{ run_id: string; report_markdown: string }>(`/runs/${runId}/report`);
}

export async function getOpportunityEvidence(opportunityId: string) {
  return request<{ opportunity_id: string; count: number; evidence_items: EvidenceItem[] }>(
    `/opportunities/${opportunityId}/evidence`,
  );
}
