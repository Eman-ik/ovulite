/**
 * Ovulite's four operational roles, plus the two support roles the backend
 * already issues.
 *
 *   admin         → runs the platform          (Command Center)
 *   embryologist  → runs the IVF laboratory    (OPU → embryo → freeze)
 *   veterinarian  → runs recipients and ET     (sync → CL → transfer → PD)
 *   researcher    → analyses outcomes          (analytics, models, exports)
 *
 * Support roles: `organization_admin` (admin scoped to one org) and `viewer`
 * (read-only). `et team` is the legacy string for `veterinarian` — the ET
 * dataset was imported with it, so both resolve to the same permissions.
 */

export const CANONICAL_ROLES = [
  "admin",
  "organization_admin",
  "embryologist",
  "veterinarian",
  "researcher",
  "viewer",
] as const;

export type CanonicalRole = (typeof CANONICAL_ROLES)[number];

/**
 * Map any role string the backend might hand us onto a canonical role.
 * Order matters: the most specific match wins.
 */
export function normalizeRole(role: string | null | undefined): CanonicalRole {
  const r = (role ?? "").trim().toLowerCase();
  if (!r) return "viewer";

  if (r.includes("organization_admin") || r.includes("organization admin")) return "organization_admin";
  if (r.includes("admin")) return "admin";
  // "lab" must be tested before the bare "technician" fallback below, or
  // "lab technician" would resolve to the ET side.
  if (r.includes("embryologist") || r.includes("lab")) return "embryologist";
  if (r.includes("research") || r.includes("analyst") || r.includes("data scientist")) return "researcher";
  if (r.includes("vet") || r.includes("et team") || r.includes("et-team") || r.includes("et_team")) {
    return "veterinarian";
  }
  // A bare "technician" is an ET technician in this dataset — the lab side is
  // always recorded as "embryologist" or "lab …".
  if (r.includes("technician")) return "veterinarian";
  return "viewer";
}

/**
 * Every operational role lands on `/app` — the dashboard reshapes itself per
 * role (see buildRoleConfig in HomepageDashboard), so a lab user gets the
 * laboratory view and a vet gets the recipient view at the same URL. Viewers
 * have no dashboard of their own and go straight to the case list.
 */
export function getRoleLandingPath(role: string | null | undefined): string {
  return normalizeRole(role) === "viewer" ? "/app/cases" : "/app";
}

export function getRoleDisplayName(role: string | null | undefined): string {
  switch (normalizeRole(role)) {
    case "admin":
      return "System Administrator";
    case "organization_admin":
      return "Organization Administrator";
    case "embryologist":
      return "Embryologist / Lab Team";
    case "veterinarian":
      return "Veterinarian / ET Team";
    case "researcher":
      return "Researcher / Data Analyst";
    case "viewer":
    default:
      return "Viewer";
  }
}

type PermissionSet = {
  /** Create and manage users, laboratories and org settings. */
  canManageUsers: boolean;
  /** Read the analytics environment (rates, protocol and donor performance). */
  canViewAnalytics: boolean;
  /** See org-wide data including the data-quality checklist. */
  canViewAllData: boolean;
  /** Write OPU / IVF / embryo records. */
  canEnterLabData: boolean;
  /** Write recipient / transfer / pregnancy-diagnosis records. */
  canEnterETData: boolean;
  /** Use the AI grading tool and record a manual grade. */
  canGradeEmbryos: boolean;
  canEditSettings: boolean;
  canExportReports: boolean;
  /** Model evaluation, dataset explorer, protocol comparison. */
  canViewResearch: boolean;
  /** See the prediction surface. */
  canViewPredictions: boolean;
  /**
   * Generate a prediction. Split out of canEnterETData because asking the
   * model about a candidate transfer is not the same privilege as writing
   * clinical records: it commits nothing, and an embryologist choosing
   * between freezing and transferring an embryo has a genuine use for it.
   * Recording the actual outcome — whether the recipient was pregnant — is
   * an ET-side observation and stays on canEnterETData.
   */
  canRunPredictions: boolean;
};

const VET_PERMISSIONS: PermissionSet = {
  canManageUsers: false,
  canViewAnalytics: false,
  canViewAllData: false,
  canEnterLabData: false,
  canEnterETData: true,
  canGradeEmbryos: false,
  canEditSettings: false,
  canExportReports: true,
  canViewResearch: false,
  canViewPredictions: true,
  canRunPredictions: true,
};

const ADMIN_PERMISSIONS: PermissionSet = {
  canManageUsers: true,
  canViewAnalytics: true,
  canViewAllData: true,
  canEnterLabData: true,
  canEnterETData: true,
  canGradeEmbryos: true,
  canEditSettings: true,
  canExportReports: true,
  canViewResearch: true,
  canViewPredictions: true,
  canRunPredictions: true,
};

export const ROLE_PERMISSIONS: Record<CanonicalRole, PermissionSet> & {
  /** Legacy alias kept so imported `et team` accounts resolve. */
  "et team": PermissionSet;
} = {
  admin: ADMIN_PERMISSIONS,

  // Matches how organizations.py already treats organization_admin, and the
  // backend's LAB_WRITE_ROLES / ET_WRITE_ROLES groupings.
  organization_admin: ADMIN_PERMISSIONS,

  embryologist: {
    canManageUsers: false,
    canViewAnalytics: false,
    canViewAllData: false,
    canEnterLabData: true,
    canEnterETData: false,
    canGradeEmbryos: true,
    canEditSettings: false,
    canExportReports: true,
    canViewResearch: false,
    canViewPredictions: true,
    // Can ask the model about a candidate transfer — useful when deciding
    // whether to freeze or transfer an embryo — but cannot record whether the
    // recipient became pregnant, which is an ET-side observation.
    canRunPredictions: true,
  },

  veterinarian: VET_PERMISSIONS,

  // Reads everything, writes nothing. The research role exists to analyse
  // outcomes and evaluate models, not to edit clinical records — so every
  // write flag is false while the analysis surfaces are all open.
  researcher: {
    canManageUsers: false,
    canViewAnalytics: true,
    canViewAllData: true,
    canEnterLabData: false,
    canEnterETData: false,
    canGradeEmbryos: false,
    canEditSettings: false,
    canExportReports: true,
    canViewResearch: true,
    canViewPredictions: true,
    // Read-only by definition: the research role analyses outcomes, it does
    // not create records of any kind.
    canRunPredictions: false,
  },

  viewer: {
    canManageUsers: false,
    canViewAnalytics: false,
    canViewAllData: false,
    canEnterLabData: false,
    canEnterETData: false,
    canGradeEmbryos: false,
    canEditSettings: false,
    canExportReports: false,
    canViewResearch: false,
    canViewPredictions: false,
    canRunPredictions: false,
  },

  "et team": VET_PERMISSIONS,
};

/** Resolve a raw backend role string straight to its permission set. */
export function getPermissions(role: string | null | undefined): PermissionSet {
  return ROLE_PERMISSIONS[normalizeRole(role)];
}
