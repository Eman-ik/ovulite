/**
 * Ovulite's four roles. Each one is a job someone does here.
 *
 *   admin         runs the system        — users, settings, every module, reports
 *   embryologist  runs the laboratory    — OPU, IVF, IVM, grading, lab QC
 *   veterinarian  runs recipients and ET — sync, protocols, transfers, PD, outcomes
 *   researcher    analyses the data      — read-only; dashboard, analytics, models
 *
 * Mirrors CANONICAL_ROLES and the *_ROLES tuples in backend/app/auth/dependencies.py.
 * Legacy strings are mapped, never shown: "et team" is the ET dataset's spelling of
 * veterinarian, "organization_admin" is admin, and "viewer" is researcher.
 */

export const CANONICAL_ROLES = [
  "admin",
  "embryologist",
  "veterinarian",
  "researcher",
] as const;

export type CanonicalRole = (typeof CANONICAL_ROLES)[number];

const LEGACY_ALIASES: Record<string, CanonicalRole> = {
  organization_admin: "admin",
  "organization admin": "admin",
  "et team": "veterinarian",
  "et-team": "veterinarian",
  et_team: "veterinarian",
  viewer: "researcher",
};

/**
 * Map any role string the backend might hand us onto one of the four roles.
 * An unrecognised value falls to the least privilege available, researcher,
 * which is read-only — never to a role with writes.
 */
export function normalizeRole(role: string | null | undefined): CanonicalRole {
  const r = (role ?? "").trim().toLowerCase();
  if (!r) return "researcher";
  if ((CANONICAL_ROLES as readonly string[]).includes(r)) return r as CanonicalRole;
  if (r in LEGACY_ALIASES) return LEGACY_ALIASES[r];
  // Free-text roles from older imports: match on the job, not the exact string.
  if (r.includes("admin")) return "admin";
  if (r.includes("embryologist") || r.includes("lab")) return "embryologist";
  if (r.includes("vet") || r.includes("technician")) return "veterinarian";
  return "researcher";
}

/**
 * Every role lands on `/app`; the dashboard reshapes itself per role.
 */
export function getRoleLandingPath(): string {
  return "/app";
}

export function getRoleDisplayName(role: string | null | undefined): string {
  switch (normalizeRole(role)) {
    case "admin":
      return "Admin";
    case "embryologist":
      return "Embryologist";
    case "veterinarian":
      return "Veterinarian";
    case "researcher":
    default:
      return "Researcher";
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
   * Generate a prediction. Separate from writing clinical records: asking the
   * model about a candidate transfer commits nothing, and an embryologist
   * choosing between freezing and transferring has a real use for it. Recording
   * the outcome stays on canEnterETData.
   */
  canRunPredictions: boolean;
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

export const ROLE_PERMISSIONS: Record<CanonicalRole, PermissionSet> = {
  admin: ADMIN_PERMISSIONS,

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
    canRunPredictions: true,
  },

  veterinarian: {
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
  },

  // Reads the analysis surfaces and writes nothing clinical. Every write flag is
  // false by definition: this role analyses outcomes, it does not record them.
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
    canRunPredictions: false,
  },
};

/** Resolve a raw backend role string straight to its permission set. */
export function getPermissions(role: string | null | undefined): PermissionSet {
  return ROLE_PERMISSIONS[normalizeRole(role)];
}
