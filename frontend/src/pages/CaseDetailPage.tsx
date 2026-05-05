import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Download, Printer, AlertCircle, CheckCircle } from "lucide-react";

interface CaseDetail {
  id: string;
  transfer_id: string;
  case_date: string;
  outcome: "pregnant" | "open" | "recheck" | "pending";
  
  // Transfer Details
  donor: {
    tag_id: string;
    breed: string;
    birth_weight_epd: number;
  };
  sire: {
    name: string;
    breed: string;
    semen_type: string;
  };
  recipient: {
    tag_id: string;
    farm_location: string;
    cow_or_heifer: string;
  };
  
  // Embryo Info
  embryo_stage: number;
  embryo_grade: string;
  cl_size_mm: number;
  fresh_or_frozen: string;
  
  // Protocol & Staff
  protocol_name: string;
  technician_name: string;
  
  // AI Predictions
  pregnancy_prediction: {
    probability: number;
    confidence_lower: number;
    confidence_upper: number;
    risk_band: string;
    model_version: string;
  };
  grading_prediction: {
    grade: string;
    confidence: number;
    model_version: string;
  };
  
  // QC Analysis
  qc_flags: string[];
  qc_passed: boolean;
  
  // Actual Outcome (if available)
  actual_result: string | null;
  ultrasound_date: string | null;
  follow_up_notes: string;
  
  // Traceability
  audit_trail: Array<{
    timestamp: string;
    action: string;
    user: string;
    details: string;
  }>;
  
  // Linked Cases
  similar_cases: Array<{
    transfer_id: string;
    outcome: string;
    prediction_accuracy: number;
  }>;
}

export default function CaseDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    fetchCaseDetail();
  }, [id]);

  const fetchCaseDetail = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/cases/${id}`);
      setCaseDetail(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load case detail");
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadPDF = async () => {
    try {
      const response = await api.get(`/cases/${id}/download-pdf`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `case-${id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (err) {
      setError("Failed to download PDF");
    }
  };

  const getOutcomeColor = (outcome: string) => {
    switch (outcome) {
      case "pregnant":
        return "bg-green-100 text-green-800";
      case "open":
        return "bg-red-100 text-red-800";
      case "recheck":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getPredictionColor = (prob: number) => {
    if (prob < 0.3) return "text-red-600";
    if (prob < 0.6) return "text-yellow-600";
    return "text-green-600";
  };

  if (loading)
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-600">Loading case details...</p>
      </div>
    );

  if (error)
    return (
      <div className="p-6">
        <Button variant="ghost" onClick={() => navigate("/app/cases")}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Cases
        </Button>
        <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      </div>
    );

  if (!caseDetail)
    return (
      <div className="p-6">
        <Button variant="ghost" onClick={() => navigate("/app/cases")}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Cases
        </Button>
        <p className="text-gray-600">Case not found</p>
      </div>
    );

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Button variant="ghost" onClick={() => navigate("/app/cases")}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Cases
          </Button>
          <h1 className="text-3xl font-bold mt-2">Case #{caseDetail.transfer_id}</h1>
          <p className="text-gray-600">
            {new Date(caseDetail.case_date).toLocaleDateString()} • {caseDetail.protocol_name}
            {" • "}
            {caseDetail.technician_name}
          </p>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={handlePrint}>
            <Printer className="w-4 h-4 mr-2" />
            Print
          </Button>
          <Button onClick={handleDownloadPDF}>
            <Download className="w-4 h-4 mr-2" />
            Download PDF
          </Button>
        </div>
      </div>

      {/* Outcome Badge */}
      <div className="flex gap-2 items-center">
        <span className="text-sm font-medium">Outcome:</span>
        <Badge className={getOutcomeColor(caseDetail.outcome)}>
          {caseDetail.outcome.toUpperCase()}
        </Badge>
        {caseDetail.actual_result && (
          <span className="text-sm text-gray-600">Verified: {caseDetail.actual_result}</span>
        )}
      </div>

      {/* QC Flags Alert */}
      {caseDetail.qc_flags.length > 0 && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-6">
            <div className="flex gap-3">
              <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-yellow-900">QC Flags</p>
                <ul className="text-sm text-yellow-800 mt-1">
                  {caseDetail.qc_flags.map((flag, idx) => (
                    <li key={idx}>• {flag}</li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="genetics">Genetics</TabsTrigger>
          <TabsTrigger value="predictions">Predictions</TabsTrigger>
          <TabsTrigger value="qc">QC Analysis</TabsTrigger>
          <TabsTrigger value="audit">Audit Trail</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Transfer Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <p className="text-gray-600">Transfer ID</p>
                  <p className="font-mono font-bold">{caseDetail.transfer_id}</p>
                </div>
                <div>
                  <p className="text-gray-600">Date</p>
                  <p>{new Date(caseDetail.case_date).toLocaleDateString()}</p>
                </div>
                <div>
                  <p className="text-gray-600">Protocol</p>
                  <p>{caseDetail.protocol_name}</p>
                </div>
                <div>
                  <p className="text-gray-600">Technician</p>
                  <p>{caseDetail.technician_name}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Embryo Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <p className="text-gray-600">Stage</p>
                  <p>{caseDetail.embryo_stage === 7 ? "Blastocyst" : "Day " + caseDetail.embryo_stage}</p>
                </div>
                <div>
                  <p className="text-gray-600">Grade</p>
                  <p className="font-bold">{caseDetail.embryo_grade}</p>
                </div>
                <div>
                  <p className="text-gray-600">CL Size</p>
                  <p>{caseDetail.cl_size_mm} mm</p>
                </div>
                <div>
                  <p className="text-gray-600">Embryo Source</p>
                  <p>{caseDetail.fresh_or_frozen}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Donor</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <p className="text-gray-600">Tag</p>
                  <p className="font-mono">{caseDetail.donor.tag_id}</p>
                </div>
                <div>
                  <p className="text-gray-600">Breed</p>
                  <p>{caseDetail.donor.breed}</p>
                </div>
                <div>
                  <p className="text-gray-600">Birth Weight EPD</p>
                  <p>{caseDetail.donor.birth_weight_epd}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Sire</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <p className="text-gray-600">Name</p>
                  <p className="font-mono">{caseDetail.sire.name}</p>
                </div>
                <div>
                  <p className="text-gray-600">Breed</p>
                  <p>{caseDetail.sire.breed}</p>
                </div>
                <div>
                  <p className="text-gray-600">Semen Type</p>
                  <p>{caseDetail.sire.semen_type}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Recipient</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <p className="text-gray-600">Tag</p>
                  <p className="font-mono">{caseDetail.recipient.tag_id}</p>
                </div>
                <div>
                  <p className="text-gray-600">Type</p>
                  <p>{caseDetail.recipient.cow_or_heifer}</p>
                </div>
                <div>
                  <p className="text-gray-600">Farm</p>
                  <p>{caseDetail.recipient.farm_location}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Genetics Tab */}
        <TabsContent value="genetics">
          <Card>
            <CardHeader>
              <CardTitle>Genetic Information</CardTitle>
              <CardDescription>Detailed genetic and pedigree information</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="p-3 bg-gray-50 rounded">
                  <p className="font-semibold mb-1">Donor Genetics</p>
                  <ul className="space-y-1 text-gray-700">
                    <li>{caseDetail.donor.breed} Breed</li>
                    <li>Birth Weight EPD: {caseDetail.donor.birth_weight_epd}</li>
                  </ul>
                </div>
                <div className="p-3 bg-gray-50 rounded">
                  <p className="font-semibold mb-1">Sire Genetics</p>
                  <ul className="space-y-1 text-gray-700">
                    <li>{caseDetail.sire.breed} Breed</li>
                    <li>Semen Type: {caseDetail.sire.semen_type}</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Predictions Tab */}
        <TabsContent value="predictions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Pregnancy Prediction</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Probability</p>
                  <p className={`text-2xl font-bold ${getPredictionColor(caseDetail.pregnancy_prediction.probability)}`}>
                    {(caseDetail.pregnancy_prediction.probability * 100).toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">95% CI</p>
                  <p className="text-sm font-mono">
                    [{(caseDetail.pregnancy_prediction.confidence_lower * 100).toFixed(1)}% -
                    {(caseDetail.pregnancy_prediction.confidence_upper * 100).toFixed(1)}%]
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Risk Band</p>
                  <p className="font-bold">{caseDetail.pregnancy_prediction.risk_band}</p>
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-600">Model Version: {caseDetail.pregnancy_prediction.model_version}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Embryo Grading Prediction</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Grade</p>
                  <p className="text-xl font-bold">{caseDetail.grading_prediction.grade}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Confidence</p>
                  <p className="text-xl font-bold">{(caseDetail.grading_prediction.confidence * 100).toFixed(0)}%</p>
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-600">Model Version: {caseDetail.grading_prediction.model_version}</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* QC Tab */}
        <TabsContent value="qc">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {caseDetail.qc_passed ? (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-600" />
                )}
                QC Analysis
              </CardTitle>
              <CardDescription>
                {caseDetail.qc_passed ? "Passed all QC checks" : "Failed QC review"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {caseDetail.qc_flags.length > 0 ? (
                <div className="space-y-2">
                  {caseDetail.qc_flags.map((flag, idx) => (
                    <div key={idx} className="p-3 border-l-4 border-yellow-400 bg-yellow-50 rounded">
                      <p className="font-medium">{flag}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-600">No QC flags detected</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit Trail Tab */}
        <TabsContent value="audit">
          <Card>
            <CardHeader>
              <CardTitle>Audit Trail</CardTitle>
              <CardDescription>Complete record of all actions on this case</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {caseDetail.audit_trail.map((entry, idx) => (
                  <div key={idx} className="pb-3 border-b last:border-b-0">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-semibold text-sm">{entry.action}</p>
                        <p className="text-xs text-gray-500">{entry.details}</p>
                      </div>
                      <div className="text-right text-xs text-gray-600">
                        <p>{entry.user}</p>
                        <p>{new Date(entry.timestamp).toLocaleString()}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Similar Cases */}
      {caseDetail.similar_cases.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Similar Cases</CardTitle>
            <CardDescription>Cases with similar characteristics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {caseDetail.similar_cases.map((similar, idx) => (
                <div
                  key={idx}
                  className="p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/app/cases/${similar.transfer_id}`)}
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-semibold">{similar.transfer_id}</p>
                      <Badge className={similar.outcome === "pregnant" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}>
                        {similar.outcome}
                      </Badge>
                    </div>
                    <p className="text-sm">
                      <span className="text-gray-600">Prediction Accuracy: </span>
                      <span className="font-bold">{(similar.prediction_accuracy * 100).toFixed(0)}%</span>
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
