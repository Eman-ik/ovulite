import { useEffect, useState } from "react";
import { AlertTriangle, Activity, FlaskConical, GitCompare, Grid3x3, Info } from "lucide-react";
import AttributionPanel from "@/components/research/AttributionPanel";
import api from "@/lib/api";
import type {
  AttributionResponse,
  DonorSireResponse,
  OutcomeFactorsResponse,
  ProtocolComparisonResponse,
  RateCell,
} from "@/lib/types";

/** Pale mint → sage → deep emerald. Deliberately sequential, not diverging:
 *  pregnancy rate has no meaningful midpoint to diverge around. */
function heatRGB(pct: number | null): [number, number, number] {
  if (pct === null) return [234, 243, 236];
  const t = Math.max(0, Math.min(1, pct / 60));
  // The dark end stops at a mid sage rather than continuing to #596070. Going
  // darker lands the cell in a luminance band where neither a dark nor a light
  // label reaches 4.5:1 — the scale is bounded so one ink always works.
  const stops: [number, [number, number, number]][] = [
    [0, [237, 246, 239]],
    [0.5, [168, 203, 180]],
    [1, [95, 144, 124]],
  ];
  let [lo, hi] = [stops[0], stops[1]];
  if (t > 0.5) [lo, hi] = [stops[1], stops[2]];
  const f = (t - lo[0]) / (hi[0] - lo[0]);
  return lo[1].map((v, i) => Math.round(v + (hi[1][i] - v) * f)) as [number, number, number];
}

function heatColor(pct: number | null): string {
  const [r, g, b] = heatRGB(pct);
  return `rgb(${r}, ${g}, ${b})`;
}

/**
 * The label colour follows the cell, not the palette. The previous warm scale
 * used one fixed ink across the whole range and left `n=5` at 2.06:1 on the
 * darkest cells.
 *
 * With the bounded scale above every cell sits in the dark-ink branch; the
 * light branch is the guard that keeps this correct if the stops are ever
 * changed. 0.23 is where #2E3645 stops reaching 4.5:1.
 */
function heatInk(pct: number | null): string {
  const [r, g, b] = heatRGB(pct);
  const lin = (v: number) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  const luminance = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  return luminance > 0.23 ? "#2E3645" : "#FFFFFF";
}

function Rate({ cell }: { cell: RateCell }) {
  if (cell.insufficient_data) {
    return <span className="text-xs dash-muted">n={cell.n} · too few</span>;
  }
  return (
    <span>
      <span className="font-semibold dash-heading">{cell.rate_pct}%</span>
      <span className="ml-1.5 text-xs dash-muted">
        {cell.successes}/{cell.n}
      </span>
    </span>
  );
}

/** Wilson interval drawn on a shared 0–60% scale so rows compare visually. */
function IntervalBar({ cell, scaleMax = 60 }: { cell: RateCell; scaleMax?: number }) {
  if (cell.insufficient_data || cell.rate_pct === null) {
    return <div className="h-1.5 w-full rounded-full bg-black/[0.05]" />;
  }
  const pos = (v: number) => `${Math.min(100, (v / scaleMax) * 100)}%`;
  return (
    <div className="relative h-1.5 w-full rounded-full bg-black/[0.05]">
      <div
        className="absolute h-1.5 rounded-full bg-[rgba(106,165,184,0.55)]"
        style={{ left: pos(cell.ci_low_pct ?? 0), width: `calc(${pos(cell.ci_high_pct ?? 0)} - ${pos(cell.ci_low_pct ?? 0)})` }}
      />
      <div
        className="absolute top-[-2px] h-[10px] w-[2px] rounded-full bg-[#3f7c91]"
        style={{ left: pos(cell.rate_pct) }}
      />
    </div>
  );
}

function Diff({ value, bold, strike }: { value: number | null; bold?: boolean; strike?: boolean }) {
  if (value === null) return <span className="dash-muted">—</span>;
  return (
    <span
      className={`${value > 0 ? "text-[#3F4758]" : "text-[#9d3730]"} ${bold ? "font-semibold" : ""} ${
        strike ? "line-through decoration-[#9d3730]/50" : ""
      }`}
    >
      {value > 0 ? "+" : ""}
      {value} pp
    </span>
  );
}

function PValue({
  value,
  significant,
  strike,
}: {
  value: number | null;
  significant: boolean | null;
  strike?: boolean;
}) {
  if (value === null) return <span className="dash-muted">—</span>;
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        significant ? "bg-[rgba(208,164,94,0.22)] text-[#7a5a12]" : "dash-muted"
      } ${strike ? "line-through" : ""}`}
    >
      {value < 0.001 ? "<0.001" : value}
    </span>
  );
}

function SectionNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-4 flex items-start gap-2 rounded-xl bg-[#f6faf7] px-3 py-2.5 text-[11px] leading-relaxed dash-muted">
      <Info className="mt-px h-3.5 w-3.5 shrink-0" />
      <span>{children}</span>
    </div>
  );
}

export default function ResearchPage() {
  const [protocols, setProtocols] = useState<ProtocolComparisonResponse | null>(null);
  const [donorSire, setDonorSire] = useState<DonorSireResponse | null>(null);
  const [factors, setFactors] = useState<OutcomeFactorsResponse | null>(null);
  const [attribution, setAttribution] = useState<AttributionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<ProtocolComparisonResponse>("/research/protocols"),
      api.get<DonorSireResponse>("/research/donor-sire"),
      api.get<OutcomeFactorsResponse>("/research/outcome-factors"),
      api.get<AttributionResponse>("/research/attribution"),
    ])
      .then(([p, d, f, a]) => {
        setProtocols(p.data);
        setDonorSire(d.data);
        setFactors(f.data);
        setAttribution(a.data);
      })
      .catch(() => setError("Unable to load research analyses from the server."));
  }, []);

  const overall = factors?.overall ?? donorSire?.overall ?? null;

  // Matrix lookup keyed by donor tag + sire name.
  const cellFor = (donor: string, sire: string) =>
    donorSire?.cells.find((c) => c.donor_tag === donor && c.sire_name === sire) ?? null;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold dash-heading">Reproductive Intelligence</h1>
        <p className="mt-1 text-sm dash-muted">
          Comparative outcome analysis across donors, sires, protocols and embryo attributes. Every
          rate is shown with the number of transfers behind it.
        </p>
      </div>

      {error && (
        <div className="rounded-2xl border border-[rgba(179,69,63,0.28)] bg-[rgba(185,142,168,0.16)] p-4 text-sm text-[#9d3730]">
          {error}
        </div>
      )}

      {overall && (
        <div className="dash-card flex flex-wrap items-baseline gap-x-8 gap-y-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide dash-muted">
              Overall Pregnancy Rate (PC1)
            </p>
            <p className="mt-1 text-[34px] font-semibold leading-none dash-heading">
              {overall.rate_pct}%
            </p>
          </div>
          <p className="text-sm dash-muted">
            {overall.successes} pregnant of {overall.n} transfers with a resolved outcome · 95% CI{" "}
            {overall.ci_low_pct}–{overall.ci_high_pct}%
          </p>
        </div>
      )}

      {/* ── Change attribution ── */}
      <div className="dash-card">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 dash-muted" />
          <h2 className="text-base font-semibold dash-heading">What Changed</h2>
        </div>
        <p className="mt-1 text-xs dash-muted">
          Step changes in pregnancy rate, split into what was transferred (mix) versus how well it
          went (rate). A large mix term means a comparison across this change would be confounded.
        </p>
        <AttributionPanel data={attribution} />
      </div>

      {/* ── Protocol comparison ── */}
      <div className="dash-card">
        <div className="flex items-center gap-2">
          <GitCompare className="h-4 w-4 dash-muted" />
          <h2 className="text-base font-semibold dash-heading">Protocol Comparison</h2>
        </div>
        {protocols?.baseline_protocol && (
          <p className="mt-1 text-xs dash-muted">
            Tested against <span className="font-medium">{protocols.baseline_protocol}</span>, the
            protocol with the largest sample.
          </p>
        )}

        {!protocols ? (
          <p className="mt-4 text-sm dash-muted">Loading…</p>
        ) : (
          <>
            {protocols.confounding_detected && protocols.warning && (
              <div className="mt-4 flex items-start gap-2.5 rounded-2xl border border-[rgba(179,69,63,0.3)] bg-[rgba(185,142,168,0.14)] px-4 py-3">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[#9d3730]" />
                <div className="text-sm text-[#8a3b36]">
                  <p className="font-semibold text-[#9d3730]">Confounded by time period</p>
                  <p className="mt-1 leading-relaxed">{protocols.warning}</p>
                </div>
              </div>
            )}

            {protocols.period_rates.length > 1 && (
              <div className="mt-4 rounded-2xl bg-[#f6faf7] p-4">
                <p className="text-xs font-medium uppercase tracking-wide dash-muted">
                  Programme rate by month
                </p>
                <div className="mt-3 flex items-end gap-1.5">
                  {protocols.period_rates.map((p) => (
                    <div key={p.period} className="flex flex-1 flex-col items-center gap-1">
                      <span className="text-[10px] dash-muted">
                        {p.rate_pct === null ? "" : `${Math.round(p.rate_pct)}%`}
                      </span>
                      <div
                        className="w-full rounded-t bg-[#66CAC8]"
                        style={{ height: `${Math.max(2, ((p.rate_pct ?? 0) / 60) * 52)}px` }}
                        title={`${p.period}: ${p.successes}/${p.n}`}
                      />
                      <span className="text-[9px] dash-muted">{p.period.slice(2)}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-2 text-[11px] dash-muted">
                  A protocol adopted during a strong month inherits that month's outcomes. This is
                  what the adjusted column removes.
                </p>
              </div>
            )}

            <div className="custom-scrollbar mt-4 overflow-x-auto">
              <table className="w-full min-w-[820px] text-sm">
                <thead>
                  <tr className="text-left text-[10px] uppercase tracking-wide dash-muted">
                    <th className="pb-1" />
                    <th className="pb-1" />
                    <th className="pb-1" />
                    <th className="border-b border-[var(--border)] pb-1 pr-4 text-center font-medium" colSpan={2}>
                      Pooled (ignores timing)
                    </th>
                    <th className="border-b border-[rgba(46, 54, 69,0.25)] pb-1 text-center font-medium text-[var(--foreground)]" colSpan={2}>
                      Adjusted for month
                    </th>
                  </tr>
                  <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide dash-muted">
                    <th className="pb-2 pr-4 font-medium">Protocol</th>
                    <th className="pb-2 pr-4 font-medium">Rate</th>
                    <th className="pb-2 pr-4 font-medium">95% CI</th>
                    <th className="pb-2 pr-3 font-medium">Diff</th>
                    <th className="pb-2 pr-4 font-medium">p</th>
                    <th className="pb-2 pr-3 font-medium">Diff</th>
                    <th className="pb-2 font-medium">p</th>
                  </tr>
                </thead>
                <tbody>
                  {protocols.rows.map((r) => (
                    <tr key={r.protocol_id} className="border-b border-[var(--border)] last:border-0 align-top">
                      <td className="py-3 pr-4">
                        <span className="dash-heading">{r.protocol_name}</span>
                        {r.is_baseline && (
                          <span className="ml-2 rounded-full bg-black/[0.05] px-2 py-0.5 text-[10px] font-semibold dash-muted">
                            baseline
                          </span>
                        )}
                        {r.confounded && (
                          <p className="mt-1.5 max-w-[26rem] text-[11px] leading-relaxed text-[#9d3730]">
                            {r.confound_reason}
                          </p>
                        )}
                      </td>
                      <td className="py-3 pr-4 whitespace-nowrap">
                        <Rate cell={r} />
                      </td>
                      <td className="w-36 py-3 pr-4">
                        <IntervalBar cell={r} />
                        {!r.insufficient_data && (
                          <span className="mt-1 block text-[10px] dash-muted">
                            {r.ci_low_pct}–{r.ci_high_pct}%
                          </span>
                        )}
                      </td>

                      {/* Pooled — struck through when the adjustment contradicts it. */}
                      <td className={`py-3 pr-3 whitespace-nowrap ${r.confounded ? "opacity-45" : ""}`}>
                        <Diff value={r.diff_vs_baseline_pp} strike={r.confounded} />
                      </td>
                      <td className={`py-3 pr-4 ${r.confounded ? "opacity-45" : ""}`}>
                        <PValue value={r.p_value} significant={r.significant_at_05} strike={r.confounded} />
                      </td>

                      {/* Adjusted — the estimate to read. */}
                      <td className="py-3 pr-3 whitespace-nowrap">
                        {r.is_baseline ? (
                          <span className="dash-muted">—</span>
                        ) : r.adjusted_diff_pp === null ? (
                          <span className="text-xs dash-muted">n/a</span>
                        ) : (
                          <>
                            <Diff value={r.adjusted_diff_pp} bold />
                            <span className="mt-0.5 block text-[10px] dash-muted">
                              {r.strata_compared} mo · {r.time_overlap_pct}% overlap
                            </span>
                          </>
                        )}
                      </td>
                      <td className="py-3">
                        {r.is_baseline ? (
                          <span className="dash-muted">—</span>
                        ) : (
                          <PValue value={r.adjusted_p_value} significant={r.adjusted_significant_at_05} />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <SectionNote>{protocols.note}</SectionNote>
          </>
        )}
      </div>

      {/* ── Donor × Sire matrix ── */}
      <div className="dash-card">
        <div className="flex items-center gap-2">
          <Grid3x3 className="h-4 w-4 dash-muted" />
          <h2 className="text-base font-semibold dash-heading">Donor × Sire</h2>
        </div>

        {!donorSire ? (
          <p className="mt-4 text-sm dash-muted">Loading…</p>
        ) : (
          <>
            <div className="custom-scrollbar mt-4 overflow-x-auto">
              <table className="border-separate border-spacing-1 text-xs">
                <thead>
                  <tr>
                    <th className="sticky left-0 z-10 bg-[var(--card)] pr-2" />
                    {donorSire.sires.map((s) => (
                      <th key={s} className="h-24 w-[52px] align-bottom">
                        <div className="mx-auto w-[52px] whitespace-nowrap text-left font-medium dash-muted [writing-mode:vertical-rl] [transform:rotate(180deg)]">
                          {s.length > 22 ? `${s.slice(0, 21)}…` : s}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {donorSire.donors.map((d) => (
                    <tr key={d}>
                      <th className="sticky left-0 z-10 bg-[var(--card)] pr-3 text-right font-medium dash-heading">
                        {d}
                      </th>
                      {donorSire.sires.map((s) => {
                        const cell = cellFor(d, s);
                        if (!cell) {
                          return (
                            <td key={s} className="h-[52px] w-[52px] rounded-lg bg-[#f6faf7]" />
                          );
                        }
                        const shown = cell.rate_pct !== null;
                        return (
                          <td
                            key={s}
                            title={`${d} × ${s} — ${cell.successes}/${cell.n} pregnant${
                              shown ? ` (${cell.rate_pct}%)` : " · below minimum sample"
                            }`}
                            className="h-[52px] w-[52px] rounded-lg text-center align-middle"
                            style={{ background: shown ? heatColor(cell.rate_pct) : "#EAF1F1" }}
                          >
                            <div
                              className={shown ? "font-semibold" : "dash-muted"}
                              style={shown ? { color: heatInk(cell.rate_pct) } : undefined}
                            >
                              {shown ? `${Math.round(cell.rate_pct!)}%` : "–"}
                            </div>
                            <div
                              className="text-[9px]"
                              style={{ color: shown ? heatInk(cell.rate_pct) : "#3c5a4e" }}
                            >
                              n={cell.n}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 flex items-center gap-3 text-[11px] dash-muted">
              <span>0%</span>
              <div
                className="h-2 w-40 rounded-full"
                style={{ background: "linear-gradient(90deg, #f6f3ec, #d0a45e, #c76a6a)" }}
              />
              <span>60%+</span>
              <span className="ml-3 flex items-center gap-1.5">
                <span className="inline-block h-3 w-3 rounded bg-[#EAF1F1]" /> below minimum sample
              </span>
            </div>
            <SectionNote>{donorSire.note}</SectionNote>
          </>
        )}
      </div>

      {/* ── Outcome factors ── */}
      <div className="dash-card">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-4 w-4 dash-muted" />
          <h2 className="text-base font-semibold dash-heading">Outcome Factors</h2>
        </div>
        <p className="mt-1 text-xs dash-muted">
          Pregnancy rate by embryo and recipient attribute. Factors with no variation in this dataset
          are listed with the reason rather than hidden.
        </p>

        {!factors ? (
          <p className="mt-4 text-sm dash-muted">Loading…</p>
        ) : (
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {factors.factors.map((f) => (
              <div key={f.key} className="dash-tile p-4">
                <h3 className="text-sm font-semibold dash-heading">{f.label}</h3>
                {!f.available ? (
                  <p className="mt-2 text-xs dash-muted">{f.unavailable_reason}</p>
                ) : (
                  <div className="mt-3 space-y-2.5">
                    {f.levels.map((l) => (
                      <div key={l.label} className="grid grid-cols-[7rem_1fr_5.5rem] items-center gap-3">
                        <span className="text-xs dash-heading">{l.label}</span>
                        <IntervalBar cell={l} />
                        <span className="text-right text-xs">
                          <Rate cell={l} />
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        {factors && (
          <SectionNote>
            Bars show the Wilson 95% interval on a shared 0–60% scale; the tick marks the point
            estimate. Overlapping intervals are not evidence of a difference, and none of these
            breakdowns adjust for the others.
          </SectionNote>
        )}
      </div>
    </div>
  );
}
