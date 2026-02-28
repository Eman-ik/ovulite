import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/layouts/AppLayout";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import DataEntryPage from "@/pages/DataEntryPage";
import TransferFormPage from "@/pages/TransferFormPage";
import PredictionPage from "@/pages/PredictionPage";
import GradingPage from "@/pages/GradingPage";
import QCDashboardPage from "@/pages/QCDashboardPage";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="data-entry" element={<DataEntryPage />} />
              <Route path="data-entry/new" element={<TransferFormPage />} />
              <Route path="data-entry/:id" element={<TransferFormPage />} />
              <Route path="predictions" element={<PredictionPage />} />
              <Route path="embryo-grading" element={<GradingPage />} />
              <Route path="lab-qc" element={<QCDashboardPage />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
