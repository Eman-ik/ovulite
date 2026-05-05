import { useEffect, useMemo, useRef, useState } from "react";
import { Bot, Lightbulb, SendHorizonal, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

type Contribution = {
  feature: string;
  value: number;
};

type PredictionContext = {
  probability: number;
  confidence_lower: number;
  confidence_upper: number;
  risk_band: string;
  shap_explanation: {
    contributions: Contribution[];
  };
} | null;

type Message = {
  role: "assistant" | "user";
  content: string;
};

type Props = {
  prediction: PredictionContext;
  loading?: boolean;
};

const QUICK_PROMPTS = [
  "Explain confidence interval",
  "Why this risk band?",
  "Top factors driving score",
  "What should we improve next cycle?",
  "Give plain-language summary",
];

export default function PredictionAssistantChatbox({ prediction, loading = false }: Props) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "I am your Ovulite assistant. Ask me to explain confidence, risk band, feature-level reasons, and practical next-step suggestions.",
    },
  ]);
  const viewportRef = useRef<HTMLDivElement | null>(null);

  const statusBadge = useMemo(() => {
    if (loading) return "Processing prediction...";
    if (!prediction) return "Waiting for prediction context";
    return `Context loaded: ${(prediction.probability * 100).toFixed(1)}% (${prediction.risk_band})`;
  }, [loading, prediction]);

  useEffect(() => {
    if (!prediction) return;

    const summary = buildSummary(prediction);
    setMessages((prev) => {
      const alreadySummarized = prev.some(
        (m) => m.role === "assistant" && m.content.startsWith("Prediction summary:"),
      );
      if (alreadySummarized) return prev;
      return [
        ...prev,
        {
          role: "assistant",
          content: `Prediction summary:\n${summary}`,
        },
      ];
    });
  }, [prediction]);

  useEffect(() => {
    if (!viewportRef.current) return;
    viewportRef.current.scrollTop = viewportRef.current.scrollHeight;
  }, [messages]);

  const ask = (question: string) => {
    const trimmed = question.trim();
    if (!trimmed) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    const response = generateAssistantResponse(trimmed, prediction);
    setMessages((prev) => [...prev, { role: "assistant", content: response }]);
    setInput("");
  };

  return (
    <Card className="ov-reveal ov-stagger-5 ov-hover-lift">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Bot className="h-4 w-4" />
            Ovulite Assistant
          </CardTitle>
          <Badge variant="outline" className="text-[10px]">
            {statusBadge}
          </Badge>
        </div>
        <CardDescription>
          Confidence explanation, feature reasoning, and practical cycle suggestions.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div ref={viewportRef} className="max-h-72 space-y-2 overflow-y-auto rounded-md border border-[var(--surface-border)] bg-white/75 p-2 shadow-inner backdrop-blur-sm">
          {messages.map((m, idx) => (
            <div
              key={`${m.role}-${idx}`}
              className={`rounded-md px-3 py-2 text-xs leading-relaxed ${
                m.role === "assistant"
                  ? "border border-primary/15 bg-emerald-50/80 text-foreground"
                  : "border border-[var(--surface-border)] bg-white/90 text-foreground"
              }`}
            >
              <div className="mb-1 flex items-center gap-1.5 font-semibold">
                {m.role === "assistant" ? <Bot className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
                {m.role === "assistant" ? "Assistant" : "You"}
              </div>
              <p className="whitespace-pre-line">{m.content}</p>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          {QUICK_PROMPTS.map((p) => (
            <Button key={p} type="button" variant="outline" size="sm" className="h-7 text-[11px]" onClick={() => ask(p)}>
              <Lightbulb className="mr-1 h-3 w-3" />
              {p}
            </Button>
          ))}
        </div>

        <div className="flex gap-2">
          <Input
            placeholder="Ask why this score/confidence happened, or ask for suggestions..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") ask(input);
            }}
          />
          <Button type="button" onClick={() => ask(input)} disabled={!input.trim()}>
            <SendHorizonal className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function generateAssistantResponse(question: string, prediction: PredictionContext): string {
  if (!prediction) {
    return [
      "No prediction context is available yet.",
      "Run a prediction first, then I can explain:",
      "- confidence interval meaning",
      "- top positive and negative feature contributions",
      "- specific cycle-level suggestions",
    ].join("\n");
  }

  const q = question.toLowerCase();

  if (q.includes("confidence")) {
    return explainConfidence(prediction);
  }

  if (q.includes("risk") || q.includes("why")) {
    return explainRiskBand(prediction);
  }

  if (q.includes("top") || q.includes("factor") || q.includes("driver") || q.includes("reason")) {
    return explainTopDrivers(prediction);
  }

  if (q.includes("improve") || q.includes("suggest") || q.includes("next") || q.includes("action")) {
    return buildSuggestions(prediction);
  }

  if (q.includes("summary") || q.includes("plain") || q.includes("overall")) {
    return buildSummary(prediction);
  }

  return [
    buildSummary(prediction),
    "",
    buildSuggestions(prediction),
  ].join("\n");
}

function explainConfidence(prediction: NonNullable<PredictionContext>): string {
  const width = prediction.confidence_upper - prediction.confidence_lower;
  let strength = "moderate";
  if (width <= 0.15) strength = "high";
  else if (width >= 0.35) strength = "low";

  return [
    `Confidence interval: ${(prediction.confidence_lower * 100).toFixed(1)}% to ${(prediction.confidence_upper * 100).toFixed(1)}%.`,
    `Interval width: ${(width * 100).toFixed(1)} points, so confidence is ${strength}.`,
    "Interpretation:",
    "- Narrow range => the model is more certain for this case.",
    "- Wide range => prediction is more uncertain and should be reviewed with more caution.",
  ].join("\n");
}

function explainRiskBand(prediction: NonNullable<PredictionContext>): string {
  const p = prediction.probability;
  return [
    `Risk band: ${prediction.risk_band}. Predicted probability: ${(p * 100).toFixed(1)}%.`,
    `This band is assigned based on where the score falls in configured model thresholds.`,
    `Use it together with confidence interval and feature drivers, not as a standalone decision.`
  ].join("\n");
}

function explainTopDrivers(prediction: NonNullable<PredictionContext>): string {
  const sorted = [...prediction.shap_explanation.contributions]
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 6);

  const positive = sorted.filter((x) => x.value > 0).slice(0, 3);
  const negative = sorted.filter((x) => x.value < 0).slice(0, 3);

  const posText = positive.length
    ? positive.map((x) => `+ ${toLabel(x.feature)} (${x.value.toFixed(4)})`).join("\n")
    : "No strong positive drivers were detected.";
  const negText = negative.length
    ? negative.map((x) => `- ${toLabel(x.feature)} (${x.value.toFixed(4)})`).join("\n")
    : "No strong negative drivers were detected.";

  return [
    "Top positive drivers:",
    posText,
    "",
    "Top negative drivers:",
    negText,
    "",
    "These values represent feature-level directional contribution in the current prediction context.",
  ].join("\n");
}

function buildSuggestions(prediction: NonNullable<PredictionContext>): string {
  const contributions = prediction.shap_explanation.contributions;
  const byFeature = (key: string) => contributions.find((c) => c.feature.toLowerCase().includes(key));

  const suggestions: string[] = [];

  const cl = byFeature("cl_measure") ?? byFeature("cl");
  if (cl && cl.value < 0) {
    suggestions.push("Re-check recipient CL quality/timing alignment before transfer window.");
  }

  const grade = byFeature("embryo_grade");
  if (grade && grade.value < 0) {
    suggestions.push("Prioritize embryos with stronger morphology signal when clinically feasible.");
  }

  const stage = byFeature("embryo_stage");
  if (stage && stage.value < 0) {
    suggestions.push("Review stage-specific transfer timing protocol for this cohort.");
  }

  const protocol = byFeature("protocol");
  if (protocol && protocol.value < 0) {
    suggestions.push("Compare protocol-specific performance in analytics before next cycle.");
  }

  const freshFrozen = byFeature("fresh_or_frozen");
  if (freshFrozen && freshFrozen.value < 0) {
    suggestions.push("Evaluate whether alternative fresh/frozen strategy could reduce risk for similar cases.");
  }

  const width = prediction.confidence_upper - prediction.confidence_lower;
  if (width > 0.3) {
    suggestions.push("Prediction uncertainty is high; gather more complete metadata before final decision.");
  }

  if (suggestions.length === 0) {
    suggestions.push("Current feature profile is comparatively favorable; maintain protocol consistency and continue monitoring quality controls.");
  }

  return [
    "Suggested next steps:",
    ...suggestions.map((s) => `- ${s}`),
    "",
    "Note: Suggestions are decision-support guidance and should be reviewed by embryology/clinical experts.",
  ].join("\n");
}

function buildSummary(prediction: NonNullable<PredictionContext>): string {
  const width = prediction.confidence_upper - prediction.confidence_lower;
  const confidenceTier = width <= 0.15 ? "high" : width <= 0.3 ? "moderate" : "low";

  const top = [...prediction.shap_explanation.contributions]
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 3)
    .map((x) => `${toLabel(x.feature)} (${x.value > 0 ? "+" : ""}${x.value.toFixed(4)})`)
    .join(", ");

  return [
    `- Probability: ${(prediction.probability * 100).toFixed(1)}% (${prediction.risk_band}).`,
    `- Confidence interval: ${(prediction.confidence_lower * 100).toFixed(1)}% to ${(prediction.confidence_upper * 100).toFixed(1)}% (${confidenceTier} confidence).`,
    `- Most influential factors: ${top || "not available"}.`,
  ].join("\n");
}

function toLabel(name: string): string {
  if (name.includes("__")) {
    const [base, value] = name.split("__");
    const label = base
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
    return `${label}: ${value}`;
  }

  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace("Cl ", "CL ")
    .replace("Bc ", "BC ")
    .replace("Bw ", "BW ")
    .replace("Opu", "OPU");
}
