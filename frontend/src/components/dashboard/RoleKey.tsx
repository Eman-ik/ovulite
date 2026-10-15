import { ROLE, type Role } from "@/lib/chartPalette";

/**
 * Legend for a chart whose colours carry meaning. Each swatch is drawn exactly as the
 * chart draws its role, including the outline and the dashed outline for pending.
 */
export default function RoleKey({ items }: { items: { role: Role; label: string }[] }) {
  return (
    <ul className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs dash-muted" aria-label="Legend">
      {items.map(({ role, label }) => {
        const r = ROLE[role];
        return (
          <li key={role} className="inline-flex items-center gap-1.5">
            <span
              aria-hidden
              className="inline-block h-3 w-3 rounded-[3px]"
              style={{
                background: r.fill,
                border: `1.25px ${r.dash ? "dashed" : "solid"} ${r.stroke ?? "transparent"}`,
              }}
            />
            <span className="dash-heading">{label}</span>
          </li>
        );
      })}
    </ul>
  );
}
