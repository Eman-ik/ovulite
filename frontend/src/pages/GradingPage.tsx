import { useState, useCallback, useRef } from "react";
import api from "@/lib/api";
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
import { Badge } from "@/components/ui/badge";
import { Upload, Microscope, Eye, Loader2 } from "lucide-react";

/* ─── Types ─────────────────────────────────────────────── */

interface GradeProbs {
  Low: number;
  Medium: number;
  High: number;
}

interface GradingResult {
  grade_label: string;
  grade_class: number;
  grade_probabilities: GradeProbs;
  viability_score: number;
  heatmap_base64: string | null;
}

/* ─── Constants ─────────────────────────────────────────── */

const GRADE_COLORS: Record<string, string> = {
  High: "bg-green-500",
  Medium: "bg-yellow-500",
  Low: "bg-red-500",
};

const GRADE_TEXT_COLORS: Record<string, string> = {
  High: "text-green-600",
  Medium: "text-yellow-600",
  Low: "text-red-600",
};

/* ─── Page Component ────────────────────────────────────── */

export default function GradingPage() {
  // Image state
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Metadata state
  const [embryoStage, setEmbryoStage] = useState("");
  const [embryoGrade, setEmbryoGrade] = useState("");
  const [donorBreed, setDonorBreed] = useState("");
  const [freshOrFrozen, setFreshOrFrozen] = useState("");
  const [technicianName, setTechnicianName] = useState("");

  // Result state
  const [result, setResult] = useState<GradingResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Show heatmap toggle
  const [showHeatmap, setShowHeatmap] = useState(false);

  /* ─── File handling ───────────────────────────────── */

  const handleFile = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) {
      setError("Please upload a JPEG or PNG image");
      return;
    }
    setImageFile(file);
    setError(null);
    setResult(null);
    setShowHeatmap(false);

    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target?.result as string);
    reader.readAsDataURL(file);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  /* ─── Submit ──────────────────────────────────────── */

  const handleGrade = async () => {
    if (!imageFile) {
      setError("Please upload an image first");
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("image", imageFile);
    if (embryoStage) formData.append("embryo_stage", embryoStage);
    if (embryoGrade) formData.append("embryo_grade", embryoGrade);
    if (donorBreed) formData.append("donor_breed", donorBreed);
    if (freshOrFrozen) formData.append("fresh_or_frozen", freshOrFrozen);
    if (technicianName) formData.append("technician_name", technicianName);

    try {
      const { data } = await api.post<GradingResult>(
        "/grade/embryo-with-heatmap",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setResult(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Grading failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  /* ─── Reset ───────────────────────────────────────── */

  const handleReset = () => {
    setImageFile(null);
    setImagePreview(null);
    setResult(null);
    setError(null);
    setShowHeatmap(false);
    setEmbryoStage("");
    setEmbryoGrade("");
    setDonorBreed("");
    setFreshOrFrozen("");
    setTechnicianName("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  /* ─── Render ──────────────────────────────────────── */

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-violet-100 rounded-lg">
          <Microscope className="w-6 h-6 text-violet-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Embryo Grading</h1>
          <p className="text-muted-foreground">
            Upload a blastocyst image for AI-powered viability grading
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ─── Left: Upload & Metadata ─── */}
        <div className="space-y-4">
          {/* Drop zone */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Upload Image</CardTitle>
              <CardDescription>
                Drag & drop or click to upload a blastocyst image (JPEG/PNG)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                className={`
                  border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                  transition-colors duration-200
                  ${isDragging ? "border-violet-500 bg-violet-50" : "border-gray-300 hover:border-violet-400"}
                  ${imagePreview ? "border-green-500 bg-green-50/30" : ""}
                `}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleFile(f);
                  }}
                />

                {imagePreview ? (
                  <div className="space-y-3">
                    <img
                      src={showHeatmap && result?.heatmap_base64
                        ? `data:image/jpeg;base64,${result.heatmap_base64}`
                        : imagePreview
                      }
                      alt="Embryo"
                      className="max-h-64 mx-auto rounded-lg shadow-md"
                    />
                    <p className="text-sm text-muted-foreground">
                      {imageFile?.name} ({((imageFile?.size ?? 0) / 1024).toFixed(1)} KB)
                    </p>
                    {result?.heatmap_base64 && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setShowHeatmap(!showHeatmap);
                        }}
                      >
                        <Eye className="w-4 h-4 mr-2" />
                        {showHeatmap ? "Show Original" : "Show Grad-CAM"}
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Upload className="w-12 h-12 mx-auto text-gray-400" />
                    <p className="font-medium">Drop image here or click to browse</p>
                    <p className="text-sm text-muted-foreground">
                      JPEG or PNG, max 10MB
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Metadata form */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Metadata (Optional)</CardTitle>
              <CardDescription>
                Providing embryo metadata improves grading accuracy
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="stage">Embryo Stage</Label>
                  <Select
                    id="stage"
                    value={embryoStage}
                    onChange={(e) => setEmbryoStage(e.target.value)}
                  >
                    <option value="">Select...</option>
                    {[4, 5, 6, 7, 8].map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="grade">Manual Grade</Label>
                  <Select
                    id="grade"
                    value={embryoGrade}
                    onChange={(e) => setEmbryoGrade(e.target.value)}
                  >
                    <option value="">Select...</option>
                    {[1, 2, 3, 4].map((g) => (
                      <option key={g} value={g}>{g}</option>
                    ))}
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="breed">Donor Breed</Label>
                <Input
                  id="breed"
                  placeholder="e.g. Holstein, Sahiwal"
                  value={donorBreed}
                  onChange={(e) => setDonorBreed(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="ff">Fresh or Frozen</Label>
                  <Select
                    id="ff"
                    value={freshOrFrozen}
                    onChange={(e) => setFreshOrFrozen(e.target.value)}
                  >
                    <option value="">Select...</option>
                    <option value="Fresh">Fresh</option>
                    <option value="Frozen">Frozen</option>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tech">Technician</Label>
                  <Input
                    id="tech"
                    placeholder="Name"
                    value={technicianName}
                    onChange={(e) => setTechnicianName(e.target.value)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex gap-3">
            <Button
              className="flex-1"
              onClick={handleGrade}
              disabled={!imageFile || loading}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Microscope className="w-4 h-4 mr-2" />
                  Grade Embryo
                </>
              )}
            </Button>
            <Button variant="outline" onClick={handleReset}>
              Reset
            </Button>
          </div>

          {error && (
            <div className="bg-red-50 text-red-700 p-3 rounded-md text-sm">
              {error}
            </div>
          )}
        </div>

        {/* ─── Right: Results ─── */}
        <div className="space-y-4">
          {result ? (
            <>
              {/* Grade badge */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Grading Result</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <p className="text-sm text-muted-foreground">Viability Grade</p>
                      <p className={`text-3xl font-bold ${GRADE_TEXT_COLORS[result.grade_label]}`}>
                        {result.grade_label}
                      </p>
                    </div>
                    <Badge
                      className={`text-white text-lg px-4 py-2 ${GRADE_COLORS[result.grade_label]}`}
                    >
                      {result.grade_label} Viability
                    </Badge>
                  </div>

                  {/* Viability score gauge */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Viability Score</span>
                      <span className="font-mono font-semibold">
                        {(result.viability_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-1000 ease-out ${
                          result.viability_score >= 0.6
                            ? "bg-green-500"
                            : result.viability_score >= 0.35
                            ? "bg-yellow-500"
                            : "bg-red-500"
                        }`}
                        style={{ width: `${result.viability_score * 100}%` }}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Grade probabilities */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Class Probabilities</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {(["High", "Medium", "Low"] as const).map((grade) => {
                    const prob = result.grade_probabilities[grade];
                    return (
                      <div key={grade} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className={GRADE_TEXT_COLORS[grade]}>{grade}</span>
                          <span className="font-mono">{(prob * 100).toFixed(1)}%</span>
                        </div>
                        <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-700 ${GRADE_COLORS[grade]}`}
                            style={{ width: `${prob * 100}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </CardContent>
              </Card>

              {/* Grad-CAM heatmap */}
              {result.heatmap_base64 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Eye className="w-5 h-5" />
                      Grad-CAM Heatmap
                    </CardTitle>
                    <CardDescription>
                      Highlights regions that influenced the grade prediction
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <img
                      src={`data:image/jpeg;base64,${result.heatmap_base64}`}
                      alt="Grad-CAM heatmap"
                      className="rounded-lg shadow-md w-full max-w-sm mx-auto"
                    />
                    <p className="text-xs text-muted-foreground mt-2 text-center">
                      Red/warm areas = high influence on grade prediction
                    </p>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card className="h-full flex items-center justify-center min-h-[300px]">
              <CardContent className="text-center text-muted-foreground py-16">
                <Microscope className="w-16 h-16 mx-auto mb-4 opacity-20" />
                <p className="text-lg font-medium">No result yet</p>
                <p className="text-sm mt-1">
                  Upload an embryo image and click "Grade Embryo" to see the AI assessment
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
