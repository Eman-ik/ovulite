import { useCallback, useEffect, useState } from "react";
import { Info, ListOrdered, Plus, Trash2 } from "lucide-react";
import api, { fetchAllPages } from "@/lib/api";
import { getPermissions } from "@/lib/roleRoutes";
import { useAuth } from "@/contexts/AuthContext";
import type { ProtocolStep } from "@/lib/types";

type Protocol = { protocol_id: number; name: string; description: string | null };

const BLANK = {
  day_number: "1",
  step_name: "",
  drug_name: "",
  dosage: "",
  route: "",
  is_transfer_day: false,
};

function errorText(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return err instanceof Error ? err.message : "Request failed";
}

export default function ProtocolSchedulesPage() {
  const { user } = useAuth();
  const canWrite = getPermissions(user?.role).canEnterETData;

  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [steps, setSteps] = useState<ProtocolStep[]>([]);
  const [draft, setDraft] = useState({ ...BLANK });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // /protocols/ is paginated and caps page_size at 100.
    fetchAllPages<Protocol>("/protocols/")
      .then((list) => {
        setProtocols(list);
        if (list.length && selected === null) setSelected(list[0].protocol_id);
      })
      .catch((err) => setError(errorText(err)));
    // Intentionally runs once: the protocol list is reference data.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSteps = useCallback(async (protocolId: number) => {
    try {
      const { data } = await api.get<ProtocolStep[]>(`/vet/protocols/${protocolId}/steps`);
      setSteps(data);
    } catch (err) {
      setError(errorText(err));
    }
  }, []);

  useEffect(() => {
    if (selected !== null) void loadSteps(selected);
  }, [selected, loadSteps]);

  const addStep = async () => {
    if (selected === null) return;
    setSaving(true);
    setError(null);
    try {
      // The form speaks the vet's convention ("Day 1"); storage is zero-based,
      // so the conversion happens here and nowhere else.
      await api.post(`/vet/protocols/${selected}/steps`, {
        day_offset: Number(draft.day_number) - 1,
        step_name: draft.step_name,
        drug_name: draft.drug_name || null,
        dosage: draft.dosage || null,
        route: draft.route || null,
        is_transfer_day: draft.is_transfer_day,
      });
      setDraft({ ...BLANK });
      await loadSteps(selected);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  };

  const removeStep = async (stepId: number) => {
    setError(null);
    try {
      await api.delete(`/vet/protocol-steps/${stepId}`);
      if (selected !== null) await loadSteps(selected);
    } catch (err) {
      setError(errorText(err));
    }
  };

  const active = protocols.find((p) => p.protocol_id === selected);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold dash-heading">Protocol Schedules</h1>
        <p className="mt-1 text-sm dash-muted">
          The treatment days for each synchronization protocol. Enrollment schedules are derived
          from these, so a protocol with no steps cannot be scheduled.
        </p>
      </div>

      {error && (
        <div className="rounded-2xl border border-[rgba(210,86,79,0.28)] bg-[rgba(231,154,154,0.16)] p-4 text-sm text-[#b8433d]">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[16rem_1fr]">
        <div className="dash-card !p-3">
          <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-wide dash-muted">
            Protocols
          </p>
          {protocols.length === 0 ? (
            <p className="px-2 text-sm dash-muted">No protocols defined.</p>
          ) : (
            protocols.map((p) => (
              <button
                key={p.protocol_id}
                type="button"
                onClick={() => setSelected(p.protocol_id)}
                className={`mb-0.5 block w-full rounded-xl px-3 py-2 text-left text-sm transition ${
                  selected === p.protocol_id
                    ? "bg-white font-semibold shadow-sm dash-heading"
                    : "dash-muted hover:bg-black/[0.04]"
                }`}
              >
                {p.name}
              </button>
            ))
          )}
        </div>

        <div className="dash-card">
          <div className="flex items-center gap-2">
            <ListOrdered className="h-4 w-4 dash-muted" />
            <h2 className="text-base font-semibold dash-heading">{active?.name ?? "Select a protocol"}</h2>
          </div>

          {selected !== null && (
            <>
              {steps.length === 0 ? (
                <div className="mt-4 rounded-2xl border border-[rgba(224,171,53,0.32)] bg-[rgba(234,186,107,0.14)] px-4 py-3 text-sm text-[#7a5a14]">
                  <p className="font-semibold text-[#a1741c]">No schedule defined</p>
                  <p className="mt-1 leading-relaxed">
                    This protocol's name records which drugs are used but not on which days, and
                    Ovulite does not guess treatment days. Add the steps below to make enrollments
                    on it schedulable.
                  </p>
                </div>
              ) : (
                <div className="custom-scrollbar mt-4 overflow-x-auto">
                  <table className="w-full min-w-[620px] text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide dash-muted">
                        <th className="pb-2 pr-4 font-medium">Day</th>
                        <th className="pb-2 pr-4 font-medium">Treatment</th>
                        <th className="pb-2 pr-4 font-medium">Drug</th>
                        <th className="pb-2 pr-4 font-medium">Dose</th>
                        <th className="pb-2 pr-4 font-medium">Route</th>
                        <th className="pb-2 font-medium" />
                      </tr>
                    </thead>
                    <tbody>
                      {steps.map((s) => (
                        <tr key={s.step_id} className="border-b border-[var(--border)] last:border-0">
                          <td className="py-2.5 pr-4 whitespace-nowrap">
                            <span className="font-semibold dash-heading">Day {s.day_offset + 1}</span>
                          </td>
                          <td className="py-2.5 pr-4">
                            <span className="dash-heading">{s.step_name}</span>
                            {s.is_transfer_day && (
                              <span className="ml-2 rounded-full bg-[rgba(195,166,224,0.24)] px-1.5 py-0.5 text-[9px] font-semibold text-[#8663a8]">
                                transfer day
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 pr-4 dash-muted">{s.drug_name ?? "—"}</td>
                          <td className="py-2.5 pr-4 dash-muted">{s.dosage ?? "—"}</td>
                          <td className="py-2.5 pr-4 dash-muted">{s.route ?? "—"}</td>
                          <td className="py-2.5 text-right">
                            {canWrite && (
                              <button
                                type="button"
                                onClick={() => void removeStep(s.step_id)}
                                title="Remove step"
                                className="rounded-lg p-1.5 dash-muted transition hover:bg-[rgba(231,154,154,0.2)] hover:text-[#b8433d]"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {canWrite && (
                <div className="mt-5 rounded-2xl bg-[#faf9f6] p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide dash-muted">Add a step</p>
                  <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-6">
                    <label className="text-[11px] dash-muted">
                      Day
                      <input
                        type="number"
                        min={1}
                        value={draft.day_number}
                        onChange={(e) => setDraft({ ...draft, day_number: e.target.value })}
                        className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
                      />
                    </label>
                    <label className="col-span-2 text-[11px] dash-muted">
                      Treatment
                      <input
                        value={draft.step_name}
                        onChange={(e) => setDraft({ ...draft, step_name: e.target.value })}
                        placeholder="e.g. CIDR out + PGF2a"
                        className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
                      />
                    </label>
                    <label className="text-[11px] dash-muted">
                      Drug
                      <input
                        value={draft.drug_name}
                        onChange={(e) => setDraft({ ...draft, drug_name: e.target.value })}
                        className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
                      />
                    </label>
                    <label className="text-[11px] dash-muted">
                      Dose
                      <input
                        value={draft.dosage}
                        onChange={(e) => setDraft({ ...draft, dosage: e.target.value })}
                        className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
                      />
                    </label>
                    <label className="text-[11px] dash-muted">
                      Route
                      <input
                        value={draft.route}
                        onChange={(e) => setDraft({ ...draft, route: e.target.value })}
                        placeholder="IM"
                        className="mt-1 h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-2.5 text-sm text-[var(--foreground)]"
                      />
                    </label>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                    <label className="flex items-center gap-2 text-xs dash-muted">
                      <input
                        type="checkbox"
                        checked={draft.is_transfer_day}
                        onChange={(e) => setDraft({ ...draft, is_transfer_day: e.target.checked })}
                        className="h-3.5 w-3.5 accent-[#8663a8]"
                      />
                      This is the transfer day
                    </label>
                    <button
                      type="button"
                      disabled={!draft.step_name || saving}
                      onClick={() => void addStep()}
                      className="inline-flex h-9 items-center gap-1.5 rounded-xl bg-[var(--primary)] px-3.5 text-xs font-semibold text-[var(--primary-foreground)] transition hover:bg-[#25292d] disabled:opacity-40"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      {saving ? "Adding…" : "Add step"}
                    </button>
                  </div>
                </div>
              )}

              <div className="mt-4 flex items-start gap-2 rounded-xl bg-[#faf9f6] px-3 py-2.5 text-[11px] leading-relaxed dash-muted">
                <Info className="mt-px h-3.5 w-3.5 shrink-0" />
                <span>
                  Day 1 is the enrollment start date, so a recipient enrolled on the 1st has its Day
                  7 treatment due on the 7th. Two treatments may share a day. A step cannot be
                  removed once treatments have been logged against it — that would orphan the record
                  of something actually administered.
                </span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
