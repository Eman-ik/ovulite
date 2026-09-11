import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CalendarClock, Info, Plus, RefreshCw } from "lucide-react";
import api, { fetchAllPages } from "@/lib/api";
import { getPermissions } from "@/lib/roleRoutes";
import { useAuth } from "@/contexts/AuthContext";
import ScheduleTimeline, { STATE_STYLE, relativeDay } from "@/components/vet/ScheduleTimeline";
import type {
  BoardCount,
  EnrollmentSchedule,
  ScheduledStep,
  VetBoardResponse,
} from "@/lib/types";

type Option = { id: number; label: string };

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function errorText(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return err instanceof Error ? err.message : "Request failed";
}

/** Counts read as a row of tiles; the basis is on hover so the number is checkable. */
function BoardTile({ count }: { count: BoardCount }) {
  const emphasis = count.count > 0 && /overdue/i.test(count.label);
  return (
    <div className="dash-tile p-3.5" title={count.basis}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-medium uppercase leading-tight tracking-wide dash-muted">
          {count.label}
        </p>
        {count.is_estimated && (
          <span className="shrink-0 rounded-full bg-[rgba(234,186,107,0.22)] px-1.5 py-0.5 text-[9px] font-semibold text-[#a1741c]">
            est.
          </span>
        )}
      </div>
      <p
        className="mt-2 text-[26px] font-semibold leading-none"
        style={{ color: emphasis ? "#b8433d" : "#16181a" }}
      >
        {count.count}
      </p>
    </div>
  );
}

export default function SynchronizationPage() {
  const { user } = useAuth();
  const canWrite = getPermissions(user?.role).canEnterETData;

  const [board, setBoard] = useState<VetBoardResponse | null>(null);
  const [schedules, setSchedules] = useState<EnrollmentSchedule[]>([]);
  const [recipients, setRecipients] = useState<Option[]>([]);
  const [protocols, setProtocols] = useState<Option[]>([]);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [busyStep, setBusyStep] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ recipient_id: "", protocol_id: "", start_date: todayISO() });

  const load = useCallback(async () => {
    setError(null);
    try {
      const [b, s] = await Promise.all([
        api.get<VetBoardResponse>("/vet/board"),
        api.get<EnrollmentSchedule[]>("/vet/schedule", {
          params: overdueOnly ? { overdue_only: true } : {},
        }),
      ]);
      setBoard(b.data);
      setSchedules(s.data);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }, [overdueOnly]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    // Reference data for the enrollment form. Failures here are not fatal —
    // the board is still usable without the ability to enroll.
    fetchAllPages<{ recipient_id: number; tag_id: string; farm_location: string | null }>(
      "/recipients/"
    )
      .then((rows) =>
        setRecipients(
          rows.map((x) => ({
            id: x.recipient_id,
            label: x.farm_location ? `${x.tag_id} · ${x.farm_location}` : x.tag_id,
          }))
        )
      )
      .catch(() => setRecipients([]));
    fetchAllPages<{ protocol_id: number; name: string }>("/protocols/")
      .then((rows) => setProtocols(rows.map((p) => ({ id: p.protocol_id, label: p.name }))))
      .catch(() => setProtocols([]));
  }, []);

  const logTreatment = async (enrollmentId: number, step: ScheduledStep) => {
    setBusyStep(step.step_id);
    setError(null);
    try {
      // Records the treatment on the day it was due, which is the common case.
      // A different date is corrected on the enrollment's own record.
      const { data } = await api.post<EnrollmentSchedule>(
        `/vet/enrollments/${enrollmentId}/treatments`,
        { step_id: step.step_id, step_date: step.due_date }
      );
      setSchedules((prev) => prev.map((s) => (s.enrollment_id === enrollmentId ? data : s)));
      void api.get<VetBoardResponse>("/vet/board").then((b) => setBoard(b.data));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusyStep(null);
    }
  };

  const createEnrollment = async () => {
    setError(null);
    try {
      await api.post("/vet/enrollments", {
        recipient_id: Number(form.recipient_id),
        protocol_id: Number(form.protocol_id),
        start_date: form.start_date,
      });
      setShowNew(false);
      setForm({ recipient_id: "", protocol_id: "", start_date: todayISO() });
      await load();
    } catch (err) {
      setError(errorText(err));
    }
  };

  const unschedulable = useMemo(
    () => schedules.filter((s) => !s.has_schedule).length,
    [schedules]
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold dash-heading">Synchronization</h1>
          <p className="mt-1 text-sm dash-muted">
            Recipients on protocol, their treatment schedule, and what is due. Dates are derived
            from each protocol's step template and the enrollment start date.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void load()}
            className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 text-xs font-medium transition hover:bg-black/[0.04]"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
          {canWrite && (
            <button
              type="button"
              onClick={() => setShowNew((v) => !v)}
              className="inline-flex h-9 items-center gap-1.5 rounded-xl bg-[var(--primary)] px-3.5 text-xs font-semibold text-[var(--primary-foreground)] transition hover:bg-[#25292d]"
            >
              <Plus className="h-3.5 w-3.5" />
              Enroll recipient
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-[rgba(210,86,79,0.28)] bg-[rgba(231,154,154,0.16)] p-4 text-sm text-[#b8433d]">
          {error}
        </div>
      )}

      {showNew && canWrite && (
        <div className="dash-card">
          <h2 className="text-base font-semibold dash-heading">Enroll a recipient</h2>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-4">
            <label className="text-xs dash-muted">
              Recipient
              <select
                value={form.recipient_id}
                onChange={(e) => setForm({ ...form, recipient_id: e.target.value })}
                className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
              >
                <option value="">Select…</option>
                {recipients.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs dash-muted">
              Protocol
              <select
                value={form.protocol_id}
                onChange={(e) => setForm({ ...form, protocol_id: e.target.value })}
                className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
              >
                <option value="">Select…</option>
                {protocols.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs dash-muted">
              Start date
              <input
                type="date"
                value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
              />
            </label>
            <div className="flex items-end">
              <button
                type="button"
                disabled={!form.recipient_id || !form.protocol_id || !form.start_date}
                onClick={() => void createEnrollment()}
                className="h-9 w-full rounded-xl bg-[var(--primary)] text-xs font-semibold text-[var(--primary-foreground)] transition hover:bg-[#25292d] disabled:opacity-40"
              >
                Enroll
              </button>
            </div>
          </div>
          <p className="mt-3 text-[11px] dash-muted">
            Day 1 of the protocol is the start date. Treatment dates come from the protocol's step
            template — define one under Protocol Schedules if the protocol has none.
          </p>
        </div>
      )}

      {/* ── Board counts ── */}
      <div className="dash-card">
        <div className="flex items-center gap-2">
          <CalendarClock className="h-4 w-4 dash-muted" />
          <h2 className="text-base font-semibold dash-heading">Today</h2>
          {board && <span className="text-xs dash-muted">as of {board.as_of}</span>}
        </div>
        {!board ? (
          <p className="mt-4 text-sm dash-muted">Loading…</p>
        ) : (
          <>
            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              {board.counts.map((c) => (
                <BoardTile key={c.key} count={c} />
              ))}
            </div>
            {board.protocols_without_steps.length > 0 && (
              <div className="mt-4 flex items-start gap-2.5 rounded-2xl border border-[rgba(224,171,53,0.32)] bg-[rgba(234,186,107,0.14)] px-4 py-3 text-sm">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[#a1741c]" />
                <div className="text-[#7a5a14]">
                  <p className="font-semibold text-[#a1741c]">No schedule defined</p>
                  <p className="mt-1 leading-relaxed">
                    {board.protocols_without_steps.join(", ")} — Ovulite does not guess treatment
                    days, so nothing can be scheduled for recipients on{" "}
                    {board.protocols_without_steps.length === 1 ? "this protocol" : "these protocols"}{" "}
                    until the steps are entered under Protocol Schedules.
                  </p>
                </div>
              </div>
            )}
            <div className="mt-4 flex items-start gap-2 rounded-xl bg-[#faf9f6] px-3 py-2.5 text-[11px] leading-relaxed dash-muted">
              <Info className="mt-px h-3.5 w-3.5 shrink-0" />
              <span>
                {board.note} Hover any tile to see exactly what it counted. "Overdue" means a
                treatment day has passed with nothing recorded — it may simply not be typed in yet.
              </span>
            </div>
          </>
        )}
      </div>

      {/* ── Schedule list ── */}
      <div className="dash-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold dash-heading">
            Active enrollments{" "}
            <span className="ml-1 text-sm font-normal dash-muted">({schedules.length})</span>
          </h2>
          <label className="flex items-center gap-2 text-xs dash-muted">
            <input
              type="checkbox"
              checked={overdueOnly}
              onChange={(e) => setOverdueOnly(e.target.checked)}
              className="h-3.5 w-3.5 accent-[#b8433d]"
            />
            Overdue only
          </label>
        </div>

        {loading ? (
          <p className="mt-4 text-sm dash-muted">Loading…</p>
        ) : schedules.length === 0 ? (
          <p className="mt-4 text-sm dash-muted">
            {overdueOnly
              ? "No enrollment has an overdue treatment."
              : "No active enrollments. Enroll a recipient to start a synchronization schedule."}
          </p>
        ) : (
          <div className="mt-3">
            {schedules.map((s) => {
              const open = expanded === s.enrollment_id;
              const stageTone = s.overdue_count
                ? STATE_STYLE.Overdue
                : s.next_step?.days_from_today === 0
                ? STATE_STYLE["Due today"]
                : STATE_STYLE.Upcoming;
              return (
                <div key={s.enrollment_id} className="border-b border-[var(--border)] last:border-0">
                  <button
                    type="button"
                    onClick={() => setExpanded(open ? null : s.enrollment_id)}
                    className="grid w-full grid-cols-[7rem_1fr_8rem_6rem] items-center gap-3 py-3 text-left transition hover:bg-black/[0.02]"
                  >
                    <span className="text-sm font-medium dash-heading">
                      {s.recipient_tag ?? `#${s.recipient_id}`}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm dash-heading">
                        {s.protocol_name ?? "—"}
                      </span>
                      <span className={`text-xs ${stageTone.text}`}>{s.current_stage}</span>
                    </span>
                    <span className="text-xs dash-muted">
                      {s.has_schedule ? (
                        <>
                          {s.completed_count}/{s.total_steps} done
                          {s.transfer_due_date && (
                            <span className="mt-0.5 block">ET {s.transfer_due_date}</span>
                          )}
                        </>
                      ) : (
                        <span className="text-[#a1741c]">no template</span>
                      )}
                    </span>
                    <span className="text-right">
                      {s.next_step ? (
                        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${stageTone.chip}`}>
                          {relativeDay(s.next_step.days_from_today)}
                        </span>
                      ) : (
                        <span className="text-[11px] dash-muted">—</span>
                      )}
                    </span>
                  </button>

                  {open && (
                    <div className="pb-4">
                      <p className="mb-3 text-xs dash-muted">
                        Started {s.start_date}
                        {s.transfer_id && ` · linked to transfer #${s.transfer_id}`}
                      </p>
                      <ScheduleTimeline
                        steps={s.steps}
                        busyStepId={busyStep}
                        onLog={canWrite ? (step) => void logTreatment(s.enrollment_id, step) : undefined}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {unschedulable > 0 && (
          <p className="mt-3 text-[11px] text-[#a1741c]">
            {unschedulable} enrollment{unschedulable === 1 ? "" : "s"} shown with no step template —
            their schedule cannot be derived.
          </p>
        )}
      </div>
    </div>
  );
}
