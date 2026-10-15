import { useCallback, useEffect, useState } from "react";
import { Boxes, FlaskConical, Info, Microscope, Plus } from "lucide-react";
import api from "@/lib/api";
import { getPermissions } from "@/lib/roleRoutes";
import { useAuth } from "@/contexts/AuthContext";
import {
  EMBRYO_STATUSES,
  type EmbryoStatus,
  type EmbryoTimeline,
  type InventoryResponse,
  type LabBoardResponse,
  type LabCount,
} from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  "In Culture": "bg-[rgba(106,165,184,0.22)] text-[#3f7c91]",
  Transferable: "bg-[rgba(148, 169, 190,0.22)] text-[#3F4758]",
  Frozen: "bg-[rgba(79,143,125,0.22)] text-[#2f6b5c]",
  Assigned: "bg-[rgba(141,151,196,0.24)] text-[#5f6ba0]",
  Transferred: "bg-black/[0.05] dash-muted",
  Discarded: "bg-[rgba(185,142,168,0.24)] text-[#9d3730]",
};

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function errorText(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return err instanceof Error ? err.message : "Request failed";
}

function BoardTile({ count }: { count: LabCount }) {
  return (
    <div className="dash-tile p-3.5" title={count.basis}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-medium uppercase leading-tight tracking-wide dash-muted">
          {count.label}
        </p>
        {count.is_estimated && (
          <span className="shrink-0 rounded-full bg-[rgba(208,164,94,0.22)] px-1.5 py-0.5 text-[9px] font-semibold text-[#7a5a12]">
            est.
          </span>
        )}
      </div>
      <p className="mt-2 text-[26px] font-semibold leading-none dash-heading">{count.count}</p>
    </div>
  );
}

export default function LaboratoryPage() {
  const { user } = useAuth();
  const canWrite = getPermissions(user?.role).canEnterLabData;

  const [board, setBoard] = useState<LabBoardResponse | null>(null);
  const [inventory, setInventory] = useState<InventoryResponse | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const [openEmbryo, setOpenEmbryo] = useState<number | null>(null);
  const [timeline, setTimeline] = useState<EmbryoTimeline | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [obs, setObs] = useState({ day_number: "7", observation_date: todayISO(), stage: "7", grade: "1" });

  const loadInventory = useCallback(async () => {
    try {
      const { data } = await api.get<InventoryResponse>("/lab/inventory", {
        params: { page, page_size: 25, ...(statusFilter ? { status: statusFilter } : {}) },
      });
      setInventory(data);
    } catch (err) {
      setError(errorText(err));
    }
  }, [page, statusFilter]);

  useEffect(() => {
    api
      .get<LabBoardResponse>("/lab/board")
      .then((r) => setBoard(r.data))
      .catch((err) => setError(errorText(err)));
  }, []);

  useEffect(() => {
    void loadInventory();
  }, [loadInventory]);

  const openTimeline = async (embryoId: number) => {
    if (openEmbryo === embryoId) {
      setOpenEmbryo(null);
      setTimeline(null);
      return;
    }
    setOpenEmbryo(embryoId);
    setTimeline(null);
    try {
      const { data } = await api.get<EmbryoTimeline>(`/lab/embryos/${embryoId}/timeline`);
      setTimeline(data);
    } catch (err) {
      setError(errorText(err));
    }
  };

  const addObservation = async () => {
    if (!openEmbryo) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/lab/embryos/${openEmbryo}/observations`, {
        observation_date: obs.observation_date,
        day_number: Number(obs.day_number),
        stage: obs.stage ? Number(obs.stage) : null,
        grade: obs.grade ? Number(obs.grade) : null,
      });
      const { data } = await api.get<EmbryoTimeline>(`/lab/embryos/${openEmbryo}/timeline`);
      setTimeline(data);
      void loadInventory();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const changeStatus = async (embryoId: number, next: EmbryoStatus) => {
    setError(null);
    try {
      const reason =
        next === "Discarded"
          ? window.prompt("Reason for discarding this embryo (required):")?.trim()
          : undefined;
      if (next === "Discarded" && !reason) return;
      await api.patch(`/lab/embryos/${embryoId}/status`, {
        status: next,
        ...(reason ? { discarded_reason: reason } : {}),
      });
      await loadInventory();
      const b = await api.get<LabBoardResponse>("/lab/board");
      setBoard(b.data);
    } catch (err) {
      setError(errorText(err));
    }
  };

  const totalPages = inventory ? Math.max(1, Math.ceil(inventory.total / inventory.page_size)) : 1;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold dash-heading">Laboratory</h1>
        <p className="mt-1 text-sm dash-muted">
          Today's work, the production workflow, and the embryo bank. Status is where an embryo is
          in the lab, as distinct from how it was graded.
        </p>
      </div>

      {error && (
        <div className="rounded-2xl border border-[rgba(179,69,63,0.28)] bg-[rgba(185,142,168,0.16)] p-4 text-sm text-[#9d3730]">
          {error}
        </div>
      )}

      {/* ── Today ── */}
      <div className="dash-card">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-4 w-4 dash-muted" />
          <h2 className="text-base font-semibold dash-heading">Today's Laboratory</h2>
          {board && <span className="text-xs dash-muted">as of {board.as_of}</span>}
        </div>
        {!board ? (
          <p className="mt-4 text-sm dash-muted">Loading…</p>
        ) : (
          <>
            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
              {board.counts.map((c) => (
                <BoardTile key={c.key} count={c} />
              ))}
            </div>

            <h3 className="mt-6 text-sm font-semibold dash-heading">Production workflow</h3>
            <div className="custom-scrollbar mt-3 overflow-x-auto">
              <div className="flex min-w-max items-stretch gap-0">
                {board.workflow.map((w, i) => {
                  const unavailable = w.count === null;
                  return (
                    <div key={w.label} className="flex items-stretch">
                      <div
                        className={`flex w-[150px] flex-col justify-between rounded-2xl p-3 ${
                          unavailable ? "bg-[#EAF1F1]" : "bg-[#f6faf7]"
                        }`}
                        title={w.unavailable_reason ?? undefined}
                      >
                        <p className="text-[11px] font-medium uppercase leading-tight tracking-wide dash-muted">
                          {w.label}
                        </p>
                        {unavailable ? (
                          <>
                            <p className="mt-2 text-lg font-semibold text-[#7a5a12]">n/a</p>
                            <p className="mt-0.5 text-[10px] leading-tight text-[#7a5a12]">
                              {w.unavailable_reason}
                            </p>
                          </>
                        ) : (
                          <p className="mt-2 text-2xl font-semibold dash-heading">
                            {w.count?.toLocaleString()}
                          </p>
                        )}
                      </div>
                      {i < board.workflow.length - 1 && (
                        <div className="flex items-center px-1.5">
                          <div className="h-0.5 w-4 rounded bg-[#cfe0d5]" />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="mt-4 flex items-start gap-2 rounded-xl bg-[#f6faf7] px-3 py-2.5 text-[11px] leading-relaxed dash-muted">
              <Info className="mt-px h-3.5 w-3.5 shrink-0" />
              <span>{board.note} Hover a tile to see exactly what it counted.</span>
            </div>
          </>
        )}
      </div>

      {/* ── Embryo inventory ── */}
      <div className="dash-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Boxes className="h-4 w-4 dash-muted" />
            <h2 className="text-base font-semibold dash-heading">
              Embryo Bank{" "}
              <span className="ml-1 text-sm font-normal dash-muted">
                ({inventory?.total ?? 0})
              </span>
            </h2>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="h-9 rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
          >
            <option value="">All statuses</option>
            {EMBRYO_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {inventory && inventory.summary.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {inventory.summary.map((s) => (
              <span
                key={s.status ?? "none"}
                className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                  STATUS_STYLE[s.status ?? ""] ?? "bg-black/[0.05] dash-muted"
                }`}
              >
                {s.status ?? "Not set"} · {s.count}
              </span>
            ))}
          </div>
        )}

        {!inventory ? (
          <p className="mt-4 text-sm dash-muted">Loading…</p>
        ) : inventory.rows.length === 0 ? (
          <p className="mt-4 text-sm dash-muted">No embryos match this filter.</p>
        ) : (
          <div className="custom-scrollbar mt-4 overflow-x-auto">
            <table className="w-full min-w-[880px] text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide dash-muted">
                  <th className="pb-2 pr-3 font-medium">Embryo</th>
                  <th className="pb-2 pr-3 font-medium">Donor × Sire</th>
                  <th className="pb-2 pr-3 font-medium">OPU</th>
                  <th className="pb-2 pr-3 font-medium">Stage / Grade</th>
                  <th className="pb-2 pr-3 font-medium">Storage</th>
                  <th className="pb-2 pr-3 font-medium">Status</th>
                  <th className="pb-2 font-medium">Culture</th>
                </tr>
              </thead>
              <tbody>
                {inventory.rows.map((r) => (
                  <>
                    <tr key={r.embryo_id} className="border-b border-[var(--border)]">
                      <td className="py-2.5 pr-3 font-medium dash-heading">#{r.embryo_id}</td>
                      <td className="py-2.5 pr-3 dash-muted">
                        {r.donor_tag ?? "—"}
                        {r.sire_name && <span className="dash-muted"> × {r.sire_name}</span>}
                      </td>
                      <td className="py-2.5 pr-3 dash-muted">{r.opu_date ?? "—"}</td>
                      <td className="py-2.5 pr-3 dash-muted">
                        {r.stage ?? "—"} / {r.grade ?? "—"}
                      </td>
                      <td className="py-2.5 pr-3 dash-muted">
                        {r.fresh_or_frozen ?? "—"}
                        {r.cane_number && <span className="block text-xs">{r.cane_number}</span>}
                      </td>
                      <td className="py-2.5 pr-3">
                        {canWrite && !r.transfer_id ? (
                          <select
                            value={r.status ?? ""}
                            onChange={(e) => void changeStatus(r.embryo_id, e.target.value as EmbryoStatus)}
                            className={`rounded-full px-2 py-1 text-xs font-medium ${
                              STATUS_STYLE[r.status ?? ""] ?? "bg-black/[0.05] dash-muted"
                            }`}
                          >
                            {EMBRYO_STATUSES.map((s) => (
                              <option key={s} value={s}>
                                {s}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span
                            className={`rounded-full px-2 py-1 text-xs font-medium ${
                              STATUS_STYLE[r.status ?? ""] ?? "bg-black/[0.05] dash-muted"
                            }`}
                            title={
                              r.transfer_id
                                ? `Locked: recorded on transfer #${r.transfer_id}`
                                : undefined
                            }
                          >
                            {r.status ?? "Not set"}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5">
                        <button
                          type="button"
                          onClick={() => void openTimeline(r.embryo_id)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--card)] px-2 py-1 text-xs font-medium transition hover:bg-black/[0.04]"
                        >
                          <Microscope className="h-3 w-3" />
                          {r.observation_count > 0 ? `${r.observation_count} looks` : "Timeline"}
                        </button>
                      </td>
                    </tr>
                    {openEmbryo === r.embryo_id && (
                      <tr key={`${r.embryo_id}-timeline`}>
                        <td colSpan={7} className="bg-[#f6faf7] px-3 py-4">
                          {!timeline ? (
                            <p className="text-sm dash-muted">Loading timeline…</p>
                          ) : (
                            <>
                              {timeline.observations.length === 0 ? (
                                <p className="text-sm dash-muted">
                                  No culture observations recorded. Historical embryos have none —
                                  the timeline was not captured before this existed, and an empty
                                  timeline is not an arrest.
                                </p>
                              ) : (
                                <div className="custom-scrollbar overflow-x-auto">
                                  <div className="flex min-w-max items-start gap-0">
                                    {timeline.observations.map((o, i) => (
                                      <div key={o.observation_id} className="flex items-start">
                                        <div className="flex w-[136px] flex-col items-center px-1 text-center">
                                          <div
                                            className="flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold text-white"
                                            style={{
                                              background: o.is_arrested ? "#9d3730" : "#6aa5b8",
                                            }}
                                          >
                                            D{o.day_number}
                                          </div>
                                          <p className="mt-1.5 text-[11px] font-medium leading-tight dash-heading">
                                            {o.stage_label ?? `Stage ${o.stage ?? "—"}`}
                                          </p>
                                          <p className="mt-0.5 text-[10px] dash-muted">
                                            {o.observation_date}
                                          </p>
                                          {o.cell_count !== null && (
                                            <p className="text-[10px] dash-muted">
                                              {o.cell_count} cells
                                            </p>
                                          )}
                                        </div>
                                        {i < timeline.observations.length - 1 && (
                                          <div className="mt-3 h-0.5 w-5 shrink-0 rounded bg-[#c3dbd0]" />
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {canWrite && (
                                <div className="mt-4 flex flex-wrap items-end gap-2">
                                  <label className="text-[11px] dash-muted">
                                    Day
                                    <input
                                      type="number"
                                      min={0}
                                      max={12}
                                      value={obs.day_number}
                                      onChange={(e) => setObs({ ...obs, day_number: e.target.value })}
                                      className="mt-1 h-8 w-16 rounded-lg border border-[var(--border)] bg-[var(--input)] px-2 text-sm text-[var(--foreground)]"
                                    />
                                  </label>
                                  <label className="text-[11px] dash-muted">
                                    Date
                                    <input
                                      type="date"
                                      value={obs.observation_date}
                                      onChange={(e) =>
                                        setObs({ ...obs, observation_date: e.target.value })
                                      }
                                      className="mt-1 h-8 rounded-lg border border-[var(--border)] bg-[var(--input)] px-2 text-sm text-[var(--foreground)]"
                                    />
                                  </label>
                                  <label className="text-[11px] dash-muted">
                                    Stage
                                    <input
                                      type="number"
                                      min={1}
                                      max={9}
                                      value={obs.stage}
                                      onChange={(e) => setObs({ ...obs, stage: e.target.value })}
                                      className="mt-1 h-8 w-16 rounded-lg border border-[var(--border)] bg-[var(--input)] px-2 text-sm text-[var(--foreground)]"
                                    />
                                  </label>
                                  <label className="text-[11px] dash-muted">
                                    Grade
                                    <input
                                      type="number"
                                      min={1}
                                      max={4}
                                      value={obs.grade}
                                      onChange={(e) => setObs({ ...obs, grade: e.target.value })}
                                      className="mt-1 h-8 w-16 rounded-lg border border-[var(--border)] bg-[var(--input)] px-2 text-sm text-[var(--foreground)]"
                                    />
                                  </label>
                                  <button
                                    type="button"
                                    disabled={busy}
                                    onClick={() => void addObservation()}
                                    className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-[var(--primary)] px-3 text-xs font-semibold text-[var(--primary-foreground)] transition hover:bg-[#596070] disabled:opacity-40"
                                  >
                                    <Plus className="h-3 w-3" />
                                    {busy ? "Saving…" : "Record look"}
                                  </button>
                                </div>
                              )}
                              <p className="mt-3 text-[11px] leading-relaxed dash-muted">
                                {timeline.note}
                              </p>
                            </>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {inventory && totalPages > 1 && (
          <div className="mt-4 flex items-center justify-between text-xs dash-muted">
            <span>
              Page {inventory.page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-1.5 font-medium transition hover:bg-black/[0.04] disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-1.5 font-medium transition hover:bg-black/[0.04] disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}

        {inventory && (
          <div className="mt-4 flex items-start gap-2 rounded-xl bg-[#f6faf7] px-3 py-2.5 text-[11px] leading-relaxed dash-muted">
            <Info className="mt-px h-3.5 w-3.5 shrink-0" />
            <span>{inventory.note}</span>
          </div>
        )}
      </div>
    </div>
  );
}
