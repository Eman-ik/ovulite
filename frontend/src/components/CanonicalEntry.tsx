import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";

type Field = { title?: string; type?: string; format?: string; enum?: string[]; anyOf?: Field[]; minimum?: number; maximum?: number; minLength?: number; maxLength?: number };
export type CanonicalSchema = { properties: Record<string, Field>; required: string[] };

export default function CanonicalEntry() {
  const [schema, setSchema] = useState<CanonicalSchema | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [reference, setReference] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  useEffect(() => { api.get<CanonicalSchema>("/intake/schema").then(({ data }) => setSchema(data)).catch(() => setError("Unable to load the collection schema.")); }, []);
  async function save(event: FormEvent) {
    event.preventDefault(); if (!schema) return; setBusy(true); setError("");
    const record = Object.fromEntries(Object.entries(values).filter(([, value]) => value !== "").map(([key, value]) => {
      const definition = schema.properties[key]; const field = definition.anyOf?.find(item => item.type !== "null") ?? definition;
      return [key, field.type === "boolean" ? value === "true" : ["number", "integer"].includes(field.type ?? "") ? Number(value) : value];
    }));
    try { const { data } = await api.post("/intake/manual", { record, source_reference: reference }); navigate(`/app/cases/${data.transfer_id}`); }
    catch (e) { const detail = axios.isAxiosError(e) ? e.response?.data?.detail : null; setError(typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map(item => `${item.loc?.join(".")}: ${item.msg}`).join("; ") : "Unable to save the case."); }
    finally { setBusy(false); }
  }
  function control(key: string) {
    if (!schema) return null;
    const definition = schema.properties[key]; const field = definition.anyOf?.find(item => item.type !== "null") ?? definition;
    const required = schema.required.includes(key);
    const classes = "mt-1 w-full rounded-lg border border-slate-400/40 bg-[var(--background)] p-2 text-[var(--foreground)]";
    const options = field.enum ?? (field.type === "boolean" ? ["true", "false"] : null);
    return <label key={key} className="block">{definition.title ?? key}{required ? " *" : ""}{options ? <select className={classes} required={required} value={values[key] ?? ""} onChange={e => setValues({ ...values, [key]: e.target.value })}><option value="">Not recorded</option>{options.map(option => <option key={option} value={option}>{option === "true" ? "Yes" : option === "false" ? "No" : option}</option>)}</select> : <input className={classes} required={required} type={field.format === "date" ? "date" : ["integer", "number"].includes(field.type ?? "") ? "number" : "text"} step={field.type === "integer" ? 1 : "any"} min={field.minimum} max={field.maximum} minLength={field.minLength} maxLength={field.maxLength} value={values[key] ?? ""} onChange={e => setValues({ ...values, [key]: e.target.value })} />}</label>;
  }
  return <form onSubmit={save} className="space-y-5"><h2 className="text-xl font-semibold">Create a reproductive case</h2><p>Real observations only. Leave unmeasured optional fields blank. BCS uses the 1–5 scale; ages are in years; P4 is ng/mL and CL size is mm.</p>{error && <p role="alert">{error}</p>}
    {!schema ? <p>Loading fields…</p> : <><div className="grid gap-3 md:grid-cols-2">{schema.required.map(control)}</div><details><summary className="cursor-pointer font-medium">Optional lineage, recipient, embryo and follow-up fields</summary><div className="mt-4 grid gap-3 md:grid-cols-2">{Object.keys(schema.properties).filter(key => !schema.required.includes(key)).map(control)}</div></details></>}
    <label className="block">Source reference<input required minLength={5} maxLength={1000} className="mt-1 w-full rounded-lg border border-slate-400/40 bg-[var(--background)] p-2" value={reference} onChange={e => setReference(e.target.value)} placeholder="Collection log, record owner or institution" /></label>
    <Button disabled={busy || !schema} type="submit">{busy ? "Saving…" : "Create case"}</Button>
  </form>;
}
