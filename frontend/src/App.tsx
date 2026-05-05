import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/layouts/AppLayout";
import OvuliteLandingPage from "@/pages/OvuliteLandingPage";
import LoginPage from "@/pages/LoginPage";
import SignupPage from "@/pages/SignupPage";
import LoginDebugPage from "@/pages/LoginDebugPage";
import DashboardPage from "@/pages/DashboardPage";
import DataEntryPage from "@/pages/DataEntryPage";
import TransferFormPage from "@/pages/TransferFormPage";
import PredictionPage from "@/pages/PredictionPage";
import GradingPage from "@/pages/GradingPage";
import QCDashboardPage from "@/pages/QCDashboardPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import CaseRecordsPage from "@/pages/CaseRecordsPage";
import CaseDetailPage from "@/pages/CaseDetailPage";
import ModelPerformancePage from "@/pages/ModelPerformancePage";
import ReportsExportPage from "@/pages/ReportsExportPage";

import { ThemeProvider } from "@/contexts/ThemeContext";

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<OvuliteLandingPage />} />
            <Route path="/landing" element={<OvuliteLandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/login/debug" element={<LoginDebugPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/app" element={<AppLayout />}>
                <Route index element={<DashboardPage />} />
                <Route path="data-entry" element={<DataEntryPage />} />
                <Route path="data-entry/new" element={<TransferFormPage />} />
                <Route path="data-entry/:id" element={<TransferFormPage />} />
                <Route path="predictions" element={<PredictionPage />} />
                <Route path="embryo-grading" element={<GradingPage />} />
                <Route path="lab-qc" element={<QCDashboardPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="cases" element={<CaseRecordsPage />} />
                <Route path="cases/:id" element={<CaseDetailPage />} />
                <Route path="model-performance" element={<ModelPerformancePage />} />
                <Route path="reports" element={<ReportsExportPage />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
