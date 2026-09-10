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
import DecisionSupportPage from "@/pages/DecisionSupportPage";
import GradingPage from "@/pages/GradingPage";
import OPUIVFPage from "@/pages/OPUIVFPage";
import QCDashboardPage from "@/pages/QCDashboardPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import ResearchPage from "@/pages/ResearchPage";
import CaseRecordsPage from "@/pages/CaseRecordsPage";
import CaseDetailPage from "@/pages/CaseDetailPage";
import ModelPerformancePage from "@/pages/ModelPerformancePage";
import ReportsExportPage from "@/pages/ReportsExportPage";
import LiteraturePage from "@/pages/LiteraturePage";
import IntakePage from "@/pages/IntakePage";

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
                <Route path="literature" element={<LiteraturePage />} />
                {/* Data intake writes records, so the read-only researcher role is excluded. */}
                <Route path="intake" element={<ProtectedRoute allowedRoles={["admin", "organization_admin", "embryologist", "et team", "veterinarian"]}><IntakePage /></ProtectedRoute>} />

<Route
  path="data-entry"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "et team", "veterinarian"]}>
      <DataEntryPage />
    </ProtectedRoute>
  }
/>

<Route
  path="data-entry/new"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "et team", "veterinarian"]}>
      <TransferFormPage />
    </ProtectedRoute>
  }
/>

<Route
  path="data-entry/:id"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "et team", "veterinarian"]}>
      <TransferFormPage />
    </ProtectedRoute>
  }
/>

<Route
  path="predictions"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "et team", "veterinarian"]}>
      <PredictionPage />
    </ProtectedRoute>
  }
/>

<Route
  path="predictions/:id/decision-support"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "et team", "veterinarian"]}>
      <DecisionSupportPage />
    </ProtectedRoute>
  }
/>

<Route
  path="embryo-grading"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "embryologist"]}>
      <GradingPage />
    </ProtectedRoute>
  }
/>

<Route
  path="lab-qc"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "embryologist"]}>
      <QCDashboardPage />
    </ProtectedRoute>
  }
/>

<Route
  path="opu-ivf"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "embryologist"]}>
      <OPUIVFPage />
    </ProtectedRoute>
  }
/>

<Route
  path="analytics"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "researcher"]}>
      <AnalyticsPage />
    </ProtectedRoute>
  }
/>

<Route
  path="research"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "researcher"]}>
      <ResearchPage />
    </ProtectedRoute>
  }
/>

<Route
  path="cases"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "embryologist", "et team", "veterinarian", "researcher", "viewer"]}>
      <CaseRecordsPage />
    </ProtectedRoute>
  }
/>
<Route
  path="cases/:id"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "embryologist", "et team", "veterinarian", "researcher", "viewer"]}>
      <CaseDetailPage />
    </ProtectedRoute>
  }
/>

<Route
  path="model-performance"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "researcher"]}>
      <ModelPerformancePage />
    </ProtectedRoute>
  }
/>

<Route
  path="reports"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "embryologist", "et team", "veterinarian", "researcher"]}>
      <ReportsExportPage />
    </ProtectedRoute>
  }
/>
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
