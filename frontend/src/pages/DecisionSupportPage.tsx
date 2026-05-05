import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, CheckCircle, AlertTriangle, Lightbulb, ThumbsUp } from "lucide-react";

interface DecisionSupportEntry {
  id: string;
  transfer_id: string;
  prediction_probability: number;
  confidence_lower: number;
  confidence_upper: number;
  risk_band: string;
  recommendation: string;
  clinical_considerations: string[];
  alternative_protocols: string[];
  success_factors: string[];
  risk_factors: string[];
  previous_outcomes: {
    success_count: number;
    fail_count: number;
    success_rate: number;
  };
  technician_history: {
    transfers_performed: number;
    success_rate: number;
  };
  protocol_history: {
    transfers_performed: number;
    success_rate: number;
  };
  similar_cases: Array<{
    case_id: string;
    similarity_score: number;
    outcome: "success" | "failure";
  }>;
}

export default function DecisionSupportPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [support, setSupport] = useState<DecisionSupportEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userDecision, setUserDecision] = useState<"accept" | "review" | "reject" | null>(null);
  const [notes, setNotes] = useState("");

  // Fetch decision support data
  useEffect(() => {
    const fetchDecisionSupport = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/predictions/${id}/decision-support`);
        setSupport(response.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load decision support");
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchDecisionSupport();
    }
  }, [id]);

  const handleRecordDecision = async () => {
    if (!userDecision || !id) return;

    try {
      await api.post(`/predictions/${id}/decision`, {
        decision: userDecision,
        notes,
      });
      navigate("/app/predictions");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record decision");
    }
  };

  const getRiskColor = (riskBand: string) => {
    if (riskBand.includes("Low")) return "text-green-600";
    if (riskBand.includes("Medium")) return "text-yellow-600";
    return "text-red-600";
  };

  const getProbabilityColor = (prob: number) => {
    if (prob < 0.3) return "bg-red-100 text-red-800";
    if (prob < 0.6) return "bg-yellow-100 text-yellow-800";
    return "bg-green-100 text-green-800";
  };

  if (loading)
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-600">Loading decision support...</p>
      </div>
    );

  if (error)
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      </div>
    );

  if (!support)
    return (
      <div className="p-6">
        <p className="text-gray-600">Decision support data not found</p>
      </div>
    );

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Decision Support</h1>
        <p className="text-gray-600">Transfer ID: {support.transfer_id}</p>
      </div>

      {/* Prediction Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="w-5 h-5" />
            Prediction Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-gray-600">Pregnancy Probability</p>
              <p className={`text-2xl font-bold ${getProbabilityColor(support.prediction_probability)}`}>
                {(support.prediction_probability * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Confidence Interval (95%)</p>
              <p className="text-sm font-mono">
                [{(support.confidence_lower * 100).toFixed(1)}% - {(support.confidence_upper * 100).toFixed(1)}%]
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Risk Band</p>
              <p className={`font-bold ${getRiskColor(support.risk_band)}`}>{support.risk_band}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Primary Recommendation */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-blue-600" />
            Primary Recommendation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-lg">{support.recommendation}</p>
        </CardContent>
      </Card>

      {/* Success Factors */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ThumbsUp className="w-5 h-5 text-green-600" />
            Success Factors ({support.success_factors.length})
          </CardTitle>
          <CardDescription>Conditions that favor successful pregnancy outcome</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {support.success_factors.map((factor, idx) => (
              <li key={idx} className="flex items-start gap-3">
                <span className="text-green-600 font-bold">✓</span>
                <span>{factor}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* Risk Factors */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            Risk Factors ({support.risk_factors.length})
          </CardTitle>
          <CardDescription>Conditions that may impact outcome</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {support.risk_factors.map((factor, idx) => (
              <li key={idx} className="flex items-start gap-3">
                <span className="text-yellow-600 font-bold">⚠</span>
                <span>{factor}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* Clinical Considerations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            Clinical Considerations
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {support.clinical_considerations.map((consideration, idx) => (
              <li key={idx} className="flex gap-2 text-sm">
                <span className="text-blue-600">•</span>
                <span>{consideration}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* Performance Context */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Technician History */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Technician Track Record</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <p className="text-xs text-gray-600">Transfers Performed</p>
              <p className="text-2xl font-bold">{support.technician_history.transfers_performed}</p>
            </div>
            <div>
              <p className="text-xs text-gray-600">Success Rate</p>
              <p className="text-xl font-bold text-green-600">
                {(support.technician_history.success_rate * 100).toFixed(1)}%
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Protocol History */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Protocol Track Record</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <p className="text-xs text-gray-600">Transfers Performed</p>
              <p className="text-2xl font-bold">{support.protocol_history.transfers_performed}</p>
            </div>
            <div>
              <p className="text-xs text-gray-600">Success Rate</p>
              <p className="text-xl font-bold text-green-600">
                {(support.protocol_history.success_rate * 100).toFixed(1)}%
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Similar Cases */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Similar Cases</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-xs text-gray-600">{support.similar_cases.length} similar cases found</p>
            {support.similar_cases.length > 0 && (
              <div className="text-sm">
                <p className="text-xs text-gray-600">Avg Success Rate</p>
                <p className="text-xl font-bold text-blue-600">
                  {(
                    (support.similar_cases.filter((c) => c.outcome === "success").length /
                      support.similar_cases.length) *
                    100
                  ).toFixed(0)}
                  %
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Alternative Protocols */}
      {support.alternative_protocols.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Alternative Protocols to Consider</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {support.alternative_protocols.map((protocol, idx) => (
                <div key={idx} className="p-3 border rounded bg-gray-50">
                  {protocol}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Decision Record */}
      <Card>
        <CardHeader>
          <CardTitle>Record Your Decision</CardTitle>
          <CardDescription>Choose how to proceed with this case</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <p className="text-sm font-semibold">Decision:</p>
            <div className="flex gap-2">
              <Button
                variant={userDecision === "accept" ? "default" : "outline"}
                onClick={() => setUserDecision("accept")}
              >
                ✓ Accept Recommendation
              </Button>
              <Button
                variant={userDecision === "review" ? "default" : "outline"}
                onClick={() => setUserDecision("review")}
              >
                Review Further
              </Button>
              <Button
                variant={userDecision === "reject" ? "default" : "outline"}
                onClick={() => setUserDecision("reject")}
              >
                ✗ Reject
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-semibold">Notes (Optional):</p>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any additional notes..."
              className="w-full p-2 border rounded text-sm"
              rows={3}
            />
          </div>

          <div className="flex gap-2">
            <Button onClick={handleRecordDecision} disabled={!userDecision}>
              Record Decision
            </Button>
            <Button variant="outline" onClick={() => navigate("/app/predictions")}>
              Cancel
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
