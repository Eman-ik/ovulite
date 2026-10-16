import { useEffect, useState, type FormEvent } from "react";
import axios from "axios";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { normalizeRole } from "@/lib/roleRoutes";

type Document = { document_id: number; title: string; authors: string; year: number; source_url: string; source_kind: string; rights: string };
type Citation = Document & { passage: number; excerpt: string };
type Answer = { answer: string; citations: Citation[]; corpus_size: number; limitations: string; mode: string; model: string | null; fallback_reason: string | null };
const empty = { title: "", authors: "", year: new Date().getFullYear(), source_url: "", source_kind: "peer_reviewed", rights: "", content: "" };

export default function LiteraturePage() {
  const { user } = useAuth();
  const canCurate = ["admin", "embryologist"].includes(normalizeRole(user?.role));
  const [documents, setDocuments] = useState<Document[]>([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [draft, setDraft] = useState(empty);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [adding, setAdding] = useState(false);
  const [loading, setLoading] = useState(true);
  async function refresh() { const { data } = await api.get("/literature/documents"); setDocuments(data.items); }
  function showError(e: unknown) {
    const detail = axios.isAxiosError(e) ? e.response?.data?.detail : null;
    setError(typeof detail === "string" ? detail : "The request failed. Check the fields and try again.");
  }
  useEffect(() => { refresh().catch(showError).finally(() => setLoading(false)); }, []);
  async function ask(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setAnswer(null);
    try { setAnswer((await api.post("/literature/query", { question })).data); }
    catch (e) { showError(e); } finally { setBusy(false); }
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { await api.post("/literature/documents", draft); setDraft(empty); setAdding(false); await refresh(); }
    catch (e) { showError(e); } finally { setBusy(false); }
  }
  async function seed() {
    setBusy(true); setError("");
    try { await api.post("/literature/seed"); await refresh(); }
    catch (e) { showError(e); } finally { setBusy(false); }
  }
  const inputClass = "mt-1 w-full rounded-lg border border-slate-400/40 bg-[var(--background)] p-3 text-[var(--foreground)]";
  return <div className="mx-auto max-w-5xl space-y-6 pb-10">
    <div><h1 className="text-3xl font-bold">Literature Intelligence</h1><p className="mt-2 opacity-75">Explore attributable evidence from your organization’s curated papers and approved SOPs.</p></div>
    {error && <p role="alert" className="rounded-lg border border-red-400 p-3">{error}</p>}
    <Card><CardHeader><CardTitle>Ask the evidence</CardTitle></CardHeader><CardContent>
      <form onSubmit={ask} className="space-y-3"><label className="block">Your question<textarea required minLength={3} maxLength={2000} className={inputClass} value={question} onChange={e => setQuestion(e.target.value)} placeholder="What evidence discusses progesterone and pregnancy after bovine embryo transfer?" /></label>
      <Button disabled={busy || loading} type="submit">{busy ? "Working…" : "Find evidence"}</Button></form>
      <p className="mt-3 text-sm opacity-70">Cited evidence and local AI synthesis when enabled • Human review required</p>
    </CardContent></Card>
    {answer && <section aria-live="polite" className="space-y-4"><p className="text-sm font-medium">{answer.mode === "generative_rag" ? `Evidence-grounded synthesis · ${answer.model}` : "Retrieved evidence"}</p><p className="whitespace-pre-line">{answer.answer}</p>{answer.fallback_reason && <p role="status" className="text-sm">{answer.fallback_reason}</p>}<p className="text-sm opacity-70">Searched {answer.corpus_size} documents. {answer.limitations}</p>
      {answer.citations.map((citation, i) => <Card key={`${citation.document_id}-${citation.passage}`}><CardHeader><CardTitle>[{i + 1}] {citation.title}</CardTitle><p>{citation.authors} · {citation.year} · {citation.source_kind === "approved_sop" ? "Approved SOP" : "Peer-reviewed source"} · Passage {citation.passage}</p></CardHeader><CardContent><blockquote className="border-l-4 border-amber-400 pl-4">{citation.excerpt}</blockquote><a className="mt-3 inline-block underline" href={citation.source_url} target="_blank" rel="noopener noreferrer">Open original source</a></CardContent></Card>)}
    </section>}
    <Card><CardHeader><CardTitle>Curated corpus {loading ? "…" : `(${documents.length} / 50 minimum target)`}</CardTitle></CardHeader><CardContent className="space-y-4">
      {!loading && !documents.length && <p>No sources have been added. A curator can add licensed paper text, abstracts, or approved SOPs with attribution.</p>}
      {canCurate && <Button type="button" onClick={() => setAdding(!adding)}>{adding ? "Close form" : "Add evidence source"}</Button>}
      {canCurate && <Button type="button" disabled={busy} onClick={seed}>Load 60-paper licensed starter corpus</Button>}
      {adding && <form onSubmit={save} className="space-y-3">
        <label className="block">Title<input required minLength={3} maxLength={500} className={inputClass} value={draft.title} onChange={e => setDraft({ ...draft, title: e.target.value })} /></label>
        <label className="block">Authors or SOP owner<input required minLength={2} maxLength={1000} className={inputClass} value={draft.authors} onChange={e => setDraft({ ...draft, authors: e.target.value })} /></label>
        <label className="block">Publication year<input required type="number" min={1900} max={2100} className={inputClass} value={draft.year} onChange={e => setDraft({ ...draft, year: Number(e.target.value) })} /></label>
        <label className="block">Source URL<input required type="url" maxLength={2000} className={inputClass} value={draft.source_url} onChange={e => setDraft({ ...draft, source_url: e.target.value })} /></label>
        <label className="block">Evidence type<select className={inputClass} value={draft.source_kind} onChange={e => setDraft({ ...draft, source_kind: e.target.value })}><option value="peer_reviewed">Peer-reviewed paper</option><option value="approved_sop">Approved SOP</option></select></label>
        <label className="block">License or permission to use this text<input required minLength={5} maxLength={1000} className={inputClass} value={draft.rights} onChange={e => setDraft({ ...draft, rights: e.target.value })} placeholder="Record the license or institutional permission" /></label>
        <label className="block">Source text (100–200,000 characters)<textarea required minLength={100} maxLength={200000} rows={8} className={inputClass} value={draft.content} onChange={e => setDraft({ ...draft, content: e.target.value })} /></label>
        <p className="text-sm opacity-70">Only add text your organization is permitted to store. Verify its authorship and approval status before adding it.</p><Button type="submit" disabled={busy}>Save source</Button>
      </form>}
      <ul className="divide-y divide-slate-400/20">{documents.map(doc => <li key={doc.document_id} className="py-3"><a className="font-medium underline" href={doc.source_url} target="_blank" rel="noopener noreferrer">{doc.title}</a><p className="text-sm opacity-70">{doc.authors} · {doc.year} · {doc.rights}</p></li>)}</ul>
    </CardContent></Card>
  </div>;
}
