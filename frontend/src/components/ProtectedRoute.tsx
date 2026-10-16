import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { normalizeRole } from "@/lib/roleRoutes";
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

  // A temporary password gets you exactly one screen. Enforced here as well
  // as at login, so a bookmarked deep link cannot walk past it.
  if (user.must_change_password) {
    return <Navigate to="/change-password" replace />;
  }

  // Compare the same way the sidebar does: both sides go through normalizeRole,
  // so a legacy string ("et team", "organization_admin", "viewer") is judged as
  // the role it means. Comparing raw strings here would have let a sidebar item
  // show for a role the guard then refused, or the reverse.
  if (allowedRoles && !allowedRoles.map(normalizeRole).includes(normalizeRole(user.role))) {
    return <Navigate to="/app" replace />;
  }

  return children ? <>{children}</> : <Outlet />;
}