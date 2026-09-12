import { useEffect, useState } from "react";
import { AlertTriangle, Brain, Info, TrendingUp } from "lucide-react";
import api from "@/lib/api";
import type { ModelPerformanceResponse } from "@/lib/types";

/**
 * Model performance, straight from the trained artifact.
 *
 * This page previously called `/models/performance` — a route that has never
 * existed — and on every single load fell back to a hardcoded object claiming
 * ROC-AUC 0.78 and accuracy 0.81, behind nothing but a console.warn. Those
 * numbers describe no model; the real artifact is at 0.510, which is inside
 * the shuffled-label null for this dataset. A vet reading "81% accurate" and
 * deciding to trust a prediction is the exact harm the SRS's "explainable,
 * evidence-linked" principle exists to prevent.
 *
 * So: no fallback. If the artifact cannot be read, the page says so.
 */
function errorText(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return err instanceof Error ? err.message : "Request failed";
}

function Metric({ label, value, digits = 3 }: { label: string; value: number | null; digits?: number }) {
  return (
    <div className="dash-tile p-3.5">
      <p className="text-[11px] font-medium uppercase leading-tight tracking-wide dash-muted">
        {label}
      </p>
      <p className="mt-2 text-[22px] font-semibold leading-none dash-heading">
        {value === null || value === undefined ? (
          <span className="text-base font-normal dash-muted">not recorded</span>
        ) : (
          value.toFixed(digits)
        )}
      </p>
    </div>
  );
}

export default function ModelPerformancePage() {
  const [data, setData] = useState<ModelPerformanceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<ModelPerformanceResponse>("/predict/performance")
      .then((r) => setData(r.data))
      .catch((err) => setError(errorText(err)));
  }, []);

  const best = data?.models.find((m) => m.model_key === data.best_model) ?? data?.models[0] ?? null;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold dash-heading">Model Performance</h1>
        <p className="mt-1 text-sm dash-muted">
          Holdout metrics recorded when the deployed artifact was trained. Nothing on this page is
          estimated or filled in — if a figure is missing, it says so.
        </p>
      </div>

      {error && (
        <div className="rounded-2xl border border-[rgba(179,69,63,0.28)] bg-[rgba(185,142,168,0.16)] p-4 text-sm text-[#9d3730]">
          <p className="font-semibold">Could not load model performance</p>
          <p className="mt-1">{error}</p>
          <p className="mt-2 text-xs">
            No substitute figures are shown. Any number here would be indistinguishable from a real
            measurement.
          </p>
        </div>
      )}

      {data && !data.available && (
        <div className="rounded-2xl border border-[rgba(35,131,111,0.32)] bg-[rgba(208,164,94,0.14)] p-4 text-sm text-[#6b5a1c]">
          <p className="font-semibold text-[#7a5a12]">No model artifact available</p>
          <p className="mt-1">{data.interpretation}</p>
          {data.unavailable_reason && <p className="mt-1 text-xs">{data.unavailable_reason}</p>}
        </div>
      )}

      {data?.available && (
        <>
          {/* The headline judgement, not just the number. */}
          <div
            className={`dash-card border-l-4 ${
              data.is_better_than_chance
                ? "border-l-[#8EB69B]"
                : "border-l-[#9d3730]"
            }`}
          >
            <div className="flex items-start gap-3">
              {data.is_better_than_chance ? (
                <TrendingUp className="mt-0.5 h-5 w-5 text-[#235347]" />
              ) : (
                <AlertTriangle className="mt-0.5 h-5 w-5 text-[#9d3730]" />
              )}
              <div>
                <p
                  className={`text-base font-semibold ${
                    data.is_better_than_chance ? "text-[#235347]" : "text-[#9d3730]"
                  }`}
                >
                  {data.is_better_than_chance
                    ? "Discrimination above chance"
                    : "Not distinguishable from chance"}
                </p>
                <p className="mt-1.5 max-w-3xl text-sm leading-relaxed dash-heading">
                  {data.interpretation}
                </p>
                <p className="mt-2 text-xs dash-muted">
                  Artifact {data.model_version ?? "—"}
                  {data.trained_at && ` · trained ${data.trained_at.slice(0, 10)}`}
                  {data.n_features !== null && ` · ${data.n_features} features`}
                </p>
              </div>
            </div>
          </div>

          {best && (
            <div className="dash-card">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 dash-muted" />
                <h2 className="text-base font-semibold dash-heading">
                  Selected model — {best.display_name}
                </h2>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
                <Metric label="ROC-AUC" value={best.roc_auc} />
                <Metric label="PR-AUC" value={best.pr_auc} />
                <Metric label="Brier score" value={best.brier_score} />
                <Metric label="Accuracy" value={best.accuracy} />
              </div>

              {best.confusion_matrix && (
                <>
                  <h3 className="mt-5 text-sm font-semibold dash-heading">Confusion matrix</h3>
                  <div className="mt-2 grid max-w-md grid-cols-2 gap-2">
                    {Object.entries(best.confusion_matrix).map(([k, v]) => (
                      <div key={k} className="dash-tile flex items-baseline justify-between p-3">
                        <span className="text-xs uppercase tracking-wide dash-muted">{k}</span>
                        <span className="text-lg font-semibold dash-heading">{v}</span>
                      </div>
                    ))}
                  </div>
                  {/* A matrix with no true positives is a constant predictor.
                      Worth stating outright rather than leaving to be noticed. */}
                  {Number(best.confusion_matrix.tp ?? 0) === 0 && (
                    <p className="mt-2 text-xs text-[#9d3730]">
                      Zero true positives: this model predicts the majority class for every case,
                      so precision and recall for pregnancy are both zero.
                    </p>
                  )}
                </>
              )}
            </div>
          )}

          <div className="dash-card">
            <h2 className="text-base font-semibold dash-heading">All trained models</h2>
            <div className="custom-scrollbar mt-4 overflow-x-auto">
              <table className="w-full min-w-[720px] text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide dash-muted">
                    <th className="pb-2 pr-4 font-medium">Model</th>
                    <th className="pb-2 pr-4 font-medium">ROC-AUC</th>
                    <th className="pb-2 pr-4 font-medium">PR-AUC</th>
                    <th className="pb-2 pr-4 font-medium">Brier</th>
                    <th className="pb-2 font-medium">Note</th>
                  </tr>
                </thead>
                <tbody>
                  {data.models.map((m) => (
                    <tr key={m.model_key} className="border-b border-[var(--border)] last:border-0">
                      <td className="py-2.5 pr-4 dash-heading">
                        {m.display_name}
                        {m.model_key === data.best_model && (
                          <span className="ml-2 rounded-full bg-black/[0.05] px-2 py-0.5 text-[10px] font-semibold dash-muted">
                            selected
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 dash-muted">{m.roc_auc?.toFixed(3) ?? "—"}</td>
                      <td className="py-2.5 pr-4 dash-muted">{m.pr_auc?.toFixed(3) ?? "—"}</td>
                      <td className="py-2.5 pr-4 dash-muted">{m.brier_score?.toFixed(3) ?? "—"}</td>
                      <td className="py-2.5 text-xs text-[#7a5a12]">{m.note ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {data.shap_top_features && data.shap_top_features.length > 0 && (
            <div className="dash-card">
              <h2 className="text-base font-semibold dash-heading">Top features (training-time SHAP)</h2>
              <p className="mt-1 text-xs dash-muted">
                Genuine Shapley values computed during training. The live prediction endpoint uses a
                linear surrogate instead, and labels itself as such.
              </p>
              <div className="mt-4 space-y-2">
                {data.shap_top_features.map(([name, value]) => {
                  const max = Math.max(...data.shap_top_features!.map(([, v]) => Math.abs(v)), 1e-9);
                  return (
                    <div key={name} className="grid grid-cols-[14rem_1fr_5rem] items-center gap-3">
                      <span className="truncate text-xs dash-heading" title={name}>
                        {name}
                      </span>
                      <div className="h-3 rounded bg-black/[0.04]">
                        <div
                          className="h-3 rounded bg-[#6aa5b8]"
                          style={{ width: `${(Math.abs(value) / max) * 100}%` }}
                        />
                      </div>
                      <span className="text-right text-xs dash-muted">{value.toFixed(4)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {data.split && (
            <div className="dash-card">
              <h2 className="text-base font-semibold dash-heading">Train / holdout split</h2>
              <div className="custom-scrollbar mt-3 overflow-x-auto">
                <pre className="text-xs leading-relaxed dash-muted">
                  {JSON.stringify(data.split, null, 2)}
                </pre>
              </div>
              <div className="mt-3 flex items-start gap-2 rounded-xl bg-[#f6faf7] px-3 py-2.5 text-[11px] leading-relaxed dash-muted">
                <Info className="mt-px h-3.5 w-3.5 shrink-0" />
                <span>
                  The split is temporal and falls on a regime boundary: pregnancy rate roughly
                  doubled in December 2025. That does not by itself lower ROC-AUC, which is
                  rank-based — see ml/diagnose_split.py and ml/permutation_test.py for the
                  evaluation that established the model is at chance regardless of split.
                </span>
              </div>
            </div>
          )}
        </>
      )}

      {!data && !error && <p className="text-sm dash-muted">Loading…</p>}
    </div>
  );
}
