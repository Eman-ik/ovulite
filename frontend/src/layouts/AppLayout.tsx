import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useRef, useState } from "react";
import { ROLE_PERMISSIONS, getPermissions, getRoleDisplayName } from "@/lib/roleRoutes";
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
  LifeBuoy,
  Sun,
  Moon,
  FlaskConical,
  BookOpen,
  Upload,
  Search,
  Bell,
  GitCompare,
  CalendarClock,
  HeartPulse,
  ListOrdered,
  Boxes,
  Beaker,
  UserCog,
} from "lucide-react";
import ovuliteLogo from "../pages/icon.png";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";

type Permission = keyof (typeof ROLE_PERMISSIONS)["admin"];

type NavItem = {
  to: string;
  icon: typeof LayoutDashboard;
  label: string;
  /** Item is shown when the role has this permission. */
  permission?: Permission;
  /** …or any one of these permissions. */
  permissionAny?: Permission[];
};

const NAV_SECTIONS: { label: string; items: NavItem[] }[] = [
  {
    label: "Main",
    items: [
      { to: "", icon: LayoutDashboard, label: "Dashboard" },
      { to: "cases", icon: FolderOpen, label: "Case Records" },
    ],
  },
  {
    label: "Laboratory",
    items: [
      { to: "laboratory", icon: Boxes, label: "Laboratory", permission: "canEnterLabData" },
      { to: "opu-ivf", icon: FlaskConical, label: "OPU & IVF Batches", permission: "canEnterLabData" },
      { to: "oocyte-processing", icon: Beaker, label: "Oocytes & IVM", permission: "canEnterLabData" },
      { to: "embryo-grading", icon: Microscope, label: "Embryo Grading", permission: "canGradeEmbryos" },
      { to: "lab-qc", icon: Shield, label: "Lab QC", permission: "canEnterLabData" },
    ],
  },
  {
    label: "Clinical",
    items: [
      { to: "synchronization", icon: CalendarClock, label: "Synchronization", permission: "canEnterETData" },
      { to: "pregnancy-diagnosis", icon: HeartPulse, label: "Pregnancy Diagnosis", permission: "canEnterETData" },
      { to: "protocol-schedules", icon: ListOrdered, label: "Protocol Schedules", permission: "canEnterETData" },
      { to: "data-entry", icon: FileInput, label: "Data Entry", permission: "canEnterETData" },
      { to: "predictions", icon: Brain, label: "Predictions", permission: "canViewPredictions" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { to: "analytics", icon: BarChart3, label: "Analytics", permission: "canViewAnalytics" },
      { to: "research", icon: GitCompare, label: "Research", permission: "canViewResearch" },
      { to: "model-performance", icon: TrendingUp, label: "Model Performance", permission: "canViewResearch" },
      { to: "literature", icon: BookOpen, label: "Literature" },
    ],
  },
  {
    label: "Administration",
    items: [
      { to: "admin", icon: UserCog, label: "Users & Sites", permission: "canManageUsers" },
    ],
  },
  {
    label: "Data",
    items: [
      { to: "intake", icon: Upload, label: "Data Intake", permissionAny: ["canEnterLabData", "canEnterETData"] },
      { to: "reports", icon: FileText, label: "Reports & Export", permission: "canExportReports" },
    ],
  },
];

// The sign-in background, carried through the whole app behind a light wash
// so text and cards stay readable.
const APP_BACKGROUND: React.CSSProperties = {
  backgroundImage: "linear-gradient(rgba(234, 241, 241, 0.3), rgba(234, 241, 241, 0.3)), url(/auth/login-bg.png)",
  backgroundSize: "cover",
  backgroundPosition: "center",
  backgroundAttachment: "fixed",
};

export default function AppLayout() {
  const { logout, user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  const permissions = getPermissions(user?.role);

  const visibleSections = useMemo(() => {
    const allowed = (item: NavItem) => {
      if (item.permission) return Boolean(permissions?.[item.permission]);
      if (item.permissionAny) return item.permissionAny.some((p) => Boolean(permissions?.[p]));
      return true;
    };
    return NAV_SECTIONS.map((section) => ({
      ...section,
      items: section.items.filter(allowed),
    })).filter((section) => section.items.length > 0);
  }, [permissions]);

  // Global search over the destinations this role can actually reach.
  const results = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return [];
    return visibleSections
      .flatMap((section) => section.items.map((item) => ({ ...item, section: section.label })))
      .filter((item) => item.label.toLowerCase().includes(needle) || item.section.toLowerCase().includes(needle))
      .slice(0, 6);
  }, [query, visibleSections]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchRef.current?.focus();
        setSearchOpen(true);
      }
      if (e.key === "Escape") {
        setSearchOpen(false);
        setQuery("");
        searchRef.current?.blur();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const go = (to: string) => {
    navigate(to ? `/app/${to}` : "/app");
    setQuery("");
    setSearchOpen(false);
    setMobileOpen(false);
  };

  const SidebarBody = ({ onNavigate }: { onNavigate?: () => void }) => (
    <>
      <div className="flex items-center gap-3 px-5 py-5">
        <div
          className="ov-pulse-ring flex h-9 w-9 items-center justify-center overflow-hidden rounded-xl"
          style={{ background: "linear-gradient(135deg, #94A9BE, #596070)" }}
        >
          <img src={ovuliteLogo} alt="" className="h-full w-full object-cover" />
        </div>
        <div>
          <p className="text-[15px] font-semibold leading-tight tracking-tight text-[var(--sidebar-text)]">Ovulite</p>
          <p className="text-[9px] uppercase tracking-[0.16em] text-[var(--sidebar-muted)]">
            Reproductive Intelligence
          </p>
        </div>
      </div>

      <nav className="custom-scrollbar flex-1 space-y-4 overflow-y-auto px-3 pb-3">
        {visibleSections.map((section) => (
          <div key={section.label} className="space-y-0.5">
            <p className="nav-section-label mb-1.5">{section.label}</p>
            {section.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === ""}
                onClick={onNavigate}
                className={({ isActive }) => `nav-item ${isActive ? "nav-item-active" : ""}`}
              >
                <item.icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
                <span className="truncate">{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="border-t border-[var(--sidebar-border)] p-3">
        <div className="flex items-center gap-3 rounded-2xl border border-[var(--sidebar-border)] bg-white p-2.5 shadow-sm">
          <img
            src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user?.username || "guest"}`}
            alt=""
            className="h-9 w-9 shrink-0 rounded-full bg-black/[0.06]"
          />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium leading-tight text-[var(--sidebar-text)]">
              {user?.full_name || user?.username}
            </p>
            <p className="truncate text-[11px] text-[var(--sidebar-muted)]">
              {user?.email || getRoleDisplayName(user?.role)}
            </p>
          </div>
          <button
            onClick={logout}
            title="Log out"
            aria-label="Log out"
            className="shrink-0 rounded-lg p-2 text-[var(--sidebar-muted)] transition hover:bg-black/[0.05] hover:text-[var(--sidebar-text)]"
          >
            <LogOut className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>
      </div>
    </>
  );

  return (
    <div className="ov-app min-h-screen text-[var(--foreground)] lg:flex lg:gap-5 lg:p-4" style={APP_BACKGROUND}>
      {/* Desktop sidebar */}
      <aside className="sidebar-glow hidden w-[264px] shrink-0 flex-col rounded-3xl border border-[var(--sidebar-border)] bg-white/55 backdrop-blur-xl lg:sticky lg:top-4 lg:flex lg:h-[calc(100vh-2rem)]">
        <SidebarBody />
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm lg:hidden" onClick={() => setMobileOpen(false)}>
          <aside
            className="flex h-full w-[280px] max-w-[85vw] flex-col border-r border-[var(--sidebar-border)] bg-[var(--sidebar-bg)]"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              className="absolute right-4 top-5 rounded-lg p-2 text-[var(--sidebar-muted)] hover:bg-black/[0.05]"
              onClick={() => setMobileOpen(false)}
              aria-label="Close menu"
            >
              <X className="h-5 w-5" />
            </button>
            <SidebarBody onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar — global search + actions */}
        <header className="sticky top-0 z-30 flex items-center gap-3 bg-white/50 px-3 py-3 backdrop-blur-xl lg:static lg:bg-transparent lg:px-0 lg:pb-4 lg:pt-0 lg:backdrop-blur-none">
          <button
            type="button"
            className="rounded-xl border border-[var(--border)] p-2 text-[var(--foreground)] lg:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
            <input
              ref={searchRef}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSearchOpen(true);
              }}
              onFocus={() => setSearchOpen(true)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && results.length > 0) go(results[0].to);
              }}
              placeholder="Search pages — donors, grading, analytics…"
              className="h-11 w-full rounded-2xl border border-[var(--border)] bg-[var(--card)] pl-11 pr-16 text-sm text-[var(--foreground)] outline-none transition placeholder:text-[var(--muted-foreground)] focus:border-[rgba(168,203,160,0.4)]"
            />
            <kbd className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded-lg border border-[var(--border)] px-2 py-1 text-[10px] font-medium text-[var(--muted-foreground)] sm:block">
              ⌘K
            </kbd>

            {searchOpen && results.length > 0 && (
              <div className="dash-card-tight absolute left-0 right-0 top-[calc(100%+0.5rem)] z-40 !p-2">
                {results.map((item) => (
                  <button
                    key={item.to}
                    onClick={() => go(item.to)}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm text-[var(--foreground)] hover:bg-black/[0.04]"
                  >
                    <item.icon className="h-4 w-4 text-[var(--primary)]" strokeWidth={1.75} />
                    <span className="flex-1">{item.label}</span>
                    <span className="text-xs text-[var(--muted-foreground)]">{item.section}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            type="button"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] transition hover:text-[var(--foreground)]"
            aria-label="Notifications"
          >
            <Bell className="h-[18px] w-[18px]" strokeWidth={1.75} />
          </button>
          <button
            onClick={toggleTheme}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] transition hover:text-[var(--foreground)]"
            title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          >
            {theme === "light" ? <Moon className="h-[18px] w-[18px]" /> : <Sun className="h-[18px] w-[18px]" />}
          </button>
          <button
            type="button"
            className="hidden h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] transition hover:text-[var(--foreground)] sm:flex"
            aria-label="Support"
          >
            <LifeBuoy className="h-[18px] w-[18px]" strokeWidth={1.75} />
          </button>
        </header>

        <main className="min-w-0 flex-1 px-3 pb-8 lg:px-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
