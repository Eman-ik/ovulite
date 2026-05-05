import { useAuth } from "@/contexts/AuthContext";
import { RoleBasedDashboard } from "@/components/RoleBasedDashboard";
import AdminDashboard from "./AdminDashboard";

export default function DashboardPage() {
  const { user } = useAuth();
  
  // Check user role - if not admin, show role-based dashboard
  const userRole = user?.role?.toLowerCase() || "";
  if (!userRole.includes("admin")) {
    return <RoleBasedDashboard />;
  }

  // Admin gets full analytics dashboard with real data
  return <AdminDashboard />;
}