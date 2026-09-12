import { useCallback, useEffect, useState } from "react";
import { Beaker, Info, Plus, Thermometer } from "lucide-react";
import api, { fetchAllPages } from "@/lib/api";
import { getPermissions } from "@/lib/roleRoutes";
import { useAuth } from "@/contexts/AuthContext";
import type { OocyteGradeSummary } from "@/lib/types";

type OpuOption = { opu_id: number; opu_date: string; donor_id: number; donor_tag?: string | null };

const GRADE_COLORS = ["#8EB69B", "#6aa5b8", "#d0a45e", "#b98ea8"] as const;

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function errorText(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return err instanceof Error ? err.message : "Request failed";
}

export default function OocyteProcessingPage() {
  const { user } = useAuth();
  const canWrite = getPermissions(user?.role).canEnterLabData;

  const [sessions, setSessions] = useState<OpuOption[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [summary, setSummary] = useState<OocyteGradeSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [grades, setGrades] = useState({ a: "", b: "", c: "", degen: "" });
  const [ivm, setIvm] = useState({
    ivm_date: todayISO(),
    medium: "",
    medium_lot: "",
    incubation_hours: "22",
    temperature_c: "38.5",
    co2_percent: "5",
    oocytes_in: "",
    mature_oocytes_out: "",
  });

  useEffect(() => {
    fetchAllPages<OpuOption>("/opu-sessions/")
      .then((rows) => {
        const sorted = [...rows].sort((a, b) => (a.opu_date < b.opu_date ? 1 : -1));
        setSessions(sorted);
        if (sorted.length && selected === null) setSelected(sorted[0].opu_id);
      })
      .catch((err) => setError(errorText(err)));
    // Reference data; loaded once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const load = useCallback(async (opuId: number) => {
    try {
      const { data } = await api.get<OocyteGradeSummary>(`/lab/opu-sessions/${opuId}/processing`);
      setSummary(data);
      setGrades({
        a: data.grade_a_oocytes?.toString() ?? "",
        b: data.grade_b_oocytes?.toString() ?? "",
        c: data.grade_c_oocytes?.toString() ?? "",
        degen: data.degenerated_oocytes?.toString() ?? "",
      });
    } catch (err) {
      setError(errorText(err));
    }
  }, []);

  useEffect(() => {
    if (selected !== null) void load(selected);
  }, [selected, load]);

  const saveGrades = async () => {
    if (selected === null || !summary) return;
    setBusy(true);
    setError(null);
    try {
      // A focused PATCH rather than a full PUT on the session: grading happens
      // after recovery and often by a different person, so resending
      // donor_id/opu_date just to change four counts risks clobbering a field
      // someone else edited in between.
      const { data } = await api.patch<OocyteGradeSummary>(
        `/lab/opu-sessions/${selected}/oocyte-grades`,
        {
          grade_a_oocytes: grades.a === "" ? null : Number(grades.a),
          grade_b_oocytes: grades.b === "" ? null : Number(grades.b),
          grade_c_oocytes: grades.c === "" ? null : Number(grades.c),
          degenerated_oocytes: grades.degen === "" ? null : Number(grades.degen),
        }
      );
      setSummary(data);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const addIvm = async () => {
    if (selected === null) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/lab/opu-sessions/${selected}/ivm-batches`, {
        ivm_date: ivm.ivm_date || null,
        medium: ivm.medium || null,
        medium_lot: ivm.medium_lot || null,
        incubation_hours: ivm.incubation_hours === "" ? null : Number(ivm.incubation_hours),
        temperature_c: ivm.temperature_c === "" ? null : Number(ivm.temperature_c),
        co2_percent: ivm.co2_percent === "" ? null : Number(ivm.co2_percent),
        oocytes_in: ivm.oocytes_in === "" ? null : Number(ivm.oocytes_in),
        mature_oocytes_out: ivm.mature_oocytes_out === "" ? null : Number(ivm.mature_oocytes_out),
      });
      await load(selected);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const gradeBars = summary
    ? [
        { label: "Grade A", value: summary.grade_a_oocytes ?? 0 },
        { label: "Grade B", value: summary.grade_b_oocytes ?? 0 },
        { label: "Grade C", value: summary.grade_c_oocytes ?? 0 },
        { label: "Degenerate", value: summary.degenerated_oocytes ?? 0 },
      ]
    : [];
  const gradeMax = Math.max(...gradeBars.map((g) => g.value), 1);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold dash-heading">Oocyte Assessment &amp; IVM</h1>
        <p className="mt-1 text-sm dash-muted">
          Grading and maturation for one recovery session. Oocytes are tallied per grade rather
          than recorded individually, which is how they are counted in the dish.
        </p>
      </div>

      {error && (
        <div className="rounded-2xl border border-[rgba(179,69,63,0.28)] bg-[rgba(185,142,168,0.16)] p-4 text-sm text-[#9d3730]">
          {error}
        </div>
      )}

      <div className="dash-card">
        <label className="text-xs dash-muted">
          OPU session
          <select
            value={selected ?? ""}
            onChange={(e) => setSelected(Number(e.target.value))}
            className="mt-1 block h-9 w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
          >
            {sessions.map((s) => (
              <option key={s.opu_id} value={s.opu_id}>
                #{s.opu_id} · {s.opu_date}
              </option>
            ))}
          </select>
        </label>
      </div>

      {summary && (
        <>
          {/* ── Oocyte grading ── */}
          <div className="dash-card">
            <div className="flex items-center gap-2">
              <Beaker className="h-4 w-4 dash-muted" />
              <h2 className="text-base font-semibold dash-heading">Oocyte Assessment</h2>
            </div>
            <p className="mt-1 text-xs dash-muted">
              Donor {summary.donor_tag ?? "—"} · recovered{" "}
              {summary.oocytes_recovered ?? "not recorded"}
              {summary.ungraded !== null && ` · ${summary.ungraded} ungraded`}
            </p>

            {summary.graded_total > 0 && (
              <div className="mt-4 space-y-2">
                {gradeBars.map((g, i) => (
                  <div key={g.label} className="grid grid-cols-[6rem_1fr_2.5rem] items-center gap-3">
                    <span className="text-xs dash-heading">{g.label}</span>
                    <div className="h-4 rounded bg-black/[0.04]">
                      <div
                        className="h-4 rounded"
                        style={{
                          width: `${(g.value / gradeMax) * 100}%`,
                          background: GRADE_COLORS[i],
                        }}
                      />
                    </div>
                    <span className="text-right text-xs font-semibold dash-heading">{g.value}</span>
                  </div>
                ))}
              </div>
            )}

            {canWrite && (
              <div className="mt-5 rounded-2xl bg-[#f6faf7] p-4">
                <p className="text-xs font-semibold uppercase tracking-wide dash-muted">
                  Record grading
                </p>
                <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-5">
                  {(
                    [
                      ["a", "Grade A"],
                      ["b", "Grade B"],
                      ["c", "Grade C"],
                      ["degen", "Degenerate"],
                    ] as const
                  ).map(([key, label]) => (
                    <label key={key} className="text-[11px] dash-muted">
                      {label}
                      <input
                        type="number"
                        min={0}
                        value={grades[key]}
                        onChange={(e) => setGrades({ ...grades, [key]: e.target.value })}
                        className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
                      />
                    </label>
                  ))}
                  <div className="flex items-end">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void saveGrades()}
                      className="h-9 w-full rounded-xl bg-[var(--primary)] text-xs font-semibold text-[var(--primary-foreground)] transition hover:bg-[#163832] disabled:opacity-40"
                    >
                      {busy ? "Saving…" : "Save"}
                    </button>
                  </div>
                </div>
                <p className="mt-3 text-[11px] dash-muted">
                  A partial tally is fine — grading often happens in a second pass. The total is
                  rejected only if it exceeds the oocytes recovered.
                </p>
              </div>
            )}
          </div>

          {/* ── IVM ── */}
          <div className="dash-card">
            <div className="flex items-center gap-2">
              <Thermometer className="h-4 w-4 dash-muted" />
              <h2 className="text-base font-semibold dash-heading">
                In-Vitro Maturation{" "}
                <span className="ml-1 text-sm font-normal dash-muted">
                  ({summary.ivm_batches.length})
                </span>
              </h2>
            </div>

            {summary.ivm_batches.length === 0 ? (
              <p className="mt-4 text-sm dash-muted">
                No IVM batch recorded for this session.
              </p>
            ) : (
              <div className="custom-scrollbar mt-4 overflow-x-auto">
                <table className="w-full min-w-[760px] text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide dash-muted">
                      <th className="pb-2 pr-3 font-medium">Date</th>
                      <th className="pb-2 pr-3 font-medium">Medium</th>
                      <th className="pb-2 pr-3 font-medium">Hours</th>
                      <th className="pb-2 pr-3 font-medium">Temp / CO₂</th>
                      <th className="pb-2 pr-3 font-medium">In → Mature</th>
                      <th className="pb-2 font-medium">Maturation rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.ivm_batches.map((b) => (
                      <tr key={b.ivm_batch_id} className="border-b border-[var(--border)] last:border-0">
                        <td className="py-2.5 pr-3 dash-heading">{b.ivm_date ?? "—"}</td>
                        <td className="py-2.5 pr-3 dash-muted">
                          {b.medium ?? "—"}
                          {b.medium_lot && <span className="block text-xs">lot {b.medium_lot}</span>}
                        </td>
                        <td className="py-2.5 pr-3 dash-muted">{b.incubation_hours ?? "—"}</td>
                        <td className="py-2.5 pr-3 dash-muted">
                          {b.temperature_c ?? "—"}°C / {b.co2_percent ?? "—"}%
                        </td>
                        <td className="py-2.5 pr-3 dash-muted">
                          {b.oocytes_in ?? "—"} → {b.mature_oocytes_out ?? "—"}
                        </td>
                        <td className="py-2.5">
                          {b.maturation_rate_pct === null ? (
                            <span className="text-xs dash-muted">not computable</span>
                          ) : (
                            <span className="font-semibold dash-heading">
                              {b.maturation_rate_pct}%
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {canWrite && (
              <div className="mt-5 rounded-2xl bg-[#f6faf7] p-4">
                <p className="text-xs font-semibold uppercase tracking-wide dash-muted">
                  Add an IVM batch
                </p>
                <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
                  {(
                    [
                      ["ivm_date", "Date", "date"],
                      ["medium", "Medium", "text"],
                      ["medium_lot", "Lot", "text"],
                      ["incubation_hours", "Hours", "number"],
                      ["temperature_c", "Temp °C", "number"],
                      ["co2_percent", "CO₂ %", "number"],
                      ["oocytes_in", "Oocytes in", "number"],
                      ["mature_oocytes_out", "Mature out", "number"],
                    ] as const
                  ).map(([key, label, type]) => (
                    <label key={key} className="text-[11px] dash-muted">
                      {label}
                      <input
                        type={type}
                        step={type === "number" ? "any" : undefined}
                        value={ivm[key]}
                        onChange={(e) => setIvm({ ...ivm, [key]: e.target.value })}
                        className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
                      />
                    </label>
                  ))}
                </div>
                <div className="mt-3 flex justify-end">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void addIvm()}
                    className="inline-flex h-9 items-center gap-1.5 rounded-xl bg-[var(--primary)] px-3.5 text-xs font-semibold text-[var(--primary-foreground)] transition hover:bg-[#163832] disabled:opacity-40"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    {busy ? "Adding…" : "Add batch"}
                  </button>
                </div>
              </div>
            )}

            <div className="mt-4 flex items-start gap-2 rounded-xl bg-[#f6faf7] px-3 py-2.5 text-[11px] leading-relaxed dash-muted">
              <Info className="mt-px h-3.5 w-3.5 shrink-0" />
              <span>
                Maturation rate is shown only when both counts are present — a rate without its
                denominator is not interpretable. Recording more matured than were put in is
                rejected.
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
