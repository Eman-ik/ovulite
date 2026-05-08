import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import type { ReactNode } from "react";

type ProtectedRouteProps = {
  allowedRoles?: string[];
  children?: ReactNode;
};

export default function ProtectedRoute({ allowedRoles, children }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const role = user.role?.toLowerCase();

  if (allowedRoles && !allowedRoles.includes(role || "")) {
    return <Navigate to="/app" replace />;
  }

  return children ? <>{children}</> : <Outlet />;
}