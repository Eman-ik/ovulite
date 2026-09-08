import { useEffect, useState } from "react";
import axios from "axios";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import CanonicalEntry, { type CanonicalSchema } from "@/components/CanonicalEntry";

type Report = { total: number; accepted: number; rejected: number; duplicate: number; incomplete: number; unmapped_columns?: string[]; missing_by_field?: Record<string, number>; rows: { row: number; status: string; errors: string[] }[] };
type Batch = { batch_id: string; filename: string; source_type: string; source_reference: string; status: string; checksum: string; created_by: string; report: Report };
type Inspection = { headers: string[]; fields: Record<string, { title: string }>; required: string[] };

export default function IntakePage() {
  const [text, setText] = useState("");
  const [filename, setFilename] = useState("");
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [sourceType, setSourceType] = useState("real_internal");
  const [reference, setReference] = useState("");
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selected, setSelected] = useState<Batch | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [manual, setManual] = useState(false);
  const inputClass = "mt-1 w-full rounded-lg border border-slate-400/40 bg-[var(--background)] p-2 text-[var(--foreground)]";
  function failure(e: unknown) { const detail = axios.isAxiosError(e) ? e.response?.data?.detail : null; setError(typeof detail === "string" ? detail : e instanceof Error ? e.message : "Request failed. Check your inputs and try again."); }
  async function refresh() { const { data } = await api.get("/intake/batches"); setBatches(data); return data as Batch[]; }
  useEffect(() => { refresh().catch(failure); }, []);
  async function inspect(file?: File) {
    if (!file) return;
    setBusy(true); setError(""); setSelected(null); setInspection(null); setMessage("");
    try {
      if (file.size > 5000000) throw new Error("File too large");
      let csv: string;
      try { csv = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(await file.arrayBuffer()); }
      catch { throw new Error("CSV must use valid UTF-8 encoding. Export the file as UTF-8 and try again."); }
      const { data } = await api.post<Inspection>("/intake/inspect", { csv_text: csv });
      setText(csv); setFilename(file.name); setInspection(data);
      setMapping(Object.fromEntries(Object.keys(data.fields).filter(key => data.headers.includes(key)).map(key => [key, key])));
    } catch (e) { failure(e); } finally { setBusy(false); }
  }
  async function preview() {
    setBusy(true); setError(""); setMessage("");
    try {
      const { data } = await api.post("/intake/preview", { filename, csv_text: text, mapping, source_type: sourceType, source_reference: reference });
      const list = await refresh(); setSelected(list.find(batch => batch.batch_id === data.batch_id) ?? null);
    } catch (e) { failure(e); } finally { setBusy(false); }
  }
  async function commit() {
    if (!selected) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const { data } = await api.post(`/intake/batches/${selected.batch_id}/commit`);
      setMessage(data.message ?? `${data.inserted} validated records imported.`);
      const list = await refresh(); setSelected(list.find(batch => batch.batch_id === selected.batch_id) ?? null);
    } catch (e) { failure(e); } finally { setBusy(false); }
  }
  async function template() {
    let schema: CanonicalSchema;
    try { schema = (await api.get<CanonicalSchema>("/intake/schema")).data; } catch (e) { failure(e); return; }
    const csv = Object.keys(schema.properties).join(",") + "\r\n";
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a"); a.href = url; a.download = "ovulite-et-collection-template.csv"; a.click(); URL.revokeObjectURL(url);
  }
  return <div className="mx-auto max-w-5xl space-y-6 pb-10"><h1 className="text-3xl font-bold">Data Import</h1>
    <Button type="button" variant="outline" onClick={() => setManual(!manual)}>{manual ? "Close manual form" : "Enter a case manually"}</Button>
    {manual && <Card><CardContent className="pt-6"><CanonicalEntry /></CardContent></Card>}
    <p>Map your columns, review validation, then import accepted rows. Original CSV text and provenance are retained.</p>
    {error && <p role="alert" className="rounded-lg border border-red-400 p-3">{error}</p>}{message && <p role="status">{message}</p>}
    <Card><CardHeader><CardTitle>1. Select and map a CSV</CardTitle></CardHeader><CardContent className="space-y-4">
      <Button type="button" onClick={template}>Download collection template</Button>
      <label className="block">CSV file (UTF-8, up to 5 MB / 10,000 rows)<input disabled={busy} className={inputClass} type="file" accept=".csv,text/csv" onChange={e => void inspect(e.target.files?.[0])} /></label>
      {inspection && <><div className="grid gap-3 md:grid-cols-2">{Object.entries(inspection.fields).map(([key, field]) => <label key={key}>{field.title}{inspection.required.includes(key) ? " *" : ""}<select className={inputClass} value={mapping[key] ?? ""} onChange={e => { const next = { ...mapping }; if (e.target.value) next[key] = e.target.value; else delete next[key]; setMapping(next); }}><option value="">Choose column</option>{inspection.headers.map(header => <option key={header}>{header}</option>)}</select></label>)}</div>
      <p className="text-sm opacity-75">Dates: YYYY-MM-DD. BCS: 1–5 scale. CL: millimetres. Stage: 4–8. Grade: 1–4. Resolved pregnancy outcomes require the check date. ET numbers must be unique within your organization.</p>
      <label className="block">Data source<select className={inputClass} value={sourceType} onChange={e => setSourceType(e.target.value)}><option value="real_internal">Real internal observations</option><option value="external_collaboration">External collaboration</option><option value="public_dataset">Public dataset</option><option value="synthetic_demo">Synthetic demonstration (staging only)</option></select></label>
      <label className="block">Source reference / permission<input minLength={5} maxLength={1000} className={inputClass} value={reference} onChange={e => setReference(e.target.value)} /></label>
      <Button disabled={busy || reference.trim().length < 5 || inspection.required.some(key => !mapping[key])} onClick={preview}>Validate and save preview</Button></>}
    </CardContent></Card>
    {selected && <Card><CardHeader><CardTitle>2. Review: {selected.filename}</CardTitle></CardHeader><CardContent className="space-y-4">
      <p>{selected.source_type} · {selected.source_reference} · {selected.status}</p>
      <p>Total: {selected.report.total} · Accepted: {selected.report.accepted} · Rejected: {selected.report.rejected} · Duplicate: {selected.report.duplicate} · Incomplete: {selected.report.incomplete}</p>
      {!!selected.report.unmapped_columns?.length && <p>Columns not mapped: {selected.report.unmapped_columns.join(", ")}. Their original values remain in the source CSV.</p>}
      {selected.report.missing_by_field && <details><summary className="cursor-pointer">Missing values by field</summary><dl className="mt-2 grid grid-cols-2 gap-2">{Object.entries(selected.report.missing_by_field).map(([key, count]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{count} / {selected.report.total}</dd></div>)}</dl></details>}
      <div className="max-h-72 overflow-auto"><table className="w-full text-left"><thead><tr><th>CSV row</th><th>Status</th><th>Correction</th></tr></thead><tbody>{selected.report.rows.map(row => <tr key={row.row}><td className="p-2">{row.row}</td><td>{row.status}</td><td>{row.errors.join("; ") || "Validated"}</td></tr>)}</tbody></table></div>
      <p className="break-all text-sm opacity-70">Uploaded by {selected.created_by} · SHA-256 {selected.checksum}</p>
      {selected.status === "preview" && <Button disabled={busy || !selected.report.accepted} onClick={commit}>{selected.source_type === "synthetic_demo" ? "Keep demo in staging" : `Import ${selected.report.accepted} accepted rows`}</Button>}
    </CardContent></Card>}
    <Card><CardHeader><CardTitle>Import history</CardTitle></CardHeader><CardContent><ul className="space-y-3">{batches.map(batch => <li key={batch.batch_id}><button className="text-left underline" onClick={() => { setSelected(batch); setMessage(""); }}>{batch.filename} · {batch.source_type} · {batch.status}</button></li>)}</ul>{!batches.length && <p>No saved imports yet.</p>}</CardContent></Card>
  </div>;
}
