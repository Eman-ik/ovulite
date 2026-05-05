export function getRoleLandingPath(role: string | null | undefined): string {
  const normalized = (role ?? "").trim().toLowerCase();

  if (!normalized) return "/app";
  
  // Admin dashboard
  if (normalized.includes("admin")) return "/app/analytics";
  
  // Lab/Embryologist dashboard
  if (normalized.includes("embryologist")) return "/app/embryo-grading";
  
  // ET Team/Technician/Vet dashboard
  if (normalized.includes("et team") || normalized.includes("et-team") || normalized.includes("vet") || normalized.includes("veterinarian")) {
    return "/app/predictions";
  }
  
  // Technician/Lab staff - data entry
  if (normalized.includes("technician") || normalized.includes("lab") || normalized.includes("staff")) {
    return "/app/data-entry";
  }
  
  // Viewer - cases only
  if (normalized.includes("viewer")) return "/app/cases";

  // Default fallback
  return "/app";
}

export function getRoleDisplayName(role: string | null | undefined): string {
  const normalized = (role ?? "").trim().toLowerCase();
  
  if (normalized.includes("admin")) return "System Administrator";
  if (normalized.includes("embryologist")) return "Lab Technician / Embryologist";
  if (normalized.includes("et team")) return "ET Technician / Veterinarian";
  if (normalized.includes("veterinarian")) return "Veterinarian";
  if (normalized.includes("technician")) return "Technician";
  if (normalized.includes("viewer")) return "Viewer";
  
  return "User";
}

export const ROLE_PERMISSIONS = {
  admin: {
    canManageUsers: true,
    canViewAnalytics: true,
    canViewAllData: true,
    canEnterLabData: true,
    canEnterETData: true,
    canGradeEmbryos: true,
    canEditSettings: true,
    canExportReports: true,
  },
  embryologist: {
    canManageUsers: false,
    canViewAnalytics: false,
    canViewAllData: false,
    canEnterLabData: true,
    canEnterETData: false,
    canGradeEmbryos: true,
    canEditSettings: false,
    canExportReports: true,
  },
  "et team": {
    canManageUsers: false,
    canViewAnalytics: false,
    canViewAllData: false,
    canEnterLabData: false,
    canEnterETData: true,
    canGradeEmbryos: false,
    canEditSettings: false,
    canExportReports: true,
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
  },
};
