import { useState, useEffect, useCallback, type FormEvent } from "react";
import api, { fetchAllPages } from "@/lib/api";
import SitePicker from "@/components/SitePicker";
import type {
  PaginatedResponse,
  OPUSession,
  IVFBatch,
  IVMBatch,
  Donor,
  Sire,
  Technician,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  FlaskConical,
  TestTube,
  Plus,
  Pencil,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Loader2,
  X,
} from "lucide-react";

const PAGE_SIZE = 25;

function getApiErrorMessage(err: unknown): string {
  const strip = (msg: string) => msg.replace(/^Value error,\s*/i, "");
  if (err && typeof err === "object" && "response" in err) {
    const response = (err as { response?: { data?: { detail?: unknown } } }).response;
    const detail = response?.data?.detail;
    if (typeof detail === "string") return strip(detail);
    if (Array.isArray(detail) && detail[0]?.msg) return strip(String(detail[0].msg));
  }
  return err instanceof Error ? err.message : "Something went wrong";
}

function formatRate(value: number | null): string {
  return value == null ? "—" : `${(value * 100).toFixed(1)}%`;
}

/* ─── Page ──────────────────────────────────────────────── */

export default function OPUIVFPage() {
  const [activeTab, setActiveTab] = useState<"opu" | "ivf">("opu");

  const [donors, setDonors] = useState<Donor[]>([]);
  const [sires, setSires] = useState<Sire[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);

  useEffect(() => {
    Promise.all([
      fetchAllPages<Donor>("/donors/"),
      fetchAllPages<Sire>("/sires/"),
      fetchAllPages<Technician>("/technicians/"),
    ]).then(([donorRows, sireRows, techRows]) => {
      setDonors(donorRows);
      setSires(sireRows);
      setTechnicians(techRows);
    });
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-primary/15 p-2">
          <FlaskConical className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">OPU & IVF Batches</h1>
          <p className="text-sm text-muted-foreground">
            Ovum-pickup sessions and the laboratory IVF batches produced from them
          </p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "opu" | "ivf")}>
        <TabsList>
          <TabsTrigger value="opu">OPU Sessions</TabsTrigger>
          <TabsTrigger value="ivf">IVF Batches</TabsTrigger>
        </TabsList>

        <TabsContent value="opu">
          <OPUSessionsTab donors={donors} technicians={technicians} />
        </TabsContent>

        <TabsContent value="ivf">
          <IVFBatchesTab technicians={technicians} sires={sires} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

/* ─── OPU Sessions tab ──────────────────────────────────── */

function OPUSessionsTab({ donors, technicians }: { donors: Donor[]; technicians: Technician[] }) {
  const [items, setItems] = useState<OPUSession[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [filterDonor, setFilterDonor] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<OPUSession | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    const params: Record<string, string | number> = { page, page_size: PAGE_SIZE };
    if (filterDonor) params.donor_id = filterDonor;
    api
      .get<PaginatedResponse<OPUSession>>("/opu-sessions/", { params })
      .then((res) => {
        setItems(res.data.items);
        setTotal(res.data.total);
        setPages(res.data.pages);
      })
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, filterDonor, refreshNonce]);

  useEffect(() => load(), [load]);

  const handleDelete = async (s: OPUSession) => {
    if (!window.confirm(`Delete OPU session #${s.opu_id} (${s.donor_tag ?? s.donor_id}, ${s.opu_date})?`)) return;
    try {
      await api.delete(`/opu-sessions/${s.opu_id}`);
      setRefreshNonce((n) => n + 1);
    } catch (err) {
      alert(getApiErrorMessage(err));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">{total} total OPU sessions</p>
        <div className="flex flex-wrap gap-2">
          <Select value={filterDonor} onChange={(e) => { setFilterDonor(e.target.value); setPage(1); }}>
            <option value="">All Donors</option>
            {donors.map((d) => (
              <option key={d.donor_id} value={d.donor_id}>{d.tag_id}</option>
            ))}
          </Select>
          <Button onClick={() => { setEditing(null); setModalOpen(true); }}>
            <Plus className="mr-2 h-4 w-4" />
            New OPU Session
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex h-40 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : items.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center text-muted-foreground">
              <p>No OPU sessions found</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">#</TableHead>
                  <TableHead>Donor</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Technician</TableHead>
                  <TableHead>Follicles</TableHead>
                  <TableHead>Recovered</TableHead>
                  <TableHead>Viable</TableHead>
                  <TableHead>Recovery Rate</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((s) => (
                  <TableRow key={s.opu_id}>
                    <TableCell className="font-mono text-xs">{s.opu_id}</TableCell>
                    <TableCell>{s.donor_tag ?? s.donor_id}</TableCell>
                    <TableCell>{s.opu_date}</TableCell>
                    <TableCell>{s.technician_name ?? "—"}</TableCell>
                    <TableCell>{s.total_follicles ?? "—"}</TableCell>
                    <TableCell>{s.oocytes_recovered ?? "—"}</TableCell>
                    <TableCell>{s.viable_oocytes ?? "—"}</TableCell>
                    <TableCell>
                      {s.recovery_rate == null ? (
                        <span className="text-muted-foreground">—</span>
                      ) : (
                        <Badge variant="secondary">{formatRate(s.recovery_rate)}</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="sm" onClick={() => { setEditing(s); setModalOpen(true); }}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(s)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {pages > 1 && (
        <Pagination page={page} pages={pages} total={total} onPageChange={setPage} />
      )}

      {modalOpen && (
        <OPUSessionModal
          donors={donors}
          technicians={technicians}
          editing={editing}
          onClose={() => setModalOpen(false)}
          onSaved={() => { setModalOpen(false); setRefreshNonce((n) => n + 1); }}
        />
      )}
    </div>
  );
}

/* ─── IVF Batches tab ───────────────────────────────────── */

function IVFBatchesTab({ technicians, sires }: { technicians: Technician[]; sires: Sire[] }) {
  const [items, setItems] = useState<IVFBatch[]>([]);
  const [opuSessions, setOpuSessions] = useState<OPUSession[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [filterOpu, setFilterOpu] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<IVFBatch | null>(null);

  useEffect(() => {
    // The IVF form picks an OPU session from the full list, not the first 100.
    fetchAllPages<OPUSession>("/opu-sessions/").then(setOpuSessions);
  }, [refreshNonce]);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    const params: Record<string, string | number> = { page, page_size: PAGE_SIZE };
    if (filterOpu) params.opu_id = filterOpu;
    api
      .get<PaginatedResponse<IVFBatch>>("/ivf-batches/", { params })
      .then((res) => {
        setItems(res.data.items);
        setTotal(res.data.total);
        setPages(res.data.pages);
      })
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, filterOpu, refreshNonce]);

  useEffect(() => load(), [load]);

  const handleDelete = async (b: IVFBatch) => {
    if (!window.confirm(`Delete IVF batch #${b.ivf_batch_id}?`)) return;
    try {
      await api.delete(`/ivf-batches/${b.ivf_batch_id}`);
      setRefreshNonce((n) => n + 1);
    } catch (err) {
      alert(getApiErrorMessage(err));
    }
  };

  const opuLabel = (s: OPUSession) => `${s.donor_tag ?? s.donor_id} · ${s.opu_date}`;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">{total} total IVF batches</p>
        <div className="flex flex-wrap gap-2">
          <Select value={filterOpu} onChange={(e) => { setFilterOpu(e.target.value); setPage(1); }}>
            <option value="">All OPU Sessions</option>
            {opuSessions.map((s) => (
              <option key={s.opu_id} value={s.opu_id}>{opuLabel(s)}</option>
            ))}
          </Select>
          <Button onClick={() => { setEditing(null); setModalOpen(true); }} disabled={opuSessions.length === 0}>
            <Plus className="mr-2 h-4 w-4" />
            New IVF Batch
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex h-40 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : items.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center text-muted-foreground">
              <p>No IVF batches found</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">#</TableHead>
                  <TableHead>OPU Session</TableHead>
                  <TableHead>Sire</TableHead>
                  <TableHead>IVF Date</TableHead>
                  <TableHead>Oocytes Used</TableHead>
                  <TableHead>Cleaved</TableHead>
                  <TableHead>Blastocysts</TableHead>
                  <TableHead>Cleavage Rate</TableHead>
                  <TableHead>Blastocyst Rate</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((b) => (
                  <TableRow key={b.ivf_batch_id}>
                    <TableCell className="font-mono text-xs">{b.ivf_batch_id}</TableCell>
                    <TableCell>
                      {b.opu_donor_tag ?? b.opu_id}
                      {b.opu_date && <span className="ml-1 text-xs text-muted-foreground">({b.opu_date})</span>}
                    </TableCell>
                    <TableCell>{b.sire_name ?? "—"}</TableCell>
                    <TableCell>{b.ivf_date ?? "—"}</TableCell>
                    <TableCell>{b.oocytes_used ?? "—"}</TableCell>
                    <TableCell>{b.cleaved_embryos ?? "—"}</TableCell>
                    <TableCell>{b.blastocysts ?? "—"}</TableCell>
                    <TableCell>
                      {b.cleavage_rate == null ? (
                        <span className="text-muted-foreground">—</span>
                      ) : (
                        <Badge variant="secondary">{formatRate(b.cleavage_rate)}</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {b.blastocyst_rate == null ? (
                        <span className="text-muted-foreground">—</span>
                      ) : (
                        <Badge variant="secondary">{formatRate(b.blastocyst_rate)}</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="sm" onClick={() => { setEditing(b); setModalOpen(true); }}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(b)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {pages > 1 && (
        <Pagination page={page} pages={pages} total={total} onPageChange={setPage} />
      )}

      {modalOpen && (
        <IVFBatchModal
          opuSessions={opuSessions}
          sires={sires}
          technicians={technicians}
          editing={editing}
          onClose={() => setModalOpen(false)}
          onSaved={() => { setModalOpen(false); setRefreshNonce((n) => n + 1); }}
        />
      )}
    </div>
  );
}

/* ─── Shared pagination ─────────────────────────────────── */

function Pagination({
  page, pages, total, onPageChange,
}: { page: number; pages: number; total: number; onPageChange: (p: number) => void }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-sm text-muted-foreground">Page {page} of {pages} ({total} records)</p>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          <ChevronLeft className="h-4 w-4" />
          Previous
        </Button>
        <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>
          Next
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

/* ─── Modal shell ───────────────────────────────────────── */

function ModalShell({
  title, icon: Icon, onClose, children,
}: { title: string; icon: typeof FlaskConical; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-background p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-bold">{title}</h3>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}

/* ─── OPU Session create/edit modal ─────────────────────── */

function OPUSessionModal({
  donors, technicians, editing, onClose, onSaved,
}: {
  donors: Donor[];
  technicians: Technician[];
  editing: OPUSession | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    donor_id: editing?.donor_id?.toString() ?? "",
    opu_date: editing?.opu_date ?? "",
    technician_id: editing?.technician_id?.toString() ?? "",
    farm_location: editing?.farm_location ?? "",
    laboratory_id: editing?.laboratory_id ?? null,
    total_follicles: editing?.total_follicles?.toString() ?? "",
    oocytes_recovered: editing?.oocytes_recovered?.toString() ?? "",
    viable_oocytes: editing?.viable_oocytes?.toString() ?? "",
    notes: editing?.notes ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const set = (field: keyof typeof form) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.donor_id || !form.opu_date) {
      setError("Donor and OPU date are required");
      return;
    }
    setSaving(true);
    const payload: Record<string, unknown> = {
      donor_id: parseInt(form.donor_id),
      opu_date: form.opu_date,
    };
    if (form.technician_id) payload.technician_id = parseInt(form.technician_id);
    if (form.laboratory_id !== null) payload.laboratory_id = form.laboratory_id;
    if (form.total_follicles) payload.total_follicles = parseInt(form.total_follicles);
    if (form.oocytes_recovered) payload.oocytes_recovered = parseInt(form.oocytes_recovered);
    if (form.viable_oocytes) payload.viable_oocytes = parseInt(form.viable_oocytes);
    if (form.notes) payload.notes = form.notes;

    try {
      if (editing) {
        await api.put(`/opu-sessions/${editing.opu_id}`, payload);
      } else {
        await api.post("/opu-sessions/", payload);
      }
      onSaved();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalShell title={editing ? `Edit OPU Session #${editing.opu_id}` : "New OPU Session"} icon={FlaskConical} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="opu-donor">Donor *</Label>
            <Select id="opu-donor" value={form.donor_id} onChange={set("donor_id")} required>
              <option value="">Select...</option>
              {donors.map((d) => <option key={d.donor_id} value={d.donor_id}>{d.tag_id}</option>)}
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="opu-date">OPU Date *</Label>
            <Input id="opu-date" type="date" value={form.opu_date} onChange={set("opu_date")} required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="opu-technician">Technician</Label>
            <Select id="opu-technician" value={form.technician_id} onChange={set("technician_id")}>
              <option value="">Select...</option>
              {technicians.map((t) => <option key={t.technician_id} value={t.technician_id}>{t.name}</option>)}
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="opu-site">Site</Label>
            <SitePicker
              id="opu-site"
              value={form.laboratory_id}
              legacyText={form.farm_location || null}
              onChange={(laboratory_id) => setForm((f) => ({ ...f, laboratory_id }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="opu-follicles">Total Follicles</Label>
            <Input id="opu-follicles" type="number" min="0" value={form.total_follicles} onChange={set("total_follicles")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="opu-recovered">Oocytes Recovered</Label>
            <Input id="opu-recovered" type="number" min="0" value={form.oocytes_recovered} onChange={set("oocytes_recovered")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="opu-viable">Viable Oocytes</Label>
            <Input id="opu-viable" type="number" min="0" value={form.viable_oocytes} onChange={set("viable_oocytes")} />
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="opu-notes">Notes</Label>
          <Textarea id="opu-notes" value={form.notes} onChange={set("notes")} rows={2} />
        </div>

        {error && <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}

        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? "Saving..." : editing ? "Update" : "Create"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

/* ─── IVF Batch create/edit modal ───────────────────────── */

function IVFBatchModal({
  opuSessions, sires, technicians, editing, onClose, onSaved,
}: {
  opuSessions: OPUSession[];
  sires: Sire[];
  technicians: Technician[];
  editing: IVFBatch | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    opu_id: editing?.opu_id?.toString() ?? "",
    ivm_batch_id: editing?.ivm_batch_id?.toString() ?? "",
    sire_id: editing?.sire_id?.toString() ?? "",
    ivf_date: editing?.ivf_date ?? "",
    oocytes_used: editing?.oocytes_used?.toString() ?? "",
    mature_oocytes: editing?.mature_oocytes?.toString() ?? "",
    cleaved_embryos: editing?.cleaved_embryos?.toString() ?? "",
    blastocysts: editing?.blastocysts?.toString() ?? "",
    degenerated_embryos: editing?.degenerated_embryos?.toString() ?? "",
    culture_media: editing?.culture_media ?? "",
    embryologist_id: editing?.embryologist_id?.toString() ?? "",
    notes: editing?.notes ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  // IVM batches for the chosen OPU session. The lab sequence is OPU -> IVM -> IVF,
  // so an IVF batch needs one of these.
  const [ivmOptions, setIvmOptions] = useState<IVMBatch[]>([]);

  useEffect(() => {
    if (!form.opu_id) {
      setIvmOptions([]);
      return;
    }
    let cancelled = false;
    api
      .get<{ ivm_batches: IVMBatch[] }>(`/lab/opu-sessions/${form.opu_id}/processing`)
      .then((r) => {
        if (!cancelled) setIvmOptions(r.data.ivm_batches);
      })
      .catch(() => {
        if (!cancelled) setIvmOptions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [form.opu_id]);

  const set = (field: keyof typeof form) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.opu_id) {
      setError("OPU session is required");
      return;
    }
    if (!editing && !form.ivm_batch_id) {
      setError("Choose the IVM batch this IVF comes from. Record one on Oocytes & IVM first if none is listed.");
      return;
    }
    setSaving(true);
    const payload: Record<string, unknown> = { opu_id: parseInt(form.opu_id) };
    if (form.ivm_batch_id) payload.ivm_batch_id = parseInt(form.ivm_batch_id);
    if (form.sire_id) payload.sire_id = parseInt(form.sire_id);
    if (form.ivf_date) payload.ivf_date = form.ivf_date;
    if (form.oocytes_used) payload.oocytes_used = parseInt(form.oocytes_used);
    if (form.mature_oocytes) payload.mature_oocytes = parseInt(form.mature_oocytes);
    if (form.cleaved_embryos) payload.cleaved_embryos = parseInt(form.cleaved_embryos);
    if (form.blastocysts) payload.blastocysts = parseInt(form.blastocysts);
    if (form.degenerated_embryos) payload.degenerated_embryos = parseInt(form.degenerated_embryos);
    if (form.culture_media) payload.culture_media = form.culture_media;
    if (form.embryologist_id) payload.embryologist_id = parseInt(form.embryologist_id);
    if (form.notes) payload.notes = form.notes;

    try {
      if (editing) {
        await api.put(`/ivf-batches/${editing.ivf_batch_id}`, payload);
      } else {
        await api.post("/ivf-batches/", payload);
      }
      onSaved();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const opuLabel = (s: OPUSession) => `${s.donor_tag ?? s.donor_id} · ${s.opu_date}`;

  return (
    <ModalShell title={editing ? `Edit IVF Batch #${editing.ivf_batch_id}` : "New IVF Batch"} icon={TestTube} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="ivf-opu">OPU Session *</Label>
            <Select id="ivf-opu" value={form.opu_id} onChange={set("opu_id")} required>
              <option value="">Select...</option>
              {opuSessions.map((s) => <option key={s.opu_id} value={s.opu_id}>{opuLabel(s)}</option>)}
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="ivf-ivm">IVM Batch {editing ? "" : "*"}</Label>
            <Select id="ivf-ivm" value={form.ivm_batch_id} onChange={set("ivm_batch_id")} required={!editing} disabled={!form.opu_id}>
              <option value="">Select...</option>
              {ivmOptions.map((b) => (
                <option key={b.ivm_batch_id} value={b.ivm_batch_id}>
                  IVM #{b.ivm_batch_id}{b.ivm_date ? ` · ${b.ivm_date}` : ""}
                </option>
              ))}
            </Select>
            {form.opu_id && ivmOptions.length === 0 && (
              <p className="text-xs text-[#9d3730]">
                No IVM batch for this OPU session yet. Record one on Oocytes &amp; IVM first.
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="ivf-sire">Sire</Label>
            <Select id="ivf-sire" value={form.sire_id} onChange={set("sire_id")}>
              <option value="">Select...</option>
              {sires.map((s) => <option key={s.sire_id} value={s.sire_id}>{s.name}</option>)}
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="ivf-date">IVF Date</Label>
            <Input id="ivf-date" type="date" value={form.ivf_date} onChange={set("ivf_date")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ivf-embryologist">Embryologist</Label>
            <Select id="ivf-embryologist" value={form.embryologist_id} onChange={set("embryologist_id")}>
              <option value="">Select...</option>
              {technicians.map((t) => <option key={t.technician_id} value={t.technician_id}>{t.name}</option>)}
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="ivf-oocytes-used">Oocytes Used</Label>
            <Input id="ivf-oocytes-used" type="number" min="0" value={form.oocytes_used} onChange={set("oocytes_used")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ivf-mature">Mature Oocytes</Label>
            <Input id="ivf-mature" type="number" min="0" value={form.mature_oocytes} onChange={set("mature_oocytes")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ivf-cleaved">Cleaved Embryos</Label>
            <Input id="ivf-cleaved" type="number" min="0" value={form.cleaved_embryos} onChange={set("cleaved_embryos")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ivf-blastocysts">Blastocysts</Label>
            <Input id="ivf-blastocysts" type="number" min="0" value={form.blastocysts} onChange={set("blastocysts")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ivf-degenerated">Degenerated Embryos</Label>
            <Input id="ivf-degenerated" type="number" min="0" value={form.degenerated_embryos} onChange={set("degenerated_embryos")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ivf-media">Culture Media</Label>
            <Input id="ivf-media" value={form.culture_media} onChange={set("culture_media")} />
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="ivf-notes">Notes</Label>
          <Textarea id="ivf-notes" value={form.notes} onChange={set("notes")} rows={2} />
        </div>

        {error && <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}

        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? "Saving..." : editing ? "Update" : "Create"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}
