import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  FileInput,
  Brain,
  Microscope,
  Shield,
  BarChart3,
  LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/data-entry", icon: FileInput, label: "Data Entry" },
  { to: "/predictions", icon: Brain, label: "Predictions" },
  { to: "/embryo-grading", icon: Microscope, label: "Embryo Grading" },
  { to: "/lab-qc", icon: Shield, label: "Lab QC" },
  { to: "/analytics", icon: BarChart3, label: "Analytics" },
];

export default function AppLayout() {
  const handleLogout = () => {
    localStorage.removeItem("ovulite_token");
    window.location.href = "/login";
  };

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 z-40 flex h-full w-64 flex-col border-r bg-card">
        {/* Branding */}
        <div className="flex h-16 items-center gap-2 border-b px-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground text-sm font-bold">
            O
          </div>
          <span className="text-lg font-semibold">Ovulite</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-4">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Logout */}
        <div className="border-t p-4">
          <Button
            variant="ghost"
            className="w-full justify-start gap-3"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <div className="ml-64 flex flex-1 flex-col">
        {/* Top bar */}
        <header className="flex h-16 items-center justify-between border-b px-6">
          <h1 className="text-lg font-semibold">Ovulite AI Platform</h1>
          <div className="text-sm text-muted-foreground">
            Reproductive Intelligence System
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
