import { MessageSquareText, Scale, ShieldAlert } from "lucide-react";
import { AgentReview, FinalDecision, OpportunityCardData } from "@/lib/api";

type Props = {
  cards: OpportunityCardData[];
  reviews: AgentReview[];
  decisions: FinalDecision[];
};

function reviewsByOpportunity(reviews: AgentReview[]) {
  const map = new Map<string, AgentReview[]>();
  for (const review of reviews) {
    const current = map.get(review.opportunity_id) || [];
    current.push(review);
    map.set(review.opportunity_id, current);
  }
  return map;
}

function decisionsByOpportunity(decisions: FinalDecision[]) {
  const map = new Map<string, FinalDecision>();
  for (const decision of decisions) {
    map.set(decision.opportunity_id, decision);
  }
  return map;
}

export default function DebateProcessPanel({ cards, reviews, decisions }: Props) {
  const reviewMap = reviewsByOpportunity(reviews);
  const decisionMap = decisionsByOpportunity(decisions);

  return (
    <aside className="rounded-lg border border-border bg-white shadow-sm xl:sticky xl:top-4 xl:self-start">
      <div className="border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <MessageSquareText className="h-4 w-4 text-primary" />
          <h2 className="text-base font-semibold text-foreground">Debate process</h2>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Structured agent review before the final judge.
        </p>
      </div>

      {cards.length === 0 ? (
        <div className="px-4 py-5 text-sm text-muted-foreground">
          No validated cards entered debate.
        </div>
      ) : (
        <div className="max-h-[calc(100dvh-120px)] overflow-y-auto">
          {cards.map((card) => {
            const cardReviews = reviewMap.get(card.opportunity_id) || [];
            const decision = decisionMap.get(card.opportunity_id);
            return (
              <section key={card.opportunity_id} className="border-b border-border px-4 py-4 last:border-b-0">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold leading-snug text-foreground">{card.title}</h3>
                    <p className="mt-1 text-xs text-muted-foreground">{card.opportunity_id}</p>
                  </div>
                  {decision ? (
                    <div className="shrink-0 rounded-md border border-emerald-100 bg-emerald-50 px-2 py-1 text-right">
                      <p className="text-xs font-semibold uppercase text-emerald-800">{decision.decision}</p>
                      <p className="text-xs text-emerald-900">{decision.score}</p>
                    </div>
                  ) : null}
                </div>

                {decision ? (
                  <div className="mt-3 rounded-md border border-border bg-background px-3 py-3">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                      <Scale className="h-3.5 w-3.5" />
                      Final judge
                    </div>
                    <p className="mt-2 text-sm leading-6 text-foreground">
                      {decision.reason || "Final decision is based on available agent reviews."}
                    </p>
                    {decision.first_validation_action ? (
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        Next: {decision.first_validation_action}
                      </p>
                    ) : null}
                  </div>
                ) : null}

                <div className="mt-3 space-y-2">
                  {cardReviews.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No agent reviews recorded.</p>
                  ) : (
                    cardReviews.map((review) => (
                      <article key={`${review.opportunity_id}-${review.agent}`} className="rounded-md border border-border bg-white px-3 py-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="rounded-md bg-muted px-2 py-1 text-xs font-semibold text-foreground">
                              {review.agent}
                            </span>
                            <span className="text-xs font-medium text-muted-foreground">
                              {review.recommendation}
                            </span>
                          </div>
                          <span className="text-xs font-semibold text-muted-foreground">{review.score}/10</span>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-foreground">{review.key_argument}</p>
                        {review.main_risk ? (
                          <p className="mt-2 flex gap-2 text-sm leading-6 text-muted-foreground">
                            <ShieldAlert className="mt-1 h-3.5 w-3.5 shrink-0 text-amber-700" />
                            <span>{review.main_risk}</span>
                          </p>
                        ) : null}
                      </article>
                    ))
                  )}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </aside>
  );
}
