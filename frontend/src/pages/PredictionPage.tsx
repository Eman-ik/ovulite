import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";
import type { PaginatedResponse, Technician, Protocol } from "@/lib/types";
import PredictionAssistantChatbox from "@/components/PredictionAssistantChatbox";
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Minus,
  Sparkles,
  BarChart3,
  AlertCircle,
  ChevronDown,
  Bot,
} from "lucide-react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";

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

/* ─── Styled Select ─────────────────────────────────────── */

function StyledSelect({
  id,
  value,
  onChange,
  children,
}: {
  id: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="pp-select-wrap">
      <select
        id={id}
        value={value}
        onChange={onChange}
        required
        className="pp-select"
      >
        {children}
      </select>
      <ChevronDown className="pp-select-chevron" size={14} />
    </div>
  );
}

/* ─── Animated Counter ──────────────────────────────────── */

function AnimatedNumber({ value, decimals = 1 }: { value: number; decimals?: number }) {
  const [display, setDisplay] = useState(0);
  const frame = useRef<number>(0);

  useEffect(() => {
    const start = display;
    const end = value;
    const duration = 900;
    const startTime = performance.now();

    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(start + (end - start) * eased);
      if (progress < 1) frame.current = requestAnimationFrame(animate);
    };

    frame.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame.current);
  }, [value, display]);

  return <>{display.toFixed(decimals)}</>;
}

/* ─── Floating Particle ─────────────────────────────────── */

function FloatingOrbs() {
  return (
    <div className="pp-orbs" aria-hidden>
      <div className="pp-orb pp-orb-1" />
      <div className="pp-orb pp-orb-2" />
      <div className="pp-orb pp-orb-3" />
    </div>
  );
}

/* ─── Main Component ────────────────────────────────────── */

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
  const [donorBwEpd, setDonorBwEpd] = useState("");
  const [sireBwEpd, setSireBwEpd] = useState("");
  const [customerId, setCustomerId] = useState("");

  // Reference data
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);

  // Results
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [, setModelInfo] = useState<ModelInfo | null>(null);
  const [initLoading, setInitLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [initError, setInitError] = useState("");
  const [resultVisible, setResultVisible] = useState(false);
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);

  const { token } = useAuth();

  // Load reference data and model info. Re-run when auth token changes so
  // protocols/technicians populate after user logs in.
  useEffect(() => {
    let cancelled = false;
    const loadInitialData = async () => {
      setInitLoading(true);
      setInitError("");
      try {
        const [protoRes, techRes, modelRes] = await Promise.all([
          api.get<PaginatedResponse<Protocol>>("/protocols/", { params: { page_size: 50 } }),
          api.get<PaginatedResponse<Technician>>("/technicians/", { params: { page_size: 50 } }),
          api.get<ModelInfo>("/predict/model-info"),
        ]);
        if (cancelled) return;
        setProtocols(Array.isArray(protoRes.data.items) ? protoRes.data.items : []);
        setTechnicians(Array.isArray(techRes.data.items) ? techRes.data.items : []);
        if (isModelInfo(modelRes.data)) {
          setModelInfo(modelRes.data);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        setInitError(err instanceof Error ? err.message : "Failed to load prediction reference data");
      } finally {
        if (!cancelled) setInitLoading(false);
      }
    };
    // Only attempt loading reference data when we have an auth token (or on mount).
    if (token !== null) void loadInitialData();
    return () => { cancelled = true; };
  }, [token]);

  const handlePredict = async () => {
    setError("");

    if (!clMeasure || !clSide || !embryoStage || !embryoGrade || !freshOrFrozen ||
      !protocolName || !technicianName || !donorBreed || !semenType || !heatDay ||
      !bcScore || !daysOpuToEt || !customerId) {
      setError("Please fill in all required fields.");
      return;
    }

    setLoading(true);
    setPrediction(null);
    setResultVisible(false);

    try {
      const payload = {
        cl_measure_mm: parseFloat(clMeasure),
        cl_side: clSide,
        embryo_stage: parseInt(embryoStage),
        embryo_grade: parseInt(embryoGrade),
        fresh_or_frozen: freshOrFrozen,
        protocol_name: protocolName,
        technician_name: technicianName,
        donor_breed: donorBreed,
        semen_type: semenType,
        heat_day: parseInt(heatDay),
        bc_score: parseFloat(bcScore),
        days_opu_to_et: parseInt(daysOpuToEt),
        donor_bw_epd: donorBwEpd ? parseFloat(donorBwEpd) : null,
        sire_bw_epd: sireBwEpd ? parseFloat(sireBwEpd) : null,
        customer_id: customerId,
      };

      const res = await api.post<PredictionResult>("/predict/pregnancy", payload);
      if (!isPredictionResult(res.data)) throw new Error("Prediction response has an unexpected format.");
      setPrediction(res.data);
      setTimeout(() => setResultVisible(true), 50);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message
          : typeof err === "object" && err !== null && "response" in err
            ? ((err as Record<string, Record<string, unknown>>).response?.data as Record<string, string>)?.detail ?? "Prediction failed"
            : "Prediction failed";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  };

  const riskColor =
    prediction?.risk_band === "High"
      ? { bg: "rgba(34,197,94,0.12)", border: "rgba(34,197,94,0.3)", text: "#22c55e" }
      : prediction?.risk_band === "Medium"
        ? { bg: "rgba(245,158,11,0.12)", border: "rgba(245,158,11,0.3)", text: "#f59e0b" }
        : { bg: "rgba(239,68,68,0.12)", border: "rgba(239,68,68,0.3)", text: "#ef4444" };

  return (
    <>
      <style>{`
        .pp-root * { box-sizing: border-box; }
        .pp-root {
          font-family: var(--font-body);
          min-height: 100vh;
          background: transparent;
          color: #1e293b;
          position: relative;
        }

        .pp-orbs { position: absolute; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }
        .pp-orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(80px);
          animation: pp-float linear infinite;
        }
        .pp-orb-1 {
          width: 500px; height: 500px;
          background: radial-gradient(circle, rgba(255,193,7,0.08) 0%, transparent 70%);
          top: -10%; left: -5%;
          animation-duration: 18s;
        }
        .pp-orb-2 {
          width: 400px; height: 400px;
          background: radial-gradient(circle, rgba(250,219,179,0.1) 0%, transparent 70%);
          bottom: 10%; right: -5%;
          animation-duration: 22s; animation-direction: reverse;
        }
        
        @keyframes pp-float {
          0%   { transform: translate(0, 0) scale(1); }
          33%  { transform: translate(30px, -20px) scale(1.05); }
          66%  { transform: translate(-20px, 30px) scale(0.95); }
          100% { transform: translate(0, 0) scale(1); }
        }

        .pp-inner {
          position: relative; z-index: 1;
          max-width: 1400px; margin: 0 auto;
          padding: 0 0 64px;
        }

        .pp-header {
          display: flex; justify-content: space-between;
          align-items: center; gap: 16px;
          margin-bottom: 32px; flex-wrap: wrap;
        }

        .pp-header-icon {
          width: 48px; height: 48px; border-radius: 16px;
          background: linear-gradient(135deg, #FFC107, #FADBB3);
          display: flex; align-items: center; justify-content: center;
          flex-shrink: 0;
          box-shadow: 0 8px 20px rgba(255,193,7,0.2);
        }

        .pp-title {
          font-family: var(--font-display);
          font-size: 36px;
          font-weight: 800; letter-spacing: -0.02em;
          color: #0f172a; line-height: 1.2;
          margin-bottom: 8px;
        }

        .pp-subtitle { font-size: 16px; color: #64748b; }

        @media (min-width: 1024px) {
          .pp-main-container { 
            display: grid;
            grid-template-columns: 1.2fr 1fr; 
            gap: 48px;
            align-items: start;
          }
        }

        .pp-result-display {
          aspect-ratio: 1 / 1;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          border-radius: 32px;
          box-shadow: 0 20px 40px rgba(0,0,0,0.05);
          padding: 48px;
          position: sticky;
          top: 40px;
          text-align: center;
          transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .pp-gauge-label {
          font-size: 14px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 1.5px;
          opacity: 0.7;
          margin-bottom: 12px;
        }

        .pp-gauge-value {
          font-size: 84px;
          font-weight: 800;
          margin: 0;
          line-height: 1;
          letter-spacing: -2px;
        }

        .pp-gauge-status { font-size: 18px; font-weight: 500; margin-top: 16px; }

        .pp-empty-display {
          opacity: 0.5;
          border: 2px dashed rgba(0,0,0,0.1);
          background: transparent;
        }

        .pp-panel {
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 32px; overflow: hidden;
          box-shadow: 0 4px 24px rgba(0,0,0,0.04);
          transition: transform 0.3s ease, box-shadow 0.3s ease;
          display: flex; flex-direction: column;
        }
        .pp-panel:hover { box-shadow: 0 12px 40px rgba(0,0,0,0.08); }

        .pp-panel-header { padding: 32px 32px 16px; }
        .pp-panel-title {
          font-family: var(--font-display);
          font-size: 20px; font-weight: 700;
          color: #0f172a; display: flex; align-items: center; gap: 12px;
        }
        .pp-panel-sub { font-size: 14px; color: #94a3b8; margin-top: 6px; }
        .pp-panel-body { padding: 16px 32px 32px; flex: 1; }

        .pp-form-grid {
          display: grid; grid-template-columns: 1fr; gap: 20px;
        }
        @media (min-width: 640px) { .pp-form-grid { grid-template-columns: repeat(2, 1fr); } }

        .pp-field { display: flex; flex-direction: column; gap: 8px; }
        .pp-label { font-size: 14px; font-weight: 600; color: var(--foreground); opacity: 0.8; }

        .pp-input {
          background: var(--background) !important;
          border: 1px solid var(--border) !important;
          border-radius: 14px !important;
          color: var(--foreground) !important;
          font-size: 16px !important;
          transition: all 0.2s !important;
          height: 52px !important;
          padding: 0 20px !important;
        }
        .pp-input:focus {
          background: white !important;
          border-color: #FFC107 !important;
          box-shadow: 0 0 0 5px rgba(255,193,7,0.12) !important;
          outline: none !important;
        }

        .pp-select-wrap { position: relative; }
        .pp-select {
          width: 100%; appearance: none; background: var(--background);
          border: 1px solid var(--border); border-radius: 14px;
          padding: 0 44px 0 20px; height: 52px; color: var(--foreground);
          font-size: 16px; cursor: pointer; transition: all 0.2s; outline: none;
        }
        .pp-select:focus {
          background: white; border-color: #FFC107;
          box-shadow: 0 0 0 5px rgba(255,193,7,0.12);
        }
        .pp-select-chevron {
          position: absolute; right: 14px; top: 50%;
          transform: translateY(-50%); color: #94a3b8; pointer-events: none;
        }

        .pp-btn {
          width: 100%; background: var(--primary); border: none; border-radius: 16px;
          padding: 16px 24px; font-family: var(--font-display); font-size: 16px; font-weight: 700;
          color: var(--card); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 12px;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
        .pp-btn:hover:not(:disabled) { background: #1e293b; transform: translateY(-2px); box-shadow: 0 15px 30px rgba(0,0,0,0.15); }
        .pp-btn:disabled { opacity: 0.6; cursor: not-allowed; }

        .pp-shap-item { padding: 12px; border-radius: 14px; background: transparent; margin-bottom: 4px; }
        .pp-shap-bar-track { height: 6px; background: #f1f5f9; border-radius: 100px; overflow: hidden; margin-top: 8px; }
        .pp-shap-bar-fill { height: 100%; border-radius: 100px; transition: width 1s cubic-bezier(0.34, 1.56, 0.64, 1); }

        .pp-spinner {
          width: 20px; height: 20px; border: 2px solid rgba(255,255,255,0.3);
          border-top-color: white; border-radius: 50%; animation: pp-spin 0.8s linear infinite;
        }
        @keyframes pp-spin { to { transform: rotate(360deg); } }

        .pp-assistant-trigger {
          position: fixed; bottom: 32px; right: 32px; width: 56px; height: 56px;
          border-radius: 50%; background: #0f172a; color: white; display: flex;
          align-items: center; justify-content: center; cursor: pointer;
          box-shadow: 0 8px 24px rgba(0,0,0,0.2); z-index: 9999;
          transition: all 0.3s; border: 2px solid rgba(255,255,255,0.1);
        }
        .pp-assistant-trigger:hover { transform: scale(1.1); }
        .pp-assistant-popover {
          position: fixed; bottom: 100px; right: 32px; width: 380px; max-height: 600px;
          z-index: 9998; transform-origin: bottom right; animation: pp-pop-in 0.3s ease-out;
        }
        @keyframes pp-pop-in { from { opacity: 0; transform: scale(0.8) translateY(20px); } to { opacity: 1; transform: scale(1) translateY(0); } }
      `}</style>

      <div className="pp-root" style={{ color: 'var(--foreground)' }}>
        <FloatingOrbs />
        <div className="pp-inner">
          <header className="pp-header">
            <div style={{ display: "flex", gap: 16 }}>
              <div className="pp-header-icon" style={{ background: 'var(--primary)' }}>
                <Brain size={24} color="var(--card)" />
              </div>
              <div>
                <h1 className="pp-title" style={{ color: 'var(--foreground)' }}>Pregnancy Prediction</h1>
                <p className="pp-subtitle" style={{ color: 'var(--foreground)', opacity: 0.7 }}>AI-driven analysis for embryo transfer outcomes</p>
              </div>
            </div>
          </header>

          <div className="pp-main-container">
            {/* ── LEFT: Input Form ── */}
            <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 24 }}>
              <div className="pp-panel pp-stagger" style={{ width: "100%" }}>
                <div className="pp-panel-header" style={{ padding: "30px 40px" }}>
                  <div>
                    <div  id="transferFeaturesTitle" className="pp-panel-title" style={{ fontSize: "22px", gap: "12px" }}>
                      <BarChart3 size={24} color="#FFC107" />
                      Transfer Features
                    </div>
                    <p className="pp-panel-sub" style={{ fontSize: "16px" }}>Fill in as many fields as possible for best accuracy</p>
                  </div>
                </div>
                <div className="pp-panel-body" style={{ padding: "0 40px 40px 40px" }}>
                  <div className="pp-form-grid" style={{ gridTemplateColumns: "repeat(2, 1fr)", gap: "25px" }}>
                    {[
                      { id: "cl_measure", label: "CL Measure (mm)", type: "number" as const, step: "0.1", min: "0", max: "50", placeholder: "e.g. 18.5", value: clMeasure, set: setClMeasure },
                      { id: "embryo_stage", label: "Embryo Stage (4-8)", type: "number" as const, min: "1", max: "9", placeholder: "e.g. 6", value: embryoStage, set: setEmbryoStage },
                      { id: "embryo_grade", label: "Embryo Grade (1-4)", type: "number" as const, min: "1", max: "4", placeholder: "e.g. 1", value: embryoGrade, set: setEmbryoGrade },
                      { id: "heat_day", label: "Heat Day", type: "number" as const, placeholder: "e.g. 7", value: heatDay, set: setHeatDay },
                      { id: "bc_score", label: "BC Score", type: "number" as const, step: "0.5", placeholder: "e.g. 3.0", value: bcScore, set: setBcScore },
                      { id: "days_opu", label: "Days OPU → ET", type: "number" as const, placeholder: "e.g. 7", value: daysOpuToEt, set: setDaysOpuToEt },
                      { id: "donor_bw_epd", label: "Donor BW EPD", type: "number" as const, step: "0.01", placeholder: "e.g. 1.25", value: donorBwEpd, set: setDonorBwEpd },
                      { id: "sire_bw_epd", label: "Sire BW EPD", type: "number" as const, step: "0.01", placeholder: "e.g. 2.10", value: sireBwEpd, set: setSireBwEpd },
                      { id: "donor_breed", label: "Donor Breed", type: "text" as const, placeholder: "e.g. Angus", value: donorBreed, set: setDonorBreed },
                      { id: "customer_id", label: "Customer ID", type: "text" as const, placeholder: "e.g. DZF", value: customerId, set: setCustomerId },
                    ].map((f) => (
                      <div key={f.id} className="pp-field">
                        <label htmlFor={f.id} className="pp-label" style={{ fontSize: "16px", marginBottom: "10px", fontWeight: "600" }}>{f.label}</label>
                        <input
                          id={f.id}
                          type={f.type}
                          step={f.step}
                          min={(f as any).min}
                          max={(f as any).max}
                          placeholder={f.placeholder}
                          value={f.value}
                          onChange={(e) => f.set(e.target.value)}
                          className="pp-input"
                          style={{ fontSize: "18px", height: "64px" }}
                          required={!f.id.includes("bw_epd")}
                        />
                      </div>
                    ))}
                    <div className="pp-field">
                      <label htmlFor="cl_side" className="pp-label" style={{ fontSize: "16px", marginBottom: "10px", fontWeight: "600" }}>CL Side</label>
                      <StyledSelect id="cl_side" value={clSide} onChange={e => setClSide(e.target.value)}>
                        <option value="">Unknown</option>
                        <option value="Left">Left</option>
                        <option value="Right">Right</option>
                      </StyledSelect>
                    </div>
                    <div className="pp-field">
                      <label htmlFor="fresh_frozen" className="pp-label" style={{ fontSize: "16px", marginBottom: "10px", fontWeight: "600" }}>Fresh / Frozen</label>
                      <StyledSelect id="fresh_frozen" value={freshOrFrozen} onChange={e => setFreshOrFrozen(e.target.value)}>
                        <option value="Fresh">Fresh</option>
                        <option value="Frozen">Frozen</option>
                      </StyledSelect>
                    </div>
                    <div className="pp-field">
                      <label htmlFor="protocol" className="pp-label" style={{ fontSize: "16px", marginBottom: "10px", fontWeight: "600" }}>Protocol</label>
                      <StyledSelect id="protocol" value={protocolName} onChange={e => setProtocolName(e.target.value)}>
                        {protocols.length === 0 ? (
                          <option value="">No protocols found...</option>
                        ) : (
                          <>
                            <option value="">Select Protocol...</option>
                            {protocols.map(p => <option key={p.protocol_id} value={p.name}>{p.name}</option>)}
                          </>
                        )}
                      </StyledSelect>
                    </div>
                    <div className="pp-field">
                      <label htmlFor="technician" className="pp-label" style={{ fontSize: "16px", marginBottom: "10px", fontWeight: "600" }}>Technician</label>
                      <StyledSelect id="technician" value={technicianName} onChange={e => setTechnicianName(e.target.value)}>
                        {technicians.length === 0 ? (
                          <option value="">No technicians found...</option>
                        ) : (
                          <>
                            <option value="">Select Technician...</option>
                            {technicians.map(t => <option key={t.technician_id} value={t.name}>{t.name}</option>)}
                          </>
                        )}
                      </StyledSelect>
                    </div>
                    <div className="pp-field">
                      <label htmlFor="semen_type" className="pp-label" style={{ fontSize: "16px", marginBottom: "10px", fontWeight: "600" }}>Semen Type</label>
                      <StyledSelect id="semen_type" value={semenType} onChange={e => setSemenType(e.target.value)}>
                        <option value="">Unknown</option>
                        <option value="Conventional">Conventional</option>
                        <option value="Sexed">Sexed</option>
                        <option value="Sexed Female">Sexed Female</option>
                      </StyledSelect>
                    </div>
                  </div>
                </div>
              </div>

              <button
              id="predictBtn"
                className="pp-btn"
                onClick={handlePredict}
                disabled={loading}
                style={{ height: "64px", fontSize: "18px", width: "100%", borderRadius: "16px" }}
              >
                {loading ? <><div className="pp-spinner" /> Analyzing...</> : <><Brain size={22} /> Predict Pregnancy Probability</>}
              </button>

              {error && (
                <div className="pp-error" style={{ display: 'flex', gap: 8, color: '#ef4444', background: 'rgba(239,68,68,0.1)', padding: '12px 16px', borderRadius: 12, fontSize: 14, fontWeight: 500 }}>
                  <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>{error}</span>
                </div>
              )}

              {initLoading && (
                <div className="pp-init-banner" style={{ display: 'flex', gap: 10, alignItems: 'center', background: 'rgba(59,130,246,0.1)', color: '#3b82f6', padding: '12px 16px', borderRadius: 12, fontSize: 13, fontWeight: 600 }}>
                  <div className="pp-spinner" style={{ width: 14, height: 14, borderTopColor: '#3b82f6' }} />
                  Loading laboratory protocols & technicians...
                </div>
              )}

              {initError && (
                <div className="pp-error" style={{ display: 'flex', gap: 8, color: '#ef4444', background: 'rgba(239,68,68,0.1)', padding: '12px 16px', borderRadius: 12, fontSize: 13, fontWeight: 500 }}>
                  <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>{initError}. Please ensure the backend is running and database is initialized.</span>
                </div>
              )}
            </div>

            {/* ── RIGHT: Results Column ── */}
            <div style={{ width: "100%", position: "relative" }}>
              <div style={{ position: "sticky", top: "40px", display: "flex", flexDirection: "column", gap: 24 }}>
                {prediction && resultVisible ? (
                  <div
                    className="pp-panel pp-result-display"
                    style={{
                      background: riskColor.bg,
                      borderColor: riskColor.border,
                      borderWidth: '2px',
                      color: riskColor.text,
                    }}
                  >
                    <span className="pp-gauge-label">Success Probability</span>
                    <h1 className="pp-gauge-value">
                      <AnimatedNumber value={prediction.probability * 100} />%
                    </h1>
                    <div className="pp-gauge-status">{prediction.risk_band} Likelihood</div>
                    <div style={{ marginTop: 24, fontSize: 13, opacity: 0.8, fontWeight: 600 }}>
                      95% Confidence: {(prediction.confidence_lower * 100).toFixed(0)}% – {(prediction.confidence_upper * 100).toFixed(0)}%
                    </div>
                  </div>
                ) : loading ? (
                  <div className="pp-panel pp-result-display" style={{ background: "rgba(255,255,255,0.5)" }}>
                    <div className="pp-spinner" style={{ width: 48, height: 48, borderWidth: 4, borderTopColor: '#FFC107' }} />
                    <p style={{ marginTop: 24, fontWeight: 600, color: "#64748b" }}>Analyzing Laboratory Parameters...</p>
                  </div>
                ) : (
                  <div className="pp-panel pp-result-display pp-empty-display">
                    <div style={{ fontSize: "48px", marginBottom: "20px" }}>🔬</div>
                    <p style={{ fontSize: "18px", fontWeight: "500", color: "#64748b" }}>Enter parameters to generate AI insight</p>
                  </div>
                )}

                {prediction && resultVisible && prediction.shap_explanation.contributions.length > 0 && (
                  <div className="pp-panel" style={{ padding: "24px" }}>
                    <div className="pp-panel-header" style={{ padding: "0 0 16px 0" }}>
                      <div className="pp-panel-title" style={{ fontSize: 16 }}>
                        <BarChart3 size={18} color="#FFC107" />
                        Key Drivers
                      </div>
                    </div>
                    <div className="pp-panel-body" style={{ padding: 0, display: "flex", flexDirection: "column", gap: 10 }}>
                      {prediction.shap_explanation.contributions.slice(0, 10).map((c, i) => {
                        const maxVal = Math.max(...prediction.shap_explanation.contributions.map(x => Math.abs(x.value)));
                        const pct = maxVal > 0 ? Math.abs(c.value) / maxVal : 0;
                        const isPos = c.value > 0;
                        return (
                          <div key={i} className="pp-shap-item">
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, marginBottom: 4 }}>
                              <span style={{ fontSize: 12, fontWeight: 600, color: "#475569" }}>{formatFeatureName(c.feature)}</span>
                              <span style={{ fontSize: 11, fontWeight: 700, color: isPos ? "#10b981" : "#ef4444" }}>
                                {isPos ? "+" : ""}{c.value.toFixed(3)}
                              </span>
                            </div>
                            <div className="pp-shap-bar-track">
                              <div
                                className="pp-shap-bar-fill"
                                style={{
                                  width: `${pct * 100}%`,
                                  background: isPos ? "#10b981" : "#ef4444",
                                  float: isPos ? "left" : "right",
                                }}
                              />
                            </div>
                          </div>
                        );
                      })}
                      <div style={{ display: "flex", gap: 16, marginTop: 12 }}>
                        {[["#10b981", "Increases likelihood"], ["#ef4444", "Decreases likelihood"]].map(([c, l]) => (
                          <span key={l} style={{ fontSize: 11, color: "#94a3b8", display: "flex", alignItems: "center", gap: 6, fontWeight: 500 }}>
                            <span style={{ width: 8, height: 8, borderRadius: "50%", background: c, display: "inline-block" }} />
                            {l}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        className="pp-assistant-trigger"
        onClick={() => setIsAssistantOpen(!isAssistantOpen)}
      >
        {isAssistantOpen ? <Sparkles size={24} /> : <Bot size={24} />}
      </div>

      {isAssistantOpen && (
        <div className="pp-assistant-popover">
          <PredictionAssistantChatbox prediction={prediction} loading={loading} />
        </div>
      )}
    </>
  );
}

/* ─── Guards ─────────────────────────────────────────────── */

function isModelInfo(v: unknown): v is ModelInfo {
  if (!v || typeof v !== "object") return false;
  const x = v as Record<string, unknown>;
  return typeof x.model_name === "string" && typeof x.model_version === "string" && typeof x.n_features === "number";
}

function isPredictionResult(v: unknown): v is PredictionResult {
  if (!v || typeof v !== "object") return false;
  const x = v as Record<string, unknown>;
  if (typeof x.probability !== "number" || typeof x.confidence_lower !== "number" || typeof x.confidence_upper !== "number" || typeof x.risk_band !== "string") return false;
  const shap = x.shap_explanation as Record<string, unknown> | undefined;
  return !!shap && Array.isArray(shap.contributions);
}

/* ─── Helpers ────────────────────────────────────────────── */

function formatFeatureName(name: string): string {
  if (name.includes("__")) {
    const [base, value] = name.split("__");
    const label = base.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    return `${label}: ${value}`;
  }
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace("Cl ", "CL ")
    .replace("Bc ", "BC ")
    .replace("Bw ", "BW ")
    .replace("Opu", "OPU");
}