import { useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Download, FileText, BarChart3, Calendar, Filter } from "lucide-react";

export default function ReportsExportPage() {
  const [reportType, setReportType] = useState("summary");
  const [exportFormat, setExportFormat] = useState("pdf");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [includeAnalytics, setIncludeAnalytics] = useState(true);
  const [includePredictions, setIncludePredictions] = useState(true);
  const [includeQC, setIncludeQC] = useState(true);
  const [includeAuditTrail, setIncludeAuditTrail] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleGenerateReport = async () => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      const params = new URLSearchParams({
        type: reportType,
        format: exportFormat,
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
        include_analytics: includeAnalytics.toString(),
        include_predictions: includePredictions.toString(),
        include_qc: includeQC.toString(),
        include_audit: includeAuditTrail.toString(),
      });

      const response = await api.get(`/reports/generate?${params}`, {
        responseType: "blob",
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `report-${reportType}-${Date.now()}.${exportFormat}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);

      setSuccess(`Report generated and downloaded successfully!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate report");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Reports & Export</h1>
        <p className="text-gray-600">Generate custom reports and export data in multiple formats</p>
      </div>

      {/* Alerts */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-green-800">{success}</p>
        </div>
      )}

      {/* Report Generator */}
      <Tabs defaultValue="generate">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="generate">Generate Report</TabsTrigger>
          <TabsTrigger value="templates">Report Templates</TabsTrigger>
          <TabsTrigger value="exports">Data Exports</TabsTrigger>
        </TabsList>

        {/* Generate Tab */}
        <TabsContent value="generate" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Create Custom Report</CardTitle>
              <CardDescription>Select report type, format, and content options</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Report Type */}
              <div>
                <label className="block text-sm font-semibold mb-2">Report Type</label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { id: "summary", name: "Summary Report", icon: "📊" },
                    { id: "detailed", name: "Detailed Report", icon: "📋" },
                    { id: "analytics", name: "Analytics Report", icon: "📈" },
                    { id: "model_performance", name: "Model Performance", icon: "🤖" },
                  ].map((type) => (
                    <button
                      key={type.id}
                      onClick={() => setReportType(type.id)}
                      className={`p-3 border rounded-lg text-left transition ${
                        reportType === type.id
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <span className="text-lg">{type.icon}</span>
                      <p className="font-medium text-sm">{type.name}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Export Format */}
              <div>
                <label className="block text-sm font-semibold mb-2">Export Format</label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { id: "pdf", name: "PDF", icon: "📄" },
                    { id: "excel", name: "Excel (.xlsx)", icon: "📊" },
                    { id: "csv", name: "CSV", icon: "📋" },
                    { id: "json", name: "JSON", icon: "{ }" },
                  ].map((format) => (
                    <button
                      key={format.id}
                      onClick={() => setExportFormat(format.id)}
                      className={`p-3 border rounded-lg text-left transition ${
                        exportFormat === format.id
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <span className="text-lg">{format.icon}</span>
                      <p className="font-medium text-sm">{format.name}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Date Range */}
              <div>
                <label className="block text-sm font-semibold mb-2">Date Range (Optional)</label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-600">From</label>
                    <Input
                      type="date"
                      value={dateFrom}
                      onChange={(e) => setDateFrom(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-600">To</label>
                    <Input
                      type="date"
                      value={dateTo}
                      onChange={(e) => setDateTo(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Content Options */}
              <div>
                <label className="block text-sm font-semibold mb-3">Content to Include</label>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={includeAnalytics}
                      onCheckedChange={setIncludeAnalytics}
                    />
                    <label className="text-sm cursor-pointer">Analytics & KPIs</label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={includePredictions}
                      onCheckedChange={setIncludePredictions}
                    />
                    <label className="text-sm cursor-pointer">Prediction Results & Performance</label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={includeQC}
                      onCheckedChange={setIncludeQC}
                    />
                    <label className="text-sm cursor-pointer">QC Analysis & Anomalies</label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={includeAuditTrail}
                      onCheckedChange={setIncludeAuditTrail}
                    />
                    <label className="text-sm cursor-pointer">Audit Trail & User Actions (detailed)</label>
                  </div>
                </div>
              </div>

              {/* Generate Button */}
              <Button
                onClick={handleGenerateReport}
                disabled={loading}
                className="w-full"
                size="lg"
              >
                <Download className="w-4 h-4 mr-2" />
                {loading ? "Generating..." : "Generate & Download Report"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Templates Tab */}
        <TabsContent value="templates" className="space-y-4">
          {[
            {
              id: "weekly_summary",
              name: "Weekly Summary Report",
              description: "Summary of predictions, outcomes, and KPIs for the past week",
              format: ["PDF", "Excel"],
              icon: "📅",
            },
            {
              id: "monthly_performance",
              name: "Monthly Performance Report",
              description: "Detailed monthly performance metrics, protocol effectiveness, technician stats",
              format: ["PDF", "Excel"],
              icon: "📊",
            },
            {
              id: "protocol_comparison",
              name: "Protocol Comparison Report",
              description: "Compare success rates, outcomes, and efficiency of different protocols",
              format: ["PDF", "Excel", "CSV"],
              icon: "⚖️",
            },
            {
              id: "model_accuracy",
              name: "Model Accuracy & Calibration",
              description: "Detailed model performance metrics, prediction accuracy, calibration analysis",
              format: ["PDF", "JSON"],
              icon: "🤖",
            },
            {
              id: "qc_compliance",
              name: "QC Compliance Report",
              description: "QC pass rates, anomalies detected, control chart analysis",
              format: ["PDF", "Excel"],
              icon: "✅",
            },
            {
              id: "case_traceability",
              name: "Case Traceability Report",
              description: "Detailed case records with audit trail, genetic info, outcomes",
              format: ["PDF", "CSV", "JSON"],
              icon: "🔍",
            },
          ].map((template) => (
            <Card key={template.id}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-2xl">{template.icon}</span>
                      <h3 className="font-semibold">{template.name}</h3>
                    </div>
                    <p className="text-sm text-gray-600 mb-3">{template.description}</p>
                    <div className="flex gap-2">
                      {template.format.map((fmt) => (
                        <Badge key={fmt} variant="outline">
                          {fmt}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <Button variant="outline">Use Template</Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* Exports Tab */}
        <TabsContent value="exports" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Bulk Data Exports</CardTitle>
              <CardDescription>Export large datasets for external analysis</CardDescription>
            </CardHeader>
          </Card>

          {[
            {
              name: "All Transfer Records",
              description: "Export complete ET transfer data (488+ records)",
              records: "488",
              formats: ["CSV", "Excel", "JSON"],
              icon: "📋",
            },
            {
              name: "Prediction Results",
              description: "Export all predictions with inputs, outputs, and outcomes",
              records: "488",
              formats: ["CSV", "Excel", "JSON"],
              icon: "🔮",
            },
            {
              name: "QC Analysis Data",
              description: "Export QC analysis, anomaly flags, and control chart data",
              records: "488",
              formats: ["CSV", "Excel"],
              icon: "🔬",
            },
            {
              name: "Analytics Metrics",
              description: "Export KPIs, performance metrics, by-protocol stats",
              records: "50+",
              formats: ["CSV", "Excel", "JSON"],
              icon: "📊",
            },
            {
              name: "Audit Trail",
              description: "Export complete audit log of all system actions and user activities",
              records: "5000+",
              formats: ["CSV", "JSON"],
              icon: "📖",
            },
            {
              name: "Model Training Data",
              description: "Export features and labels for model retraining",
              records: "488",
              formats: ["CSV", "JSON"],
              icon: "🤖",
            },
          ].map((export_, idx) => (
            <Card key={idx}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-2xl">{export_.icon}</span>
                      <h3 className="font-semibold">{export_.name}</h3>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{export_.description}</p>
                    <p className="text-xs text-gray-500 mb-3">{export_.records} records</p>
                    <div className="flex gap-2">
                      {export_.formats.map((fmt) => (
                        <Badge key={fmt} variant="outline">
                          {fmt}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <Button
                    onClick={async () => {
                      try {
                        const response = await api.get(`/exports/${idx}`, {
                          responseType: "blob",
                        });
                        const url = window.URL.createObjectURL(new Blob([response.data]));
                        const link = document.createElement("a");
                        link.href = url;
                        link.setAttribute("download", `export-${idx}-${Date.now()}.csv`);
                        document.body.appendChild(link);
                        link.click();
                      } catch (err) {
                        alert("Failed to download export");
                      }
                    }}
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Export
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>

      {/* Info Card */}
      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <FileText className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-semibold text-blue-900">Report Generation Help</p>
              <p className="text-blue-700 mt-1">
                • <strong>Summary Reports</strong> provide high-level overview suitable for stakeholders
              </p>
              <p className="text-blue-700">
                • <strong>Detailed Reports</strong> include all case-level data, predictions, and outcomes
              </p>
              <p className="text-blue-700">
                • <strong>PDF</strong> format is best for sharing and printing
              </p>
              <p className="text-blue-700">
                • <strong>Excel/CSV</strong> formats are best for further analysis in other tools
              </p>
              <p className="text-blue-700">
                • <strong>JSON</strong> format is suitable for programmatic integration
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
