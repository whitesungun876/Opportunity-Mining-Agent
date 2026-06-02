import { AgentReview, FinalDecision } from "@/lib/api";

type Props = {
  decision?: FinalDecision;
  reviews: AgentReview[];
};

export default function DebateSummary({ decision, reviews }: Props) {
  if (!decision && reviews.length === 0) {
    return null;
  }

  return (
    <section>
      {decision ? (
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-primary px-2 py-1 text-xs font-semibold uppercase text-primary-foreground shadow-sm">
              {decision.decision}
            </span>
            <span className="text-sm font-medium text-foreground">Score {decision.score}</span>
            {decision.decision_confidence !== undefined ? (
              <span className="text-xs text-muted-foreground">
                confidence {Math.round(decision.decision_confidence * 100)}%
              </span>
            ) : null}
          </div>
          {decision.reason ? <p className="mt-2 text-sm text-muted-foreground">{decision.reason}</p> : null}
        </div>
      ) : null}

      {reviews.length ? (
        <div className="mt-3 overflow-hidden rounded-md border border-border">
          {reviews.map((review) => (
            <div key={`${review.opportunity_id}-${review.agent}`} className="grid grid-cols-[110px_1fr_64px] items-center gap-2 border-t border-border bg-background px-3 py-2 first:border-t-0">
              <p className="text-xs font-semibold text-foreground">{review.agent}</p>
              <p className="truncate text-xs text-muted-foreground">{review.recommendation}</p>
              <p className="text-right text-xs font-medium text-muted-foreground">{review.score}/10</p>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
