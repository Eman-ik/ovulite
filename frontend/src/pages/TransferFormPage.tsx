import { useState, useEffect, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "@/lib/api";
import type {
  PaginatedResponse,
  Donor,
  Sire,
  Recipient,
  Technician,
  Protocol,
  ETTransferDetail,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ArrowLeft, Save } from "lucide-react";

interface FormData {
  et_number: string;
  et_date: string;
  customer_id: string;
  farm_location: string;
  recipient_id: string;
  bc_score: string;
  cl_side: string;
  cl_measure_mm: string;
  protocol_id: string;
  heat_observed: string;
  heat_day: string;
  donor_id: string;
  sire_id: string;
  embryo_stage: string;
  embryo_grade: string;
  fresh_or_frozen: string;
  opu_date: string;
  cane_number: string;
  technician_id: string;
  assistant_name: string;
  pc1_date: string;
  pc1_result: string;
}

const emptyForm: FormData = {
  et_number: "",
  et_date: "",
  customer_id: "",
  farm_location: "",
  recipient_id: "",
  bc_score: "",
  cl_side: "",
  cl_measure_mm: "",
  protocol_id: "",
  heat_observed: "",
  heat_day: "",
  donor_id: "",
  sire_id: "",
  embryo_stage: "",
  embryo_grade: "",
  fresh_or_frozen: "Fresh",
  opu_date: "",
  cane_number: "",
  technician_id: "",
  assistant_name: "",
  pc1_date: "",
  pc1_result: "",
};

export default function TransferFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = id && id !== "new";

  const [form, setForm] = useState<FormData>(emptyForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  // Reference data
  const [donors, setDonors] = useState<Donor[]>([]);
  const [sires, setSires] = useState<Sire[]>([]);
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [protocols, setProtocols] = useState<Protocol[]>([]);

  // Load reference data
  useEffect(() => {
    Promise.all([
      api.get<PaginatedResponse<Donor>>("/donors/", {
        params: { page_size: 100 },
      }),
      api.get<PaginatedResponse<Sire>>("/sires/", {
        params: { page_size: 100 },
      }),
      api.get<PaginatedResponse<Recipient>>("/recipients/", {
        params: { page_size: 100 },
      }),
      api.get<PaginatedResponse<Technician>>("/technicians/", {
        params: { page_size: 100 },
      }),
      api.get<PaginatedResponse<Protocol>>("/protocols/", {
        params: { page_size: 100 },
      }),
    ]).then(([donorRes, sireRes, recipRes, techRes, protoRes]) => {
      setDonors(donorRes.data.items);
      setSires(sireRes.data.items);
      setRecipients(recipRes.data.items);
      setTechnicians(techRes.data.items);
      setProtocols(protoRes.data.items);
    });
  }, []);

  // Load existing record for edit
  useEffect(() => {
    if (isEdit) {
      api.get<ETTransferDetail>(`/transfers/${id}`).then((res) => {
        const t = res.data;
        setForm({
          et_number: t.et_number?.toString() ?? "",
          et_date: t.et_date ?? "",
          customer_id: t.customer_id ?? "",
          farm_location: t.farm_location ?? "",
          recipient_id: t.recipient_id?.toString() ?? "",
          bc_score: t.bc_score?.toString() ?? "",
          cl_side: t.cl_side ?? "",
          cl_measure_mm: t.cl_measure_mm?.toString() ?? "",
          protocol_id: t.protocol_id?.toString() ?? "",
          heat_observed:
            t.heat_observed === null ? "" : t.heat_observed ? "true" : "false",
          heat_day: t.heat_day?.toString() ?? "",
          donor_id: "", // not directly on transfer
          sire_id: "",
          embryo_stage: t.embryo_stage?.toString() ?? "",
          embryo_grade: t.embryo_grade?.toString() ?? "",
          fresh_or_frozen: t.fresh_or_frozen ?? "Fresh",
          opu_date: "",
          cane_number: "",
          technician_id: t.technician_id?.toString() ?? "",
          assistant_name: t.assistant_name ?? "",
          pc1_date: t.pc1_date ?? "",
          pc1_result: t.pc1_result ?? "",
        });
      });
    }
  }, [id, isEdit]);

  const set = (field: keyof FormData) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSaving(true);

    try {
      // Validate required fields
      if (!form.et_date) {
        setError("ET Date is required");
        setSaving(false);
        return;
      }

      if (form.cl_measure_mm) {
        const cl = parseFloat(form.cl_measure_mm);
        if (isNaN(cl) || cl < 0 || cl > 50) {
          setError("CL measure must be between 0 and 50 mm");
          setSaving(false);
          return;
        }
      }

      // First create embryo if we have embryo data
      let embryo_id: number | undefined;
      if (form.embryo_stage || form.embryo_grade) {
        const embryoPayload: Record<string, unknown> = {};
        if (form.donor_id) embryoPayload.donor_id = parseInt(form.donor_id);
        if (form.sire_id) embryoPayload.sire_id = parseInt(form.sire_id);
        if (form.opu_date) embryoPayload.opu_date = form.opu_date;
        if (form.embryo_stage)
          embryoPayload.stage = parseInt(form.embryo_stage);
        if (form.embryo_grade)
          embryoPayload.grade = parseInt(form.embryo_grade);
        embryoPayload.fresh_or_frozen = form.fresh_or_frozen || null;
        if (form.cane_number) embryoPayload.cane_number = form.cane_number;

        const embryoRes = await api.post<{ embryo_id: number }>(
          "/embryos/",
          embryoPayload
        );
        embryo_id = embryoRes.data.embryo_id;
      }

      // Build transfer payload
      const payload: Record<string, unknown> = {
        et_date: form.et_date,
      };
      if (form.et_number) payload.et_number = parseInt(form.et_number);
      if (form.customer_id) payload.customer_id = form.customer_id;
      if (form.farm_location) payload.farm_location = form.farm_location;
      if (form.recipient_id)
        payload.recipient_id = parseInt(form.recipient_id);
      if (form.bc_score) payload.bc_score = parseFloat(form.bc_score);
      if (form.cl_side) payload.cl_side = form.cl_side;
      if (form.cl_measure_mm)
        payload.cl_measure_mm = parseFloat(form.cl_measure_mm);
      if (form.protocol_id) payload.protocol_id = parseInt(form.protocol_id);
      if (form.heat_observed)
        payload.heat_observed = form.heat_observed === "true";
      if (form.heat_day) payload.heat_day = parseInt(form.heat_day);
      if (embryo_id) payload.embryo_id = embryo_id;
      if (form.technician_id)
        payload.technician_id = parseInt(form.technician_id);
      if (form.assistant_name) payload.assistant_name = form.assistant_name;
      if (form.pc1_date) payload.pc1_date = form.pc1_date;
      if (form.pc1_result) payload.pc1_result = form.pc1_result;

      if (isEdit) {
        await api.put(`/transfers/${id}`, payload);
      } else {
        await api.post("/transfers/", payload);
      }

      navigate("/data-entry");
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : typeof err === "object" &&
              err !== null &&
              "response" in err
            ? ((err as Record<string, Record<string, unknown>>).response
                ?.data as Record<string, string>)?.detail ?? "Save failed"
            : "Save failed";
      setError(String(msg));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate("/data-entry")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <h2 className="text-2xl font-bold">
          {isEdit ? "Edit Transfer" : "New ET Transfer"}
        </h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Transfer Info */}
        <Card>
          <CardHeader>
            <CardTitle>Transfer Information</CardTitle>
            <CardDescription>Basic ET transfer details</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="et_number">ET Number</Label>
              <Input
                id="et_number"
                type="number"
                value={form.et_number}
                onChange={set("et_number")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="et_date">
                ET Date <span className="text-destructive">*</span>
              </Label>
              <Input
                id="et_date"
                type="date"
                required
                value={form.et_date}
                onChange={set("et_date")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="customer_id">Customer</Label>
              <Input
                id="customer_id"
                value={form.customer_id}
                onChange={set("customer_id")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="farm_location">Farm Location</Label>
              <Input
                id="farm_location"
                value={form.farm_location}
                onChange={set("farm_location")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="technician_id">Technician</Label>
              <Select
                id="technician_id"
                value={form.technician_id}
                onChange={set("technician_id")}
              >
                <option value="">Select...</option>
                {technicians.map((t) => (
                  <option key={t.technician_id} value={t.technician_id}>
                    {t.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="assistant_name">Assistant</Label>
              <Input
                id="assistant_name"
                value={form.assistant_name}
                onChange={set("assistant_name")}
              />
            </div>
          </CardContent>
        </Card>

        {/* Recipient & CL */}
        <Card>
          <CardHeader>
            <CardTitle>Recipient & Corpus Luteum</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="recipient_id">Recipient</Label>
              <Select
                id="recipient_id"
                value={form.recipient_id}
                onChange={set("recipient_id")}
              >
                <option value="">Select...</option>
                {recipients.map((r) => (
                  <option key={r.recipient_id} value={r.recipient_id}>
                    {r.tag_id}
                    {r.farm_location ? ` (${r.farm_location})` : ""}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="bc_score">BC Score</Label>
              <Input
                id="bc_score"
                type="number"
                step="0.5"
                value={form.bc_score}
                onChange={set("bc_score")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cl_side">CL Side</Label>
              <Select
                id="cl_side"
                value={form.cl_side}
                onChange={set("cl_side")}
              >
                <option value="">Select...</option>
                <option value="Left">Left</option>
                <option value="Right">Right</option>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="cl_measure_mm">CL Measure (mm)</Label>
              <Input
                id="cl_measure_mm"
                type="number"
                step="0.1"
                min="0"
                max="50"
                value={form.cl_measure_mm}
                onChange={set("cl_measure_mm")}
                placeholder="10-30 typical"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="protocol_id">Protocol</Label>
              <Select
                id="protocol_id"
                value={form.protocol_id}
                onChange={set("protocol_id")}
              >
                <option value="">Select...</option>
                {protocols.map((p) => (
                  <option key={p.protocol_id} value={p.protocol_id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="heat_observed">Heat Observed</Label>
              <Select
                id="heat_observed"
                value={form.heat_observed}
                onChange={set("heat_observed")}
              >
                <option value="">Unknown</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="heat_day">Heat Day</Label>
              <Input
                id="heat_day"
                type="number"
                value={form.heat_day}
                onChange={set("heat_day")}
              />
            </div>
          </CardContent>
        </Card>

        {/* Embryo Info */}
        <Card>
          <CardHeader>
            <CardTitle>Embryo Information</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="donor_id">Donor</Label>
              <Select
                id="donor_id"
                value={form.donor_id}
                onChange={set("donor_id")}
              >
                <option value="">Select...</option>
                {donors.map((d) => (
                  <option key={d.donor_id} value={d.donor_id}>
                    {d.tag_id}
                    {d.breed ? ` (${d.breed})` : ""}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="sire_id">Sire</Label>
              <Select
                id="sire_id"
                value={form.sire_id}
                onChange={set("sire_id")}
              >
                <option value="">Select...</option>
                {sires.map((s) => (
                  <option key={s.sire_id} value={s.sire_id}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="opu_date">OPU Date</Label>
              <Input
                id="opu_date"
                type="date"
                value={form.opu_date}
                onChange={set("opu_date")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="embryo_stage">Embryo Stage (4-8)</Label>
              <Input
                id="embryo_stage"
                type="number"
                min="1"
                max="9"
                value={form.embryo_stage}
                onChange={set("embryo_stage")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="embryo_grade">Embryo Grade (1-4)</Label>
              <Input
                id="embryo_grade"
                type="number"
                min="1"
                max="4"
                value={form.embryo_grade}
                onChange={set("embryo_grade")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="fresh_or_frozen">Fresh / Frozen</Label>
              <Select
                id="fresh_or_frozen"
                value={form.fresh_or_frozen}
                onChange={set("fresh_or_frozen")}
              >
                <option value="Fresh">Fresh</option>
                <option value="Frozen">Frozen</option>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="cane_number">Cane Number</Label>
              <Input
                id="cane_number"
                value={form.cane_number}
                onChange={set("cane_number")}
                placeholder="If frozen"
              />
            </div>
          </CardContent>
        </Card>

        {/* Outcome */}
        <Card>
          <CardHeader>
            <CardTitle>Pregnancy Check (Outcome)</CardTitle>
            <CardDescription>
              Only fill after pregnancy check is performed
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="pc1_date">1st PC Date</Label>
              <Input
                id="pc1_date"
                type="date"
                value={form.pc1_date}
                onChange={set("pc1_date")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pc1_result">1st PC Result</Label>
              <Select
                id="pc1_result"
                value={form.pc1_result}
                onChange={set("pc1_result")}
              >
                <option value="">Not checked yet</option>
                <option value="Pregnant">Pregnant</option>
                <option value="Open">Open</option>
                <option value="Recheck">Recheck</option>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Error + Submit */}
        {error && (
          <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}
        <div className="flex justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate("/data-entry")}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            <Save className="mr-2 h-4 w-4" />
            {saving ? "Saving..." : isEdit ? "Update Transfer" : "Create Transfer"}
          </Button>
        </div>
      </form>
    </div>
  );
}
