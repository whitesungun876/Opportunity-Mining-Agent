"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, Copy } from "lucide-react";

type Props = {
  markdown: string;
};

export default function MarkdownReportPreview({ markdown }: Props) {
  const [copied, setCopied] = useState(false);

  async function copyMarkdown() {
    await navigator.clipboard.writeText(markdown || "");
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <section className="rounded-lg border border-border bg-white shadow-sm xl:sticky xl:top-4 xl:self-start">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div>
          <h2 className="text-base font-semibold text-foreground">Report preview</h2>
          <p className="text-sm text-muted-foreground">Template report with evidence links.</p>
        </div>
        <button
          type="button"
          onClick={() => void copyMarkdown()}
          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-foreground transition hover:bg-muted"
        >
          {copied ? <Check className="h-4 w-4 text-emerald-700" /> : <Copy className="h-4 w-4" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div className="max-h-[calc(100dvh-140px)] overflow-y-auto px-4 py-4">
        {markdown ? (
          <div className="prose-report">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No report markdown returned.</p>
        )}
      </div>
    </section>
  );
}
