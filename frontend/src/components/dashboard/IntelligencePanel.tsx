import { useEffect, useState } from "react";
import api from "@/lib/api";
import type { DashboardAISummaryResponse } from "@/lib/types";
import { Brain } from "lucide-react";

interface ModelInfo {
  model_name: string;
  model_version: string;
  n_features: number;
  best_model_key: string;
  artifact_integrity_verified: boolean;
}

export default function IntelligencePanel() {
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [summary, setSummary] = useState<DashboardAISummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      api.get<ModelInfo>("/predict/model-info"),
      api.get<DashboardAISummaryResponse>("/dashboard/ai-summary"),
    ]).then(([modelRes, summaryRes]) => {
      if (cancelled) return;
      if (modelRes.status === "fulfilled") setModelInfo(modelRes.value.data);
      else setError("No prediction model is currently loaded.");
      if (summaryRes.status === "fulfilled") setSummary(summaryRes.value.data);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Brain className="h-[18px] w-[18px] text-[var(--primary)]" strokeWidth={1.75} />
        <h3 className="text-base font-semibold dash-heading">Ovulite Intelligence</h3>
      </div>

      {error && !modelInfo ? (
        <p className="text-sm dash-muted">{error}</p>
      ) : modelInfo ? (
        <div className="dash-tile p-3.5 text-sm">
          <p className="font-medium text-[var(--primary)]">
            {modelInfo.model_name} · {modelInfo.model_version}
          </p>
          <p className="mt-0.5 text-xs dash-muted">
            {modelInfo.n_features} features · best model: {modelInfo.best_model_key} ·{" "}
            {modelInfo.artifact_integrity_verified ? "integrity verified" : "integrity unverified"}
          </p>
        </div>
      ) : (
        <p className="text-sm dash-muted">Loading model info…</p>
      )}

      {summary ? (
        <div className="space-y-3">
          <p className="text-sm dash-muted">
            <span className="font-semibold dash-heading">{summary.pending_predictions_count}</span> predictions have no
            recorded outcome yet.
          </p>
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide dash-muted">
              High-Risk Transfers ({summary.high_risk_transfers.length})
            </p>
            {summary.high_risk_transfers.length === 0 ? (
              <p className="text-sm dash-muted opacity-70">No high-risk pending transfers flagged.</p>
            ) : (
              <ul className="space-y-1.5">
                {summary.high_risk_transfers.slice(0, 5).map((t) => (
                  <li
                    key={t.transfer_id}
                    className="flex items-center justify-between rounded-xl border border-[rgba(224,101,111,0.25)] bg-[rgba(224,101,111,0.1)] px-3 py-2 text-xs text-[#f0a4aa]"
                  >
                    <span>Transfer #{t.transfer_id} {t.et_date ? `(${t.et_date})` : ""}</span>
                    <span className="font-semibold">{(t.probability * 100).toFixed(0)}% predicted</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
