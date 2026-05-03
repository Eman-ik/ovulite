import { NavLink, Outlet } from "react-router-dom";
import { useMemo, useState } from "react";
import {
  LayoutDashboard,
  FileInput,
  Brain,
  Microscope,
  Shield,
  BarChart3,
  LogOut,
  Menu,
  X,
  FileText,
  TrendingUp,
  FolderOpen,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";

const navItems = [
  { to: "", icon: LayoutDashboard, label: "Dashboard" },
  { to: "data-entry", icon: FileInput, label: "Data Entry" },
  { to: "predictions", icon: Brain, label: "Predictions" },
  { to: "embryo-grading", icon: Microscope, label: "Embryo Grading" },
  { to: "lab-qc", icon: Shield, label: "Lab QC" },
  { to: "analytics", icon: BarChart3, label: "Analytics" },
  { to: "cases", icon: FolderOpen, label: "Case Records" },
  { to: "model-performance", icon: TrendingUp, label: "Model Performance" },
  { to: "reports", icon: FileText, label: "Reports & Export" },
];

export default function AppLayout() {
  const { logout, user } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const displayName = useMemo(() => {
    if (!user) return "Guest";
    return user.full_name || user.username;
  }, [user]);

  const NavItems = ({ onNavigate }: { onNavigate?: () => void }) => (
    <nav className="space-y-1.5">
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === ""}
          onClick={onNavigate}
          className={({ isActive }) =>
            `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
              isActive
                ? "bg-[#00d2ff]/20 text-[#00d2ff] shadow-[0_0_24px_rgba(0,210,255,0.2)] border border-[#00d2ff]/30 glow-shadow-blue"
                : "text-slate-400 hover:bg-white/10 hover:text-white"
            }`
          }
        >
          <item.icon className="h-4 w-4 shrink-0" strokeWidth={1.5} />
          {item.label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen text-slate-200 bg-transparent">
      {/* Desktop sidebar */}
      <aside className="glass-panel fixed left-4 top-4 bottom-4 z-30 hidden w-72 flex-col rounded-3xl lg:flex border border-white/10">
        <div className="flex h-20 items-center gap-3 border-b border-white/10 px-6">
          <div className="ov-pulse-ring flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#ff0096] to-[#9d00ff] text-sm font-bold text-white glow-shadow-pink">
            O
          </div>
          <div>
            <p className="font-semibold tracking-tight text-white">Ovulite</p>
            <p className="text-xs uppercase tracking-[0.18em] text-[#00d2ff]">AI Command</p>
          </div>
        </div>

        <div className="flex-1 p-4 overflow-y-auto custom-scrollbar">
          <NavItems />
        </div>

        <div className="space-y-2 border-t border-white/10 p-4">
          {user && (
            <div className="truncate rounded-xl bg-white/10 px-3 py-2 text-xs text-slate-400">
              {displayName}
              <span className="ml-1 text-[10px] uppercase opacity-70">
                ({user.role})
              </span>
            </div>
          )}
          <Button
            variant="ghost"
            className="w-full justify-start gap-3 hover:bg-[#ff0096]/10 text-slate-400 hover:text-[#ff0096] transition-colors"
            onClick={logout}
          >
            <LogOut className="h-4 w-4" strokeWidth={1.5} />
            Logout
          </Button>
        </div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        >
          <aside
            className="glass-panel h-full w-80 max-w-[88vw] rounded-r-3xl border-l-0 p-4 border-white/10"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between border-b border-white/10 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-[#ff0096] to-[#9d00ff] text-sm font-bold text-white glow-shadow-pink">
                  O
                </div>
                <p className="font-semibold text-white">Ovulite</p>
              </div>
              <button
                type="button"
                className="rounded-lg p-2 text-slate-500 hover:bg-white/10 hover:text-white"
                onClick={() => setMobileOpen(false)}
                aria-label="Close menu"
              >
                <X className="h-5 w-5" strokeWidth={1.5} />
              </button>
            </div>
            <NavItems onNavigate={() => setMobileOpen(false)} />
            <div className="mt-5 border-t border-white/10 pt-4">
              <Button variant="ghost" className="w-full justify-start gap-3 hover:bg-[#ff0096]/10 hover:text-[#ff0096] text-slate-400" onClick={logout}>
                <LogOut className="h-4 w-4" strokeWidth={1.5} />
                Logout
              </Button>
            </div>
          </aside>
        </div>
      )}

      {/* Main content */}
      <div className="lg:pl-[19rem]">
        <header className="glass-panel sticky top-3 z-20 mx-3 mt-3 flex h-16 items-center justify-between rounded-2xl px-4 sm:px-6 lg:mx-4 border-white/10">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-xl border border-white/10 bg-white/5 p-2 text-slate-400 hover:text-white lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" strokeWidth={1.5} />
            </button>
            <h1 className="text-base font-semibold sm:text-lg text-white">Ovulite AI Platform</h1>
          </div>
          <div className="hidden text-sm text-[#00d2ff] sm:block glow-shadow-blue">
            Reproductive Intelligence System
          </div>
          <div className="rounded-full border border-[#ff0096]/30 bg-[#ff0096]/10 px-3 py-1.5 text-xs sm:text-sm text-[#ff0096] font-medium glow-shadow-pink">
            {displayName}
          </div>
        </header>

        <main className="p-3 sm:p-4 lg:p-4">
          <section className="glass-panel min-h-[calc(100vh-7.5rem)] rounded-2xl p-4 sm:p-6 border-white/10">
            <Outlet />
          </section>
        </main>
      </div>
    </div>
  );
}
