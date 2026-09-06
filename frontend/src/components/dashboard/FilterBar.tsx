import type { DashboardFilterOptions, DashboardFilterValues } from "@/lib/types";
import { Select } from "@/components/ui/select";
import { Label } from "@/components/ui/label";

type FilterBarProps = {
  filters: DashboardFilterValues;
  options: DashboardFilterOptions | null;
  onChange: (next: DashboardFilterValues) => void;
  visibleFields?: Array<keyof DashboardFilterValues>;
};

const ALL_FIELDS: Array<keyof DashboardFilterValues> = [
  "date_from",
  "date_to",
  "farm_location",
  "breed",
  "donor_id",
  "sire_id",
  "embryologist_id",
  "technician_id",
  "protocol_id",
  "fresh_or_frozen",
];

export default function FilterBar({ filters, options, onChange, visibleFields }: FilterBarProps) {
  const visible = new Set(visibleFields ?? ALL_FIELDS);

  const set = (patch: Partial<DashboardFilterValues>) => onChange({ ...filters, ...patch });

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-2xl border border-emerald-50 bg-white p-4 shadow-sm">
      {visible.has("date_from") && (
        <div className="flex flex-col gap-1">
          <Label className="text-xs text-gray-500">From</Label>
          <input
            type="date"
            value={filters.date_from ?? ""}
            onChange={(e) => set({ date_from: e.target.value || undefined })}
            className="h-9 rounded-lg border border-gray-200 px-2 text-sm"
          />
        </div>
      )}
      {visible.has("date_to") && (
        <div className="flex flex-col gap-1">
          <Label className="text-xs text-gray-500">To</Label>
          <input
            type="date"
            value={filters.date_to ?? ""}
            onChange={(e) => set({ date_to: e.target.value || undefined })}
            className="h-9 rounded-lg border border-gray-200 px-2 text-sm"
          />
        </div>
      )}
      {visible.has("farm_location") && (
        <div className="flex flex-col gap-1">
          <Label className="text-xs text-gray-500">Farm</Label>
          <Select
            value={filters.farm_location ?? ""}
            onChange={(e) => set({ farm_location: e.target.value || undefined })}
            className="min-w-[140px] bg-white text-gray-800"
          >
            <option value="">All Farms</option>
            {options?.farm_locations.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </Select>
        </div>
      )}
      {visible.has("breed") && (
        <div className="flex flex-col gap-1">
          <Label className="text-xs text-gray-500">Breed</Label>
          <Select
            value={filters.breed ?? ""}
            onChange={(e) => set({ breed: e.target.value || undefined })}
            className="min-w-[120px] bg-white text-gray-800"
          >
            <option value="">All Breeds</option>
            {options?.breeds.map((b) => (
              <option key={b} value={b}>{b}</option>
            ))}
          </Select>
        </div>
      )}
      {visible.has("donor_id") && (
        <div className="flex flex-col gap-1">
          <Label className="text-xs text-gray-500">Donor</Label>
          <Select
            value={filters.donor_id ?? ""}
            onChange={(e) => set({ donor_id: e.target.value ? Number(e.target.value) : undefined })}
            className="min-w-[120px] bg-white text-gray-800"
          >
            <option value="">All Donors</option>
            {options?.donors.map((d) => (
              <option key={d.id} value={d.id}>{d.label}</option>
            ))}
          </Select>
        </div>
      )}
      {visible.has("sire_id") && (
        <div className="flex flex-col gap-1">
          <Label className="text-xs text-gray-500">Sire</Label>
          <Select
            value={filters.sire_id ?? ""}
            onChange={(e) => set({ sire_id: e.target.value ? Number(e.target.value) : undefined })}
            className="min-w-[140px] bg-white text-gray-800"
          >
            <option value="">All Sires</option>
            {options?.sires.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </Select>
        </div>
      )}
      {visible.has("embryologist_id") && (
        <div className="flex flex-col gap-1">
          <Label className="text-xs text-gray-500">Embryologist</Label>
          <Select
            value={filters.embryologist_id ?? ""}
            onChange={(e) => set({ embryologist_id: e.target.value ? Number(e.target.value) : undefined })}
            className="min-w-[140px] bg-white text-gray-800"
          >
            <option value="">All Embryologists</option>
            {options?.technicians.map((t) => (
              <option key={t.id} value={t.id}>{t.label}</option>
            ))}
          </Select>
        </div>
      )}
      {visible.has("technician_id") && (
        <div className="flex flex-col gap-1">
          <Label className="text-xs text-gray-500">ET Technician</Label>
          <Select
            value={filters.technician_id ?? ""}
            onChange={(e) => set({ technician_id: e.target.value ? Number(e.target.value) : undefined })}
            className="min-w-[140px] bg-white text-gray-800"
          >
            <option value="">All Technicians</option>
            {options?.technicians.map((t) => (
              <option key={t.id} value={t.id}>{t.label}</option>
            ))}
          </Select>
        </div>
      )}
      {visible.has("protocol_id") && (
        <div className="flex flex-col gap-1">
          <Label className="text-xs text-gray-500">Protocol</Label>
          <Select
            value={filters.protocol_id ?? ""}
            onChange={(e) => set({ protocol_id: e.target.value ? Number(e.target.value) : undefined })}
            className="min-w-[160px] bg-white text-gray-800"
          >
            <option value="">All Protocols</option>
            {options?.protocols.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </Select>
        </div>
      )}
      {visible.has("fresh_or_frozen") && (
        <div className="flex flex-col gap-1">
          <Label className="text-xs text-gray-500">Fresh/Frozen</Label>
          <Select
            value={filters.fresh_or_frozen ?? ""}
            onChange={(e) => set({ fresh_or_frozen: e.target.value || undefined })}
            className="min-w-[120px] bg-white text-gray-800"
          >
            <option value="">Both</option>
            {options?.fresh_or_frozen.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </Select>
        </div>
      )}
      <button
        onClick={() => onChange({})}
        className="h-9 rounded-lg border border-gray-200 px-3 text-xs font-medium text-gray-600 hover:bg-gray-50"
      >
        Clear filters
      </button>
    </div>
  );
}
