import { useState, useEffect } from "react";
import api from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TrendingUp, TrendingDown, AlertCircle, CheckCircle } from "lucide-react";

interface ModelMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  auc_roc: number;
  calibration_error: number;
}

interface ModelPerformance {
  model_name: string;
  model_version: string;
  last_trained: string;
  total_predictions: number;
  prediction_accuracy: number;
  
  train_metrics: ModelMetrics;
  test_metrics: ModelMetrics;
  validation_metrics: ModelMetrics;
  
  confusion_matrix: {
    tp: number;
    fp: number;
    tn: number;
    fn: number;
  };
  
  performance_by_risk_band: Array<{
    risk_band: string;
    count: number;
    accuracy: number;
  }>;
  
  performance_by_protocol: Array<{
    protocol_name: string;
    count: number;
    accuracy: number;
  }>;
  
  performance_by_technician: Array<{
    technician_name: string;
    count: number;
    accuracy: number;
  }>;
  
  prediction_distribution: {
    low_risk: number;
    medium_risk: number;
    high_risk: number;
  };
  
  outcome_distribution: {
    pregnant: number;
    open: number;
    recheck: number;
  };
  
  calibration_curve: Array<{
    predicted_prob: number;
    actual_freq: number;
  }>;
  
  top_important_features: Array<{
    feature: string;
    importance: number;
  }>;
  
  performance_trend: Array<{
    month: string;
    accuracy: number;
    count: number;
  }>;
}

interface CombinedPerformance {
  pregnancy_model: ModelPerformance;
  grading_model: ModelPerformance;
  qc_model: ModelPerformance;
  overall_system_accuracy: number;
}

export default function ModelPerformancePage() {
  const [performance, setPerformance] = useState<CombinedPerformance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeModel, setActiveModel] = useState("pregnancy");

  useEffect(() => {
    fetchModelPerformance();
  }, []);

  const fetchModelPerformance = async () => {
    try {
      setLoading(true);
      const response = await api.get("/models/performance");
      setPerformance(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load model performance");
    } finally {
      setLoading(false);
    }
  };

  const getMetricsColor = (value: number) => {
    if (value >= 0.8) return "text-green-600";
    if (value >= 0.6) return "text-yellow-600";
    return "text-red-600";
  };

  const MetricsCard = ({ model, label }: { model: ModelPerformance; label: string }) => (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{label}</CardTitle>
        <CardDescription>{model.model_version}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-gray-50 rounded">
            <p className="text-xs text-gray-600">Test Accuracy</p>
            <p className={`text-xl font-bold ${getMetricsColor(model.test_metrics.accuracy)}`}>
              {(model.test_metrics.accuracy * 100).toFixed(1)}%
            </p>
          </div>
          <div className="p-3 bg-gray-50 rounded">
            <p className="text-xs text-gray-600">AUC-ROC</p>
            <p className={`text-xl font-bold ${getMetricsColor(model.test_metrics.auc_roc)}`}>
              {(model.test_metrics.auc_roc * 100).toFixed(1)}%
            </p>
          </div>
          <div className="p-3 bg-gray-50 rounded">
            <p className="text-xs text-gray-600">Precision</p>
            <p className={`text-xl font-bold ${getMetricsColor(model.test_metrics.precision)}`}>
              {(model.test_metrics.precision * 100).toFixed(1)}%
            </p>
          </div>
          <div className="p-3 bg-gray-50 rounded">
            <p className="text-xs text-gray-600">Recall</p>
            <p className={`text-xl font-bold ${getMetricsColor(model.test_metrics.recall)}`}>
              {(model.test_metrics.recall * 100).toFixed(1)}%
            </p>
          </div>
        </div>

        {/* Calibration */}
        <div className="p-3 bg-blue-50 border border-blue-200 rounded">
          <p className="text-sm font-semibold text-blue-900">Calibration Error</p>
          <p className="text-lg font-bold text-blue-600">{(model.test_metrics.calibration_error * 100).toFixed(2)}%</p>
          <p className="text-xs text-blue-700 mt-1">Lower is better (well-calibrated model)</p>
        </div>

        {/* Confusion Matrix */}
        <div className="p-3 bg-gray-50 rounded">
          <p className="text-sm font-semibold mb-2">Confusion Matrix</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <p className="text-gray-600">True Positive</p>
              <p className="text-lg font-bold text-green-600">{model.confusion_matrix.tp}</p>
            </div>
            <div>
              <p className="text-gray-600">False Positive</p>
              <p className="text-lg font-bold text-red-600">{model.confusion_matrix.fp}</p>
            </div>
            <div>
              <p className="text-gray-600">True Negative</p>
              <p className="text-lg font-bold text-green-600">{model.confusion_matrix.tn}</p>
            </div>
            <div>
              <p className="text-gray-600">False Negative</p>
              <p className="text-lg font-bold text-red-600">{model.confusion_matrix.fn}</p>
            </div>
          </div>
        </div>

        {/* Predictions Made */}
        <div className="p-3 bg-blue-50 rounded">
          <p className="text-xs text-gray-600">Total Predictions Made</p>
          <p className="text-2xl font-bold text-blue-600">{model.total_predictions}</p>
        </div>
      </CardContent>
    </Card>
  );

  if (loading)
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-600">Loading model performance data...</p>
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

  if (!performance) return <div className="p-6">No performance data available</div>;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Model Performance & Outcome Learning</h1>
        <p className="text-gray-600">Monitor AI model accuracy, learn from outcomes, improve predictions</p>
      </div>

      {/* Overall System Accuracy */}
      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm text-gray-600 mb-2">Overall System Accuracy</p>
              <p className={`text-4xl font-bold ${getMetricsColor(performance.overall_system_accuracy)}`}>
                {(performance.overall_system_accuracy * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-2">Status</p>
              {performance.overall_system_accuracy >= 0.8 ? (
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-6 h-6 text-green-600" />
                  <span className="text-lg font-bold text-green-600">High Performance</span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-6 h-6 text-yellow-600" />
                  <span className="text-lg font-bold text-yellow-600">Review Needed</span>
                </div>
              )}
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-2">Recommendation</p>
              <p className="text-sm">
                {performance.overall_system_accuracy >= 0.85
                  ? "System ready for clinical deployment"
                  : "Continue monitoring and refinement"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Model Tabs */}
      <Tabs value={activeModel} onValueChange={setActiveModel}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="pregnancy">Pregnancy Model</TabsTrigger>
          <TabsTrigger value="grading">Grading Model</TabsTrigger>
          <TabsTrigger value="qc">QC Model</TabsTrigger>
        </TabsList>

        {/* Pregnancy Model Tab */}
        <TabsContent value="pregnancy" className="space-y-4">
          <MetricsCard model={performance.pregnancy_model} label="Pregnancy Prediction Model" />

          {/* Performance by Protocol */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Performance by Protocol</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {performance.pregnancy_model.performance_by_protocol.map((protocol, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 border rounded">
                    <div>
                      <p className="font-medium text-sm">{protocol.protocol_name}</p>
                      <p className="text-xs text-gray-500">{protocol.count} predictions</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {protocol.accuracy >= 0.8 ? (
                        <TrendingUp className="w-4 h-4 text-green-600" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-600" />
                      )}
                      <span className={`font-bold ${getMetricsColor(protocol.accuracy)}`}>
                        {(protocol.accuracy * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Performance by Technician */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Performance by Technician</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {performance.pregnancy_model.performance_by_technician.map((tech, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 border rounded">
                    <div>
                      <p className="font-medium text-sm">{tech.technician_name}</p>
                      <p className="text-xs text-gray-500">{tech.count} predictions</p>
                    </div>
                    <span className={`font-bold ${getMetricsColor(tech.accuracy)}`}>
                      {(tech.accuracy * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Top Features */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Top Important Features</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {performance.pregnancy_model.top_important_features.map((feature, idx) => (
                  <div key={idx}>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm font-medium">{feature.feature}</span>
                      <span className="text-sm text-gray-600">{(feature.importance * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${feature.importance * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Grading Model Tab */}
        <TabsContent value="grading" className="space-y-4">
          <MetricsCard model={performance.grading_model} label="Embryo Grading Model" />
        </TabsContent>

        {/* QC Model Tab */}
        <TabsContent value="qc" className="space-y-4">
          <MetricsCard model={performance.qc_model} label="QC Anomaly Detection Model" />
        </TabsContent>
      </Tabs>

      {/* Learning from Outcomes */}
      <Card>
        <CardHeader>
          <CardTitle>Learning from Outcomes</CardTitle>
          <CardDescription>How actual results compare to predictions</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-green-50 rounded">
              <p className="text-sm text-gray-600">Correct Predictions</p>
              <p className="text-2xl font-bold text-green-600">
                {(
                  performance.pregnancy_model.confusion_matrix.tp +
                  performance.pregnancy_model.confusion_matrix.tn
                ).toLocaleString()}
              </p>
            </div>
            <div className="p-4 bg-red-50 rounded">
              <p className="text-sm text-gray-600">Misclassifications</p>
              <p className="text-2xl font-bold text-red-600">
                {(
                  performance.pregnancy_model.confusion_matrix.fp +
                  performance.pregnancy_model.confusion_matrix.fn
                ).toLocaleString()}
              </p>
            </div>
          </div>
          <p className="text-sm text-gray-600">
            Over time, models learn from outcome feedback to improve prediction accuracy. This dashboard tracks continuous
            improvement cycles.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
