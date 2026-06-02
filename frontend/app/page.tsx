import { CheckCircle2, Lightbulb, Search, ShieldCheck, Sparkles } from "lucide-react";
import TopicInput from "@/components/TopicInput";

const steps = [
  { label: "Search GitHub", icon: Search, tone: "bg-sky-50 text-sky-700 border-sky-100" },
  { label: "Extract pain", icon: Lightbulb, tone: "bg-amber-50 text-amber-700 border-amber-100" },
  { label: "Validate evidence", icon: ShieldCheck, tone: "bg-emerald-50 text-emerald-700 border-emerald-100" },
  { label: "Review opportunity", icon: CheckCircle2, tone: "bg-violet-50 text-violet-700 border-violet-100" },
];

type PageProps = {
  searchParams?: Promise<{ q?: string }>;
};

export default async function Page({ searchParams }: PageProps) {
  const params = searchParams ? await searchParams : {};
  const initialTopic = typeof params.q === "string" ? params.q : "";

  return (
    <main className="soft-grid-bg min-h-dvh">
      <section className="mx-auto max-w-5xl px-4 pb-8 pt-10 sm:px-6 sm:pt-14 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-white/90 px-3 py-1.5 section-kicker shadow-sm">
            <Sparkles className="h-3.5 w-3.5" />
            Evidence-first AI research tool
          </div>

          <h1 className="display-title mx-auto mt-5 max-w-4xl">
            Find startup opportunities hidden in GitHub issues.
          </h1>
          <p className="body-copy mx-auto mt-5 max-w-2xl sm:text-lg">
            Turn real developer pain into evidence-backed SaaS, plugin, and hosted-service ideas.
          </p>
        </div>

        <div className="mx-auto mt-7 max-w-4xl">
          <TopicInput initialTopic={initialTopic} />
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 pb-8 sm:px-6 lg:px-8">
        <div className="surface-card rounded-xl p-4">
          <div>
            <p className="section-kicker">How it works</p>
            <h2 className="mt-1 section-title text-xl">From GitHub signal to opportunity judgment.</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              The workflow separates source evidence, pain extraction, validation, and review so the result reads like an opportunity memo.
            </p>
          </div>
          <div className="mt-4 flex items-stretch gap-2 overflow-x-auto pb-1 text-sm">
            {steps.map((step, index) => {
              const Icon = step.icon;
              return (
                <div key={step.label} className="flex min-w-[11rem] flex-1 items-stretch gap-2">
                  <div className="min-w-[9.5rem] flex-1 rounded-lg border border-border bg-white p-3 shadow-sm">
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex h-8 w-8 items-center justify-center rounded-md border ${step.tone}`}>
                        <Icon className="h-4 w-4" />
                      </span>
                      <span className="label-copy text-muted-foreground">0{index + 1}</span>
                    </div>
                    <p className="mt-3 text-sm font-semibold text-foreground">{step.label}</p>
                  </div>
                  {index < steps.length - 1 ? (
                    <div className="flex items-center justify-center text-lg text-muted-foreground/60">
                      →
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      </section>

    </main>
  );
}
