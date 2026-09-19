import { useEffect, useState } from "react";
import api from "@/lib/api";
import type { Laboratory, PaginatedResponse } from "@/lib/types";

/**
 * Select the site a record belongs to.
 *
 * Replaces the free-text "Farm Location" input that used to appear on the
 * transfer, OPU and recipient forms. That input is why the database ended up
 * treating "DZF", "DZF " and "dzf" as three different places, and why nothing
 * could hang off a site — an address, a contact, a per-site comparison.
 *
 * Only active sites are offered. A record already pointing at a deactivated
 * site keeps showing it, flagged, rather than silently resetting to blank when
 * someone opens the form to edit an unrelated field.
 */
export default function SitePicker({
  value,
  onChange,
  id = "laboratory_id",
  disabled = false,
  legacyText,
}: {
  value: number | null;
  onChange: (laboratoryId: number | null) => void;
  id?: string;
  disabled?: boolean;
  /** The imported free-text location, shown when no site is linked yet. */
  legacyText?: string | null;
}) {
  const [sites, setSites] = useState<Laboratory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<PaginatedResponse<Laboratory>>("/laboratories/", {
        // Inactive sites are included so an existing record's site still
        // resolves to a name; the option itself is disabled below.
        params: { page_size: 100, include_inactive: true },
      })
      .then((r) => {
        if (!cancelled) setSites(r.data.items);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load sites.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selected = sites.find((s) => s.laboratory_id === value);
  const orphanedLegacy = value === null && Boolean(legacyText);

  return (
    <div>
      <select
        id={id}
        value={value ?? ""}
        disabled={disabled || loading || Boolean(error)}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        className="h-10 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-3 text-sm text-[var(--foreground)] disabled:opacity-50"
      >
        <option value="">{loading ? "Loading sites…" : "— No site —"}</option>
        {sites.map((s) => (
          <option key={s.laboratory_id} value={s.laboratory_id} disabled={!s.active}>
            {s.name}
            {s.site_type ? ` · ${s.site_type}` : ""}
            {s.active ? "" : " (inactive)"}
          </option>
        ))}
      </select>

      {error && <p className="mt-1 text-xs text-[#9d3730]">{error}</p>}

      {selected && !selected.active && (
        <p className="mt-1 text-xs text-[#7a5a12]">
          This site is deactivated. It stays on the record until you pick another.
        </p>
      )}

      {orphanedLegacy && (
        <p className="mt-1 text-xs dash-muted">
          Imported location: <span className="font-medium">{legacyText}</span> — pick the matching
          site to link it.
        </p>
      )}
    </div>
  );
}
