import { useState, useEffect } from "react";
import api from "@/lib/api";
import type {
  PaginatedResponse,
  Technician,
  Protocol,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Brain, Info, TrendingUp, TrendingDown, Minus } from "lucide-react";

/* ─── Types ─────────────────────────────────────────────── */

interface ShapContribution {
  feature: string;
  value: number;
}

interface PredictionResult {
  probability: number;
  confidence_lower: number;
  confidence_upper: number;
  risk_band: string;
  model_name: string;
  model_version: string;
  shap_explanation: {
    base_value: number;
    contributions: ShapContribution[];
  };
  prediction_id: number | null;
}

interface ModelInfo {
  model_name: string;
  model_version: string;
  n_features: number;
  best_model_key: string;
  training_split: Record<string, unknown>;
  top_features: [string, number][];
}

/* ─── Component ─────────────────────────────────────────── */

export default function PredictionPage() {
  // Form state
  const [clMeasure, setClMeasure] = useState("");
  const [clSide, setClSide] = useState("");
  const [embryoStage, setEmbryoStage] = useState("");
  const [embryoGrade, setEmbryoGrade] = useState("");
  const [freshOrFrozen, setFreshOrFrozen] = useState("Fresh");
  const [protocolName, setProtocolName] = useState("");
  const [technicianName, setTechnicianName] = useState("");
  const [donorBreed, setDonorBreed] = useState("");
  const [semenType, setSemenType] = useState("");
  const [heatDay, setHeatDay] = useState("");
  const [bcScore, setBcScore] = useState("");
  const [daysOpuToEt, setDaysOpuToEt] = useState("");
  const [customerId, setCustomerId] = useState("");

  // Reference data
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);

  // Results
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load reference data and model info
  useEffect(() => {
    Promise.all([
      api.get<PaginatedResponse<Protocol>>("/protocols/", { params: { page_size: 50 } }),
      api.get<PaginatedResponse<Technician>>("/technicians/", { params: { page_size: 50 } }),
    ]).then(([protoRes, techRes]) => {
      setProtocols(protoRes.data.items);
      setTechnicians(techRes.data.items);
    });

    api
      .get<ModelInfo>("/predict/model-info")
      .then((res) => setModelInfo(res.data))
      .catch(() => {});
  }, []);

  const handlePredict = async () => {
    setError("");
    setLoading(true);
    setPrediction(null);

    try {
      const payload: Record<string, unknown> = {};
      if (clMeasure) payload.cl_measure_mm = parseFloat(clMeasure);
      if (clSide) payload.cl_side = clSide;
      if (embryoStage) payload.embryo_stage = parseInt(embryoStage);
      if (embryoGrade) payload.embryo_grade = parseInt(embryoGrade);
      if (freshOrFrozen) payload.fresh_or_frozen = freshOrFrozen;
      if (protocolName) payload.protocol_name = protocolName;
      if (technicianName) payload.technician_name = technicianName;
      if (donorBreed) payload.donor_breed = donorBreed;
      if (semenType) payload.semen_type = semenType;
      if (heatDay) payload.heat_day = parseInt(heatDay);
      if (bcScore) payload.bc_score = parseFloat(bcScore);
      if (daysOpuToEt) payload.days_opu_to_et = parseInt(daysOpuToEt);
      if (customerId) payload.customer_id = customerId;

      const res = await api.post<PredictionResult>("/predict/pregnancy", payload);
      setPrediction(res.data);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "response" in err
            ? ((err as Record<string, Record<string, unknown>>).response?.data as Record<string, string>)?.detail ?? "Prediction failed"
            : "Prediction failed";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Pregnancy Prediction</h2>
          <p className="text-sm text-muted-foreground">
            Enter transfer details to predict pregnancy probability
          </p>
        </div>
        {modelInfo && (
          <Badge variant="outline" className="text-xs">
            {modelInfo.model_name} ({modelInfo.model_version})
          </Badge>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Input Form - 3 columns */}
        <div className="lg:col-span-3 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Transfer Features</CardTitle>
              <CardDescription>
                Fill in as many fields as possible for best accuracy
              </CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="cl_measure">CL Measure (mm)</Label>
                <Input
                  id="cl_measure"
                  type="number"
                  step="0.1"
                  min="0"
                  max="50"
                  placeholder="e.g. 18.5"
                  value={clMeasure}
                  onChange={(e) => setClMeasure(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cl_side">CL Side</Label>
                <Select
                  id="cl_side"
                  value={clSide}
                  onChange={(e) => setClSide(e.target.value)}
                >
                  <option value="">Unknown</option>
                  <option value="Left">Left</option>
                  <option value="Right">Right</option>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="embryo_stage">Embryo Stage (4-8)</Label>
                <Input
                  id="embryo_stage"
                  type="number"
                  min="1"
                  max="9"
                  value={embryoStage}
                  onChange={(e) => setEmbryoStage(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="embryo_grade">Embryo Grade (1-4)</Label>
                <Input
                  id="embryo_grade"
                  type="number"
                  min="1"
                  max="4"
                  value={embryoGrade}
                  onChange={(e) => setEmbryoGrade(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="fresh_frozen">Fresh / Frozen</Label>
                <Select
                  id="fresh_frozen"
                  value={freshOrFrozen}
                  onChange={(e) => setFreshOrFrozen(e.target.value)}
                >
                  <option value="Fresh">Fresh</option>
                  <option value="Frozen">Frozen</option>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="protocol">Protocol</Label>
                <Select
                  id="protocol"
                  value={protocolName}
                  onChange={(e) => setProtocolName(e.target.value)}
                >
                  <option value="">Select...</option>
                  {protocols.map((p) => (
                    <option key={p.protocol_id} value={p.name}>
                      {p.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="technician">Technician</Label>
                <Select
                  id="technician"
                  value={technicianName}
                  onChange={(e) => setTechnicianName(e.target.value)}
                >
                  <option value="">Select...</option>
                  {technicians.map((t) => (
                    <option key={t.technician_id} value={t.name}>
                      {t.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="semen_type">Semen Type</Label>
                <Select
                  id="semen_type"
                  value={semenType}
                  onChange={(e) => setSemenType(e.target.value)}
                >
                  <option value="">Unknown</option>
                  <option value="Conventional">Conventional</option>
                  <option value="Sexed">Sexed</option>
                  <option value="Sexed Female">Sexed Female</option>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="heat_day">Heat Day</Label>
                <Input
                  id="heat_day"
                  type="number"
                  value={heatDay}
                  onChange={(e) => setHeatDay(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bc_score">BC Score</Label>
                <Input
                  id="bc_score"
                  type="number"
                  step="0.5"
                  value={bcScore}
                  onChange={(e) => setBcScore(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="days_opu">Days OPU → ET</Label>
                <Input
                  id="days_opu"
                  type="number"
                  value={daysOpuToEt}
                  onChange={(e) => setDaysOpuToEt(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="donor_breed">Donor Breed</Label>
                <Input
                  id="donor_breed"
                  value={donorBreed}
                  onChange={(e) => setDonorBreed(e.target.value)}
                  placeholder="e.g. Angus"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="customer_id">Customer</Label>
                <Input
                  id="customer_id"
                  value={customerId}
                  onChange={(e) => setCustomerId(e.target.value)}
                  placeholder="e.g. DZF"
                />
              </div>
            </CardContent>
          </Card>

          <Button
            className="w-full"
            size="lg"
            onClick={handlePredict}
            disabled={loading}
          >
            <Brain className="mr-2 h-5 w-5" />
            {loading ? "Predicting..." : "Predict Pregnancy"}
          </Button>

          {error && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
        </div>

        {/* Results Panel - 2 columns */}
        <div className="lg:col-span-2 space-y-4">
          {prediction ? (
            <>
              {/* Probability Gauge */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Prediction Result</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Big probability number */}
                  <div className="text-center">
                    <div className="text-5xl font-bold tabular-nums">
                      {(prediction.probability * 100).toFixed(1)}%
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      Probability of Pregnancy
                    </p>
                  </div>

                  {/* Risk band badge */}
                  <div className="flex justify-center">
                    <Badge
                      variant={
                        prediction.risk_band === "High"
                          ? "default"
                          : prediction.risk_band === "Medium"
                            ? "secondary"
                            : "outline"
                      }
                      className="text-sm px-4 py-1"
                    >
                      {prediction.risk_band === "High" && <TrendingUp className="mr-1 h-3 w-3" />}
                      {prediction.risk_band === "Medium" && <Minus className="mr-1 h-3 w-3" />}
                      {prediction.risk_band === "Low" && <TrendingDown className="mr-1 h-3 w-3" />}
                      {prediction.risk_band} Likelihood
                    </Badge>
                  </div>

                  {/* Confidence interval bar */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>95% Confidence Interval</span>
                      <span>
                        {(prediction.confidence_lower * 100).toFixed(1)}% –{" "}
                        {(prediction.confidence_upper * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="relative h-3 w-full rounded-full bg-muted overflow-hidden">
                      {/* CI range */}
                      <div
                        className="absolute top-0 h-full bg-primary/30 rounded-full"
                        style={{
                          left: `${prediction.confidence_lower * 100}%`,
                          width: `${(prediction.confidence_upper - prediction.confidence_lower) * 100}%`,
                        }}
                      />
                      {/* Point estimate */}
                      <div
                        className="absolute top-0 h-full w-1 bg-primary rounded-full"
                        style={{ left: `${prediction.probability * 100}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] text-muted-foreground">
                      <span>0%</span>
                      <span>50%</span>
                      <span>100%</span>
                    </div>
                  </div>

                  {/* Model info */}
                  <div className="flex items-center gap-1 text-xs text-muted-foreground pt-2 border-t">
                    <Info className="h-3 w-3" />
                    <span>
                      {prediction.model_name} · {prediction.model_version}
                    </span>
                  </div>
                </CardContent>
              </Card>

              {/* SHAP Explanation */}
              {prediction.shap_explanation.contributions.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Feature Contributions</CardTitle>
                    <CardDescription>
                      How each feature influenced this prediction
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {prediction.shap_explanation.contributions
                        .slice(0, 10)
                        .map((c, i) => {
                          const maxVal = Math.max(
                            ...prediction.shap_explanation.contributions.map((x) =>
                              Math.abs(x.value)
                            )
                          );
                          const pct = maxVal > 0 ? Math.abs(c.value) / maxVal : 0;
                          const isPositive = c.value > 0;

                          return (
                            <div key={i} className="space-y-1">
                              <div className="flex items-center justify-between text-xs">
                                <span className="truncate max-w-[60%]">
                                  {formatFeatureName(c.feature)}
                                </span>
                                <span
                                  className={
                                    isPositive
                                      ? "text-green-600 font-medium"
                                      : "text-red-600 font-medium"
                                  }
                                >
                                  {isPositive ? "+" : ""}
                                  {c.value.toFixed(4)}
                                </span>
                              </div>
                              <div className="relative h-1.5 w-full bg-muted rounded-full overflow-hidden">
                                <div
                                  className={`absolute top-0 h-full rounded-full ${
                                    isPositive ? "bg-green-500" : "bg-red-500"
                                  }`}
                                  style={{
                                    width: `${pct * 100}%`,
                                    [isPositive ? "left" : "right"]: "0",
                                  }}
                                />
                              </div>
                            </div>
                          );
                        })}
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-3">
                      Green = increases pregnancy probability · Red = decreases
                    </p>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card className="flex items-center justify-center min-h-[300px]">
              <CardContent className="text-center text-muted-foreground">
                <Brain className="mx-auto h-12 w-12 opacity-20 mb-3" />
                <p className="text-sm">
                  Fill in the transfer details and click predict to see results
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Helpers ───────────────────────────────────────────── */

function formatFeatureName(name: string): string {
  // Convert "protocol_name__CIDR" → "Protocol: CIDR"
  if (name.includes("__")) {
    const [base, value] = name.split("__");
    const label = base
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
    return `${label}: ${value}`;
  }
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace("Cl ", "CL ")
    .replace("Bc ", "BC ")
    .replace("Bw ", "BW ")
    .replace("Opu", "OPU");
}
