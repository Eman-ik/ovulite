import React, { useEffect, useState } from "react";
import { BookOpen } from "lucide-react";

type InsightType = "research" | "warning" | "info" | "success";

interface Insight {
  id: string;
  type: InsightType;
  title: string;
  message: string;
  timestamp: string;
  relatedComponent?: string;
}

const IntelligenceFeed: React.FC = () => {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchInsights = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/autonomous-agent/research/discover?max_results=3").catch(() => null);
      const data = res ? await res.json() : { insights: [] };
      const cards: Insight[] = (data?.insights || []).map((ins: any, idx: number) => ({
        id: `research_${idx}`,
        type: "research",
        title: ins.title || "Research",
        message: ins.insight || "",
        timestamp: new Date().toLocaleTimeString(),
        relatedComponent: ins.related_components?.[0],
      }));
      setInsights(cards);
    } catch (e) {
      console.error("fetchInsights error", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, []);

  return (
    <div className="w-full p-4">
      <div className="rounded-lg border border-[var(--surface-border)] bg-[var(--surface-bg)] p-4 shadow-[0_18px_50px_rgba(15,23,42,0.06)] backdrop-blur-xl">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">Intelligence Feed</h3>
          <button onClick={fetchInsights} className="text-sm text-[var(--primary)] hover:opacity-80">
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="text-sm text-[var(--muted-foreground)]">Loading...</div>
        ) : insights.length ? (
          <div className="space-y-3">
            {insights.map((ins) => (
              <div key={ins.id} className="rounded-lg border border-[var(--surface-border)] bg-white/80 p-3 shadow-[0_10px_28px_rgba(15,23,42,0.04)]">
                <div className="flex items-start gap-3">
                  <div className="text-[var(--accent)]">
                    <BookOpen className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between items-start">
                      <div className="font-medium">{ins.title}</div>
                      <div className="text-xs text-[var(--muted-foreground)]">{ins.timestamp}</div>
                    </div>
                    <div className="text-sm text-[var(--muted-foreground)] mt-1">{ins.message}</div>
                    {ins.relatedComponent && (
                      <div className="mt-2 text-xs text-[var(--muted-foreground)]">Related: {ins.relatedComponent}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-[var(--muted-foreground)]">No insights available</div>
        )}
      </div>
    </div>
  );
};

export default IntelligenceFeed;
