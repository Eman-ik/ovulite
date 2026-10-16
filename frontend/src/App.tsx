import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/layouts/AppLayout";
import OvuliteLandingPage from "@/pages/OvuliteLandingPage";
import LoginPage from "@/pages/LoginPage";
import SignupPage from "@/pages/SignupPage";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";
import ChangePasswordPage from "@/pages/ChangePasswordPage";
import DashboardPage from "@/pages/DashboardPage";
import DataEntryPage from "@/pages/DataEntryPage";
import TransferFormPage from "@/pages/TransferFormPage";
import PredictionPage from "@/pages/PredictionPage";
import DecisionSupportPage from "@/pages/DecisionSupportPage";
import GradingPage from "@/pages/GradingPage";
import OPUIVFPage from "@/pages/OPUIVFPage";
import QCDashboardPage from "@/pages/QCDashboardPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import AdminPage from "@/pages/AdminPage";
import ResearchPage from "@/pages/ResearchPage";
import SynchronizationPage from "@/pages/SynchronizationPage";
import ProtocolSchedulesPage from "@/pages/ProtocolSchedulesPage";
import PregnancyDiagnosisPage from "@/pages/PregnancyDiagnosisPage";
import LaboratoryPage from "@/pages/LaboratoryPage";
import OocyteProcessingPage from "@/pages/OocyteProcessingPage";
import CaseRecordsPage from "@/pages/CaseRecordsPage";
import CaseDetailPage from "@/pages/CaseDetailPage";
import ModelPerformancePage from "@/pages/ModelPerformancePage";
import MonitoringDashboardPage from "@/pages/MonitoringDashboardPage";
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
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            {/* Outside the app shell: a user on a temporary password cannot
                load anything the shell renders, so there is nothing to wrap. */}
            <Route path="/change-password" element={<ChangePasswordPage />} />
            
            
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

{/* researcher and embryologist are read-only here: the page hides every write
    control and the API refuses the write endpoints for those roles. Running a
    prediction is transfer-time work and stays with the ET side. */}
<Route
  path="predictions"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "et team", "veterinarian", "researcher", "embryologist"]}>
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
  path="laboratory"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "embryologist"]}>
      <LaboratoryPage />
    </ProtectedRoute>
  }
/>

<Route
  path="oocyte-processing"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "embryologist"]}>
      <OocyteProcessingPage />
    </ProtectedRoute>
  }
/>

<Route
  path="synchronization"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "et team", "veterinarian"]}>
      <SynchronizationPage />
    </ProtectedRoute>
  }
/>

<Route
  path="protocol-schedules"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "et team", "veterinarian"]}>
      <ProtocolSchedulesPage />
    </ProtectedRoute>
  }
/>

<Route
  path="pregnancy-diagnosis"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "et team", "veterinarian"]}>
      <PregnancyDiagnosisPage />
    </ProtectedRoute>
  }
/>

<Route
  path="admin"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin"]}>
      <AdminPage />
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

{/* The live counterpart to model-performance: that page reports the
    artifact's training-time holdout metrics, this one tracks how the model
    behaves against outcomes that have since resolved. Same audience, so the
    same gate. Running the pipeline is admin-only and the page hides that
    control for everyone else. */}
<Route
  path="monitoring"
  element={
    <ProtectedRoute allowedRoles={["admin", "organization_admin", "researcher"]}>
      <MonitoringDashboardPage />
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
