import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type History = { total: number; items: { transfer_id: number; date: string; outcome: string | null; checkpoint_date: string | null }[] };
type Timeline = { events: { kind: string; date: string; label: string; record_id: number }[]; recipient_history: History; donor_history: History; limitations: string; canonical_record: Record<string, unknown> | null; record_version: number | null; audit: { action: string; actor: string; timestamp: string }[]; provenance: { source_type: string; source_row: number | null; filename: string; reference: string; checksum: string | null; imported_by: string } | null };

export default function CaseTimeline({ transferId }: { transferId: string }) {
  const [data, setData] = useState<Timeline | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setData(null); setError("");
    api.get(`/case-timeline/${transferId}/timeline`).then(response => { if (active) setData(response.data); }).catch(() => { if (active) setError("Unable to load case timeline."); });
    return () => { active = false; };
  }, [transferId]);
  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p role="status">Loading timeline…</p>;
  return <div className="space-y-4"><Card><CardHeader><CardTitle>Reproductive timeline</CardTitle></CardHeader><CardContent>
    <ol className="space-y-4 border-l-2 border-amber-400 pl-4">{data.events.map((event, index) => <li key={index}><time className="text-sm opacity-70">{event.date}</time><p className="font-medium">{event.label}</p><p className="text-sm opacity-70">Record {event.record_id}</p></li>)}</ol>
    <p className="mt-4 text-sm opacity-70">{data.limitations}</p>
  </CardContent></Card>
  {([ ["Recipient", data.recipient_history], ["Donor", data.donor_history] ] as const).map(([label, history]) => <Card key={label}><CardHeader><CardTitle>{label} history · {history.total} earlier transfers</CardTitle></CardHeader><CardContent>
    {!history.total && <p>No earlier linked attempts recorded.</p>}<ul className="space-y-2">{history.items.map(row => <li key={row.transfer_id}><Link className="underline" to={`/app/cases/${row.transfer_id}`}>ET {row.transfer_id}</Link> · {row.date} · {row.outcome ?? "Outcome not recorded"}{row.checkpoint_date ? ` (checked ${row.checkpoint_date})` : ""}</li>)}</ul>
  </CardContent></Card>)}
  <Card><CardHeader><CardTitle>Data provenance</CardTitle></CardHeader><CardContent>{data.provenance ? <div className="space-y-2"><p>{data.provenance.source_type} · {data.provenance.filename}{data.provenance.source_row ? `, row ${data.provenance.source_row}` : ""}</p><p>{data.provenance.reference}</p><p>Recorded by {data.provenance.imported_by}</p>{data.provenance.checksum && <p className="break-all text-xs">SHA-256: {data.provenance.checksum}</p>}</div> : <p>No import provenance is recorded for this case. Its source classification has not been inferred.</p>}</CardContent></Card>
  {data.canonical_record && <Card><CardHeader><CardTitle>Canonical record · version {data.record_version}</CardTitle></CardHeader><CardContent><dl className="grid gap-3 md:grid-cols-2">{Object.entries(data.canonical_record).filter(([, value]) => value !== null && value !== undefined).map(([key, value]) => <div key={key}><dt className="text-sm opacity-70">{key.replaceAll("_", " ")}</dt><dd>{typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}</dd></div>)}</dl></CardContent></Card>}
  <Card><CardHeader><CardTitle>Record audit</CardTitle></CardHeader><CardContent>{data.audit?.length ? <ol className="space-y-2">{data.audit.map((event, index) => <li key={index}>{event.timestamp} · {event.action} · {event.actor}</li>)}</ol> : <p>No attributable changes recorded yet.</p>}</CardContent></Card></div>;
}
