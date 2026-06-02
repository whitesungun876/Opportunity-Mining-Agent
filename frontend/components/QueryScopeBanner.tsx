type Props = {
  queryScope?: Record<string, unknown>;
};

function scopeValue(queryScope?: Record<string, unknown>) {
  return typeof queryScope?.scope === "string" ? queryScope.scope : "broad";
}

function scopeCopy(scope: string, queryScope?: Record<string, unknown>) {
  if (scope === "focused") {
    return {
      title: "Focused validation mode",
      body: "This run prioritizes precise GitHub evidence for a specific production workflow.",
      tone: "border-blue-200 bg-gradient-to-r from-blue-50 to-white text-blue-950",
      badge: "border-blue-200 bg-blue-100 text-blue-900",
    };
  }
  if (scope === "repo_specific") {
    const repo =
      typeof queryScope?.repo_owner === "string" && typeof queryScope?.repo_name === "string"
        ? `${queryScope.repo_owner}/${queryScope.repo_name}`
        : "the selected repo";
    return {
      title: "Repo-specific analysis",
      body: `This run analyzes issues and discussions from ${repo}.`,
      tone: "border-violet-200 bg-gradient-to-r from-violet-50 to-white text-violet-950",
      badge: "border-violet-200 bg-violet-100 text-violet-900",
    };
  }
  if (scope === "ambiguous") {
    return {
      title: "Query needs refinement",
      body: "This query is too broad to analyze well. Try one of the suggested directions before generating opportunity cards.",
      tone: "border-amber-200 bg-gradient-to-r from-amber-50 to-white text-amber-950",
      badge: "border-amber-200 bg-amber-100 text-amber-900",
    };
  }
  return {
    title: "Broad exploration mode",
    body: "This run explores multiple opportunity directions. Use a focused query for deeper validation.",
    tone: "border-teal-200 bg-gradient-to-r from-teal-50 to-white text-teal-950",
    badge: "border-teal-200 bg-teal-100 text-teal-900",
  };
}

export default function QueryScopeBanner({ queryScope }: Props) {
  const scope = scopeValue(queryScope);
  const copy = scopeCopy(scope, queryScope);

  return (
    <section className={`mb-4 max-w-5xl rounded-xl border px-4 py-3 shadow-sm ${copy.tone}`}>
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="label-copy opacity-80">Query scope</p>
          <h2 className="mt-1 text-base font-semibold">{copy.title}</h2>
          <p className="mt-1 text-sm leading-6 opacity-85">{copy.body}</p>
        </div>
        <span className={`w-fit rounded-full border px-2.5 py-1 text-xs font-semibold uppercase ${copy.badge}`}>
          {scope.replace("_", " ")}
        </span>
      </div>
    </section>
  );
}
