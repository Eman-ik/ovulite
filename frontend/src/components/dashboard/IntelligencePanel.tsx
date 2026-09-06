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
        <Brain className="h-5 w-5 text-emerald-600" />
        <h3 className="text-lg font-semibold text-gray-900">Ovulite Intelligence</h3>
      </div>

      {error && !modelInfo ? (
        <p className="text-sm text-gray-500">{error}</p>
      ) : modelInfo ? (
        <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-3 text-sm">
          <p className="font-medium text-emerald-900">
            {modelInfo.model_name} · {modelInfo.model_version}
          </p>
          <p className="text-xs text-emerald-700">
            {modelInfo.n_features} features · best model: {modelInfo.best_model_key} ·{" "}
            {modelInfo.artifact_integrity_verified ? "integrity verified" : "integrity unverified"}
          </p>
        </div>
      ) : (
        <p className="text-sm text-gray-400">Loading model info…</p>
      )}

      {summary ? (
        <div className="space-y-2">
          <p className="text-sm text-gray-700">
            <span className="font-semibold">{summary.pending_predictions_count}</span> predictions have no recorded
            outcome yet.
          </p>
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
              High-Risk Transfers ({summary.high_risk_transfers.length})
            </p>
            {summary.high_risk_transfers.length === 0 ? (
              <p className="text-sm text-gray-400">No high-risk pending transfers flagged.</p>
            ) : (
              <ul className="space-y-1">
                {summary.high_risk_transfers.slice(0, 5).map((t) => (
                  <li key={t.transfer_id} className="flex items-center justify-between rounded-lg bg-rose-50 px-3 py-1.5 text-xs text-rose-800">
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
