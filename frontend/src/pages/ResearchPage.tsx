import { useEffect, useState } from "react";
import { FlaskConical, GitCompare, Grid3x3, Info } from "lucide-react";
import api from "@/lib/api";
import type {
  DonorSireResponse,
  OutcomeFactorsResponse,
  ProtocolComparisonResponse,
  RateCell,
} from "@/lib/types";

/** Cream → amber → rose. Deliberately sequential, not diverging: pregnancy
 *  rate has no meaningful midpoint to diverge around. */
function heatColor(pct: number | null): string {
  if (pct === null) return "#f1eee9";
  const t = Math.max(0, Math.min(1, pct / 60));
  const stops: [number, [number, number, number]][] = [
    [0, [246, 243, 236]],
    [0.5, [234, 186, 107]],
    [1, [199, 106, 106]],
  ];
  let [lo, hi] = [stops[0], stops[1]];
  if (t > 0.5) [lo, hi] = [stops[1], stops[2]];
  const f = (t - lo[0]) / (hi[0] - lo[0]);
  const c = lo[1].map((v, i) => Math.round(v + (hi[1][i] - v) * f));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
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
        className="absolute h-1.5 rounded-full bg-[rgba(143,184,222,0.55)]"
        style={{ left: pos(cell.ci_low_pct ?? 0), width: `calc(${pos(cell.ci_high_pct ?? 0)} - ${pos(cell.ci_low_pct ?? 0)})` }}
      />
      <div
        className="absolute top-[-2px] h-[10px] w-[2px] rounded-full bg-[#4d7ba6]"
        style={{ left: pos(cell.rate_pct) }}
      />
    </div>
  );
}

function SectionNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-4 flex items-start gap-2 rounded-xl bg-[#faf9f6] px-3 py-2.5 text-[11px] leading-relaxed dash-muted">
      <Info className="mt-px h-3.5 w-3.5 shrink-0" />
      <span>{children}</span>
    </div>
  );
}

export default function ResearchPage() {
  const [protocols, setProtocols] = useState<ProtocolComparisonResponse | null>(null);
  const [donorSire, setDonorSire] = useState<DonorSireResponse | null>(null);
  const [factors, setFactors] = useState<OutcomeFactorsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<ProtocolComparisonResponse>("/research/protocols"),
      api.get<DonorSireResponse>("/research/donor-sire"),
      api.get<OutcomeFactorsResponse>("/research/outcome-factors"),
    ])
      .then(([p, d, f]) => {
        setProtocols(p.data);
        setDonorSire(d.data);
        setFactors(f.data);
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
        <div className="rounded-2xl border border-[rgba(210,86,79,0.28)] bg-[rgba(231,154,154,0.16)] p-4 text-sm text-[#b8433d]">
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
            <div className="custom-scrollbar mt-4 overflow-x-auto">
              <table className="w-full min-w-[720px] text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide dash-muted">
                    <th className="pb-2 pr-4 font-medium">Protocol</th>
                    <th className="pb-2 pr-4 font-medium">Pregnancy Rate</th>
                    <th className="pb-2 pr-4 font-medium">95% CI</th>
                    <th className="pb-2 pr-4 font-medium">vs Baseline</th>
                    <th className="pb-2 font-medium">p</th>
                  </tr>
                </thead>
                <tbody>
                  {protocols.rows.map((r) => (
                    <tr key={r.protocol_id} className="border-b border-[var(--border)] last:border-0">
                      <td className="py-3 pr-4">
                        <span className="dash-heading">{r.protocol_name}</span>
                        {r.is_baseline && (
                          <span className="ml-2 rounded-full bg-black/[0.05] px-2 py-0.5 text-[10px] font-semibold dash-muted">
                            baseline
                          </span>
                        )}
                      </td>
                      <td className="py-3 pr-4">
                        <Rate cell={r} />
                      </td>
                      <td className="w-40 py-3 pr-4">
                        <IntervalBar cell={r} />
                        {!r.insufficient_data && (
                          <span className="mt-1 block text-[10px] dash-muted">
                            {r.ci_low_pct}–{r.ci_high_pct}%
                          </span>
                        )}
                      </td>
                      <td className="py-3 pr-4">
                        {r.diff_vs_baseline_pp === null ? (
                          <span className="dash-muted">—</span>
                        ) : (
                          <span
                            className={
                              r.diff_vs_baseline_pp > 0 ? "text-[#2f7d5c]" : "text-[#b8433d]"
                            }
                          >
                            {r.diff_vs_baseline_pp > 0 ? "+" : ""}
                            {r.diff_vs_baseline_pp} pp
                          </span>
                        )}
                      </td>
                      <td className="py-3">
                        {r.p_value === null ? (
                          <span className="dash-muted">—</span>
                        ) : (
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                              r.significant_at_05
                                ? "bg-[rgba(234,186,107,0.22)] text-[#a1741c]"
                                : "dash-muted"
                            }`}
                          >
                            {r.p_value < 0.001 ? "<0.001" : r.p_value}
                          </span>
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
                            <td key={s} className="h-[52px] w-[52px] rounded-lg bg-[#faf9f6]" />
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
                            style={{ background: shown ? heatColor(cell.rate_pct) : "#f1eee9" }}
                          >
                            <div className={shown ? "font-semibold text-[#22262a]" : "dash-muted"}>
                              {shown ? `${Math.round(cell.rate_pct!)}%` : "–"}
                            </div>
                            <div className="text-[9px] text-[#5f5540]">n={cell.n}</div>
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
                style={{ background: "linear-gradient(90deg, #f6f3ec, #eaba6b, #c76a6a)" }}
              />
              <span>60%+</span>
              <span className="ml-3 flex items-center gap-1.5">
                <span className="inline-block h-3 w-3 rounded bg-[#f1eee9]" /> below minimum sample
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
