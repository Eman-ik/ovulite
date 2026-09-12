import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, HeartPulse, Info, Search } from "lucide-react";
import api from "@/lib/api";
import { getPermissions } from "@/lib/roleRoutes";
import { useAuth } from "@/contexts/AuthContext";
import type {
  CheckMethod,
  CheckResult,
  RetentionResponse,
  TransferOutcomeChain,
} from "@/lib/types";

const RESULTS: CheckResult[] = ["Pregnant", "Open", "Recheck", "Lost"];
const METHODS: CheckMethod[] = ["Ultrasound", "Rectal Palpation", "Blood Test", "Other"];

const RESULT_STYLE: Record<CheckResult, string> = {
  Pregnant: "bg-[rgba(142,182,155,0.22)] text-[#235347]",
  Open: "bg-black/[0.05] dash-muted",
  Recheck: "bg-[rgba(208,164,94,0.24)] text-[#7a5a12]",
  Lost: "bg-[rgba(185,142,168,0.24)] text-[#9d3730]",
};

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function errorText(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return err instanceof Error ? err.message : "Request failed";
}

export default function PregnancyDiagnosisPage() {
  const { user } = useAuth();
  const canWrite = getPermissions(user?.role).canEnterETData;

  const [transferId, setTransferId] = useState("");
  const [chain, setChain] = useState<TransferOutcomeChain | null>(null);
  const [retention, setRetention] = useState<RetentionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<{ check_date: string; result: CheckResult; method: CheckMethod }>({
    check_date: todayISO(),
    result: "Pregnant",
    method: "Ultrasound",
  });

  useEffect(() => {
    api
      .get<RetentionResponse>("/vet/retention")
      .then((r) => setRetention(r.data))
      .catch(() => setRetention(null));
  }, []);

  const loadChain = useCallback(async (id: string) => {
    setError(null);
    setChain(null);
    if (!id.trim()) return;
    try {
      const { data } = await api.get<TransferOutcomeChain>(`/vet/transfers/${id}/outcome-chain`);
      setChain(data);
    } catch (err) {
      setError(errorText(err));
    }
  }, []);

  const addCheck = async () => {
    if (!chain) return;
    setSaving(true);
    setError(null);
    try {
      await api.post(`/vet/transfers/${chain.transfer_id}/pregnancy-checks`, draft);
      await loadChain(String(chain.transfer_id));
      const r = await api.get<RetentionResponse>("/vet/retention");
      setRetention(r.data);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold dash-heading">Pregnancy Diagnosis</h1>
        <p className="mt-1 text-sm dash-muted">
          The full diagnosis chain for a transfer — every check in order, plus calving. Recording a
          later check is what makes pregnancy loss visible.
        </p>
      </div>

      {error && (
        <div className="rounded-2xl border border-[rgba(179,69,63,0.28)] bg-[rgba(185,142,168,0.16)] p-4 text-sm text-[#9d3730]">
          {error}
        </div>
      )}

      {/* ── Retention ── */}
      <div className="dash-card">
        <div className="flex items-center gap-2">
          <HeartPulse className="h-4 w-4 dash-muted" />
          <h2 className="text-base font-semibold dash-heading">Retention</h2>
        </div>
        {!retention ? (
          <p className="mt-4 text-sm dash-muted">Loading…</p>
        ) : (
          <>
            <div className="custom-scrollbar mt-4 overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide dash-muted">
                    <th className="pb-2 pr-4 font-medium">Stage</th>
                    <th className="pb-2 pr-4 font-medium">Diagnosed</th>
                    <th className="pb-2 pr-4 font-medium">Pregnant</th>
                    <th className="pb-2 font-medium">Retained from previous</th>
                  </tr>
                </thead>
                <tbody>
                  {[...retention.stages, ...(retention.live_birth ? [retention.live_birth] : [])].map(
                    (s) => (
                      <tr key={s.label} className="border-b border-[var(--border)] last:border-0">
                        <td className="py-2.5 pr-4 dash-heading">{s.label}</td>
                        <td className="py-2.5 pr-4 dash-muted">{s.n}</td>
                        <td className="py-2.5 pr-4">
                          {s.rate_pct === null ? (
                            <span className="text-xs dash-muted">n={s.n} · too few</span>
                          ) : (
                            <>
                              <span className="font-semibold dash-heading">{s.rate_pct}%</span>
                              <span className="ml-1.5 text-xs dash-muted">
                                {s.pregnant}/{s.n}
                              </span>
                            </>
                          )}
                        </td>
                        <td className="py-2.5">
                          {s.retained_from_previous_pct === null ? (
                            <span className="dash-muted">—</span>
                          ) : (
                            <span className="font-medium text-[#235347]">
                              {s.retained_from_previous_pct}%
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
            {!retention.live_birth_tracked && (
              <div className="mt-4 flex items-start gap-2.5 rounded-2xl border border-[rgba(35,131,111,0.32)] bg-[rgba(208,164,94,0.14)] px-4 py-3 text-sm text-[#6b5a1c]">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[#7a5a12]" />
                <span>
                  Live birth is not tracked yet — no calving records exist, so the rate is withheld
                  rather than shown as 0%.
                </span>
              </div>
            )}
            <div className="mt-4 flex items-start gap-2 rounded-xl bg-[#f6faf7] px-3 py-2.5 text-[11px] leading-relaxed dash-muted">
              <Info className="mt-px h-3.5 w-3.5 shrink-0" />
              <span>{retention.note}</span>
            </div>
          </>
        )}
      </div>

      {/* ── Per-transfer chain ── */}
      <div className="dash-card">
        <h2 className="text-base font-semibold dash-heading">Transfer diagnosis chain</h2>
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <label className="text-xs dash-muted">
            Transfer ID
            <div className="mt-1 flex gap-2">
              <input
                value={transferId}
                onChange={(e) => setTransferId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void loadChain(transferId)}
                placeholder="e.g. 489"
                className="h-9 w-40 rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
              />
              <button
                type="button"
                onClick={() => void loadChain(transferId)}
                className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 text-xs font-medium transition hover:bg-black/[0.04]"
              >
                <Search className="h-3.5 w-3.5" />
                Load
              </button>
            </div>
          </label>
        </div>

        {chain && (
          <div className="mt-5">
            <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 rounded-2xl bg-[#f6faf7] p-4">
              <p className="text-sm dash-muted">
                Transfer <span className="font-semibold dash-heading">#{chain.transfer_id}</span>
              </p>
              <p className="text-sm dash-muted">
                Recipient <span className="dash-heading">{chain.recipient_tag ?? "—"}</span>
              </p>
              <p className="text-sm dash-muted">
                ET date <span className="dash-heading">{chain.et_date ?? "—"}</span>
              </p>
              <p className="text-sm dash-muted">
                Status <span className="font-semibold dash-heading">{chain.current_status}</span>
              </p>
            </div>

            {chain.checks.length === 0 ? (
              <p className="mt-4 text-sm dash-muted">No diagnosis recorded for this transfer yet.</p>
            ) : (
              <div className="custom-scrollbar mt-4 overflow-x-auto">
                <table className="w-full min-w-[600px] text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide dash-muted">
                      <th className="pb-2 pr-4 font-medium">Date</th>
                      <th className="pb-2 pr-4 font-medium">Day</th>
                      <th className="pb-2 pr-4 font-medium">Result</th>
                      <th className="pb-2 pr-4 font-medium">Method</th>
                      <th className="pb-2 font-medium">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {chain.checks.map((c) => (
                      <tr key={c.check_id} className="border-b border-[var(--border)] last:border-0">
                        <td className="py-2.5 pr-4 dash-heading">{c.check_date}</td>
                        <td className="py-2.5 pr-4">
                          {c.days_post_transfer === null ? (
                            <span className="dash-muted">—</span>
                          ) : c.implausible_offset ? (
                            <span
                              className="rounded-full bg-[rgba(185,142,168,0.24)] px-2 py-0.5 text-xs font-medium text-[#9d3730]"
                              title="This check is dated before its own transfer, or improbably long after it — a date-entry error upstream."
                            >
                              {c.days_post_transfer} ⚠
                            </span>
                          ) : (
                            <span className="dash-muted">{c.days_post_transfer}</span>
                          )}
                        </td>
                        <td className="py-2.5 pr-4">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${RESULT_STYLE[c.result]}`}
                          >
                            {c.result}
                          </span>
                        </td>
                        <td className="py-2.5 pr-4 dash-muted">{c.method ?? "—"}</td>
                        <td className="py-2.5 text-xs dash-muted">{c.notes ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {chain.calving && (
              <div className="mt-4 rounded-2xl bg-[rgba(142,182,155,0.14)] p-4 text-sm">
                <p className="font-semibold text-[#235347]">{chain.calving.outcome}</p>
                <p className="mt-1 dash-muted">
                  {chain.calving.calving_date}
                  {chain.calving.gestation_days && ` · ${chain.calving.gestation_days} days gestation`}
                  {chain.calving.calf_sex && ` · ${chain.calving.calf_sex}`}
                  {chain.calving.calf_weight_kg && ` · ${chain.calving.calf_weight_kg} kg`}
                </p>
              </div>
            )}

            {canWrite && (
              <div className="mt-5 rounded-2xl bg-[#f6faf7] p-4">
                <p className="text-xs font-semibold uppercase tracking-wide dash-muted">
                  Record a diagnosis
                </p>
                <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
                  <label className="text-[11px] dash-muted">
                    Date
                    <input
                      type="date"
                      value={draft.check_date}
                      onChange={(e) => setDraft({ ...draft, check_date: e.target.value })}
                      className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
                    />
                  </label>
                  <label className="text-[11px] dash-muted">
                    Result
                    <select
                      value={draft.result}
                      onChange={(e) => setDraft({ ...draft, result: e.target.value as CheckResult })}
                      className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
                    >
                      {RESULTS.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="text-[11px] dash-muted">
                    Method
                    <select
                      value={draft.method}
                      onChange={(e) => setDraft({ ...draft, method: e.target.value as CheckMethod })}
                      className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
                    >
                      {METHODS.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="flex items-end">
                    <button
                      type="button"
                      disabled={saving}
                      onClick={() => void addCheck()}
                      className="h-9 w-full rounded-xl bg-[var(--primary)] text-xs font-semibold text-[var(--primary-foreground)] transition hover:bg-[#163832] disabled:opacity-40"
                    >
                      {saving ? "Saving…" : "Record"}
                    </button>
                  </div>
                </div>
                <p className="mt-3 text-[11px] dash-muted">
                  "Lost" records a pregnancy confirmed earlier and absent now — that is the event
                  retention is built from. One diagnosis per transfer per day; re-examining the same
                  day is a correction, so edit the existing entry instead.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
