import { useState } from "react";
import { ChevronDown, Info, TrendingUp, TrendingDown } from "lucide-react";
import type { AttributionResponse, Decomposition } from "@/lib/types";

const MIX = "#8d97c4"; // composition changed
const RATE = "#4f8f7d"; // performance within groups changed

const DIMENSION_LABELS: Record<string, string> = {
  cl_side: "CL Side",
  fresh_or_frozen: "Fresh / Frozen",
  donor_breed: "Donor Breed",
};

function prettyDimension(key: string) {
  return DIMENSION_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Two bars sharing one scale, so mix and rate are compared by length rather
 * than by reading two numbers. Negative contributions extend left of centre.
 */
function ContributionBar({ value, max, color }: { value: number; max: number; color: string }) {
  const half = 50;
  const pct = max === 0 ? 0 : (Math.abs(value) / max) * half;
  return (
    <div className="relative h-4 w-full rounded bg-black/[0.04]">
      <div className="absolute left-1/2 top-0 h-4 w-px bg-black/15" />
      <div
        className="absolute top-0.5 h-3 rounded-sm"
        style={{
          background: color,
          width: `${pct}%`,
          left: value >= 0 ? `${half}%` : `${half - pct}%`,
        }}
      />
    </div>
  );
}

function DecompositionRow({ d, max }: { d: Decomposition; max: number }) {
  const [open, setOpen] = useState(false);
  const compositional = d.mix_share >= 0.5;

  return (
    <div className="border-b border-[var(--border)] last:border-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="grid w-full grid-cols-[8.5rem_1fr_4rem_1fr_4rem_1.25rem] items-center gap-3 py-3 text-left transition hover:bg-black/[0.02]"
      >
        <span className="text-sm font-medium dash-heading">{prettyDimension(d.dimension)}</span>
        <ContributionBar value={d.mix_pp} max={max} color={MIX} />
        <span className={`text-right text-xs font-semibold ${compositional ? "text-[#5f6ba0]" : "dash-muted"}`}>
          {d.mix_pp > 0 ? "+" : ""}
          {d.mix_pp} pp
        </span>
        <ContributionBar value={d.rate_pp} max={max} color={RATE} />
        <span className={`text-right text-xs font-semibold ${compositional ? "dash-muted" : "text-[#2f6b5c]"}`}>
          {d.rate_pp > 0 ? "+" : ""}
          {d.rate_pp} pp
        </span>
        <ChevronDown
          className={`h-4 w-4 dash-muted transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="pb-4">
          <p className="mb-3 text-xs leading-relaxed dash-muted">{d.verdict}</p>
          <div className="custom-scrollbar overflow-x-auto">
            <table className="w-full min-w-[560px] text-xs">
              <thead>
                <tr className="text-left uppercase tracking-wide dash-muted">
                  <th className="pb-1 pr-3 font-medium">Group</th>
                  <th className="pb-1 pr-3 font-medium">Share</th>
                  <th className="pb-1 pr-3 font-medium">Rate</th>
                  <th className="pb-1 pr-3 font-medium">Mix</th>
                  <th className="pb-1 font-medium">Rate effect</th>
                </tr>
              </thead>
              <tbody>
                {d.groups.map((g) => (
                  <tr key={g.label} className="border-t border-[var(--border)]">
                    <td className="py-1.5 pr-3 dash-heading">
                      {g.label}
                      {g.only_in && (
                        <span className="ml-1.5 rounded-full bg-[rgba(141,151,196,0.22)] px-1.5 py-px text-[9px] font-semibold text-[#5f6ba0]">
                          {g.only_in} only
                        </span>
                      )}
                    </td>
                    <td className="py-1.5 pr-3 dash-muted">
                      {g.share_before}% → {g.share_after}%
                    </td>
                    <td className="py-1.5 pr-3 dash-muted">
                      {g.rate_before_pct === null ? "—" : `${g.rate_before_pct}%`} →{" "}
                      {g.rate_after_pct === null ? "—" : `${g.rate_after_pct}%`}
                      <span className="ml-1 text-[10px]">
                        (n={g.n_before}→{g.n_after})
                      </span>
                    </td>
                    <td className="py-1.5 pr-3" style={{ color: MIX }}>
                      {g.mix_pp > 0 ? "+" : ""}
                      {g.mix_pp}
                    </td>
                    <td className="py-1.5" style={{ color: RATE }}>
                      {g.rate_pp > 0 ? "+" : ""}
                      {g.rate_pp}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AttributionPanel({ data }: { data: AttributionResponse | null }) {
  if (!data) return <p className="mt-4 text-sm dash-muted">Loading…</p>;

  const c = data.change_point;
  if (!c) {
    return (
      <p className="mt-4 text-sm dash-muted">
        No step change in pregnancy rate stands out from normal variation over the recorded period.
      </p>
    );
  }

  const rose = c.delta_pp > 0;
  const max = Math.max(...c.decompositions.flatMap((d) => [Math.abs(d.mix_pp), Math.abs(d.rate_pp)]), 1);

  return (
    <div className="mt-4">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-2xl bg-[#f6faf7] p-4">
        <div className="flex items-center gap-3">
          <div
            className="flex h-11 w-11 items-center justify-center rounded-2xl"
            style={{
              background: rose ? "rgba(142,182,155,0.2)" : "rgba(185,142,168,0.2)",
              color: rose ? "#235347" : "#9d3730",
            }}
          >
            {rose ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide dash-muted">
              Change detected at {c.period}
            </p>
            <p className="text-[26px] font-semibold leading-tight dash-heading">
              {c.delta_pp > 0 ? "+" : ""}
              {c.delta_pp} pp
            </p>
          </div>
        </div>

        <div className="text-sm dash-muted">
          <p>
            <span className="dash-heading">{c.rate_before_pct}%</span> over {c.n_before} transfers →{" "}
            <span className="dash-heading">{c.rate_after_pct}%</span> over {c.n_after}
          </p>
          <p className="mt-0.5 text-xs">
            permutation p = {c.permutation_p} · z = {c.z_score}
          </p>
        </div>
      </div>

      <p className="mt-4 text-sm leading-relaxed dash-heading">{c.summary}</p>

      <div className="mt-5 grid grid-cols-[8.5rem_1fr_4rem_1fr_4rem_1.25rem] gap-3 border-b border-[var(--border)] pb-2 text-[10px] uppercase tracking-wide dash-muted">
        <span>Dimension</span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-sm" style={{ background: MIX }} />
          Mix — what changed
        </span>
        <span className="text-right">pp</span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-sm" style={{ background: RATE }} />
          Rate — how well
        </span>
        <span className="text-right">pp</span>
        <span />
      </div>

      {c.decompositions.map((d) => (
        <DecompositionRow key={d.dimension} d={d} max={max} />
      ))}

      <div className="mt-4 flex items-start gap-2 rounded-xl bg-[#f6faf7] px-3 py-2.5 text-[11px] leading-relaxed dash-muted">
        <Info className="mt-px h-3.5 w-3.5 shrink-0" />
        <span>{data.note}</span>
      </div>
    </div>
  );
}
