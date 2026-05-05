import React, { useMemo } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { getRoleDisplayName, ROLE_PERMISSIONS } from "@/lib/roleRoutes";
import { BarChart3, Users, Database, Zap, Shield, Activity } from "lucide-react";

export function RoleBasedDashboard() {
  const { user } = useAuth();
  
  const roleInfo = useMemo(() => {
    const role = user?.role?.toLowerCase() || "viewer";
    const permissions = ROLE_PERMISSIONS[role as keyof typeof ROLE_PERMISSIONS] || ROLE_PERMISSIONS.viewer;
    
    return {
      role,
      displayName: getRoleDisplayName(user?.role),
      permissions,
    };
  }, [user?.role]);

  const getDashboardContent = () => {
    switch (roleInfo.role) {
      case "admin":
        return (
          <div className="space-y-6">
            {/* Admin Dashboard Header */}
            <div className="rounded-xl bg-gradient-to-r from-blue-600 to-blue-800 p-8 text-white">
              <h1 className="text-4xl font-bold mb-2">Admin Control Panel</h1>
              <p className="text-blue-100">Full system overview and management capabilities</p>
            </div>

            {/* Admin KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <KPICard
                icon={<Users className="h-8 w-8 text-blue-600" />}
                title="Total Users"
                value="12"
                subtitle="Active accounts"/>
              <KPICard
                icon={<Database className="h-8 w-8 text-green-600" />}
                title="Embryo Transfers"
                value="847"
                subtitle="This season"/>
              <KPICard
                icon={<Activity className="h-8 w-8 text-purple-600" />}
                title="Pregnancy Rate"
                value="68.5%"
                subtitle="Current cycle"/>
              <KPICard
                icon={<Zap className="h-8 w-8 text-amber-600" />}
                title="Model Confidence"
                value="94.2%"
                subtitle="AI predictions"/>
            </div>

            {/* Admin Features */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FeatureSection
                title="User Management"
                description="Create, manage, and monitor user accounts and roles"
                items={["Create users", "Assign roles", "Reset passwords", "Audit logs"]}
              />
              <FeatureSection
                title="Analytics & Reports"
                description="Comprehensive system analytics and custom reports"
                items={["Farm analytics", "Lab performance", "Vet efficiency", "Export reports"]}
              />
              <FeatureSection
                title="System Settings"
                description="Configure protocols and system preferences"
                items={["Protocol management", "System config", "Data retention", "Backup & restore"]}
              />
              <FeatureSection
                title="Audit & Compliance"
                description="Track all system activities for compliance"
                items={["Activity logs", "Data changes", "User actions", "Compliance reports"]}
              />
            </div>
          </div>
        );

      case "embryologist":
        return (
          <div className="space-y-6">
            {/* Lab Tech Dashboard Header */}
            <div className="rounded-xl bg-gradient-to-r from-green-600 to-green-800 p-8 text-white">
              <h1 className="text-4xl font-bold mb-2">Lab Dashboard</h1>
              <p className="text-green-100">Embryo production, grading, and lab quality control</p>
            </div>

            {/* Lab KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <KPICard
                icon={<Database className="h-8 w-8 text-green-600" />}
                title="Today's OPU"
                value="24"
                subtitle="Oocytes collected"/>
              <KPICard
                icon={<Zap className="h-8 w-8 text-amber-600" />}
                title="Embryos Graded"
                value="156"
                subtitle="This week"/>
              <KPICard
                icon={<Activity className="h-8 w-8 text-blue-600" />}
                title="Lab QC Alerts"
                value="2"
                subtitle="Requires attention"/>
              <KPICard
                icon={<Shield className="h-8 w-8 text-red-600" />}
                title="Cold Chain Temp"
                value="5.2°C"
                subtitle="Within specification"/>
            </div>

            {/* Lab Features */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FeatureSection
                title="Data Entry & Records"
                description="Record donor, OPU, and embryo data"
                items={["Donor information", "OPU records", "Embryo details", "Inventory tracking"]}
              />
              <FeatureSection
                title="Embryo Grading"
                description="Grade embryos and generate AI analysis"
                items={["Upload images", "Manual grading", "AI grade & confidence", "Batch processing"]}
              />
              <FeatureSection
                title="Lab Quality Control"
                description="Monitor and manage lab KPIs"
                items={["Temperature alerts", "Media lot tracking", "Contamination logs", "Performance metrics"]}
              />
              <FeatureSection
                title="Lab Reports"
                description="Generate lab-specific reports"
                items={["Daily summary", "Weekly KPIs", "Quality reports", "Protocol analysis"]}
              />
            </div>
          </div>
        );

      case "et team":
        return (
          <div className="space-y-6">
            {/* ET Tech Dashboard Header */}
            <div className="rounded-xl bg-gradient-to-r from-purple-600 to-purple-800 p-8 text-white">
              <h1 className="text-4xl font-bold mb-2">ET Technician Dashboard</h1>
              <p className="text-purple-100">Recipient management and embryo transfer operations</p>
            </div>

            {/* ET KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <KPICard
                icon={<Database className="h-8 w-8 text-purple-600" />}
                title="Transfers This Week"
                value="18"
                subtitle="Scheduled procedures"/>
              <KPICard
                icon={<Activity className="h-8 w-8 text-green-600" />}
                title="Success Rate"
                value="71.2%"
                subtitle="30-day pregnancy"/>
              <KPICard
                icon={<Zap className="h-8 w-8 text-amber-600" />}
                title="Pending Outcomes"
                value="34"
                subtitle="Awaiting results"/>
              <KPICard
                icon={<Shield className="h-8 w-8 text-blue-600" />}
                title="My Cases"
                value="156"
                subtitle="Assigned to me"/>
            </div>

            {/* ET Features */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FeatureSection
                title="Recipient Management"
                description="Add and manage recipient animal records"
                items={["New recipient", "Breed info", "Lactation status", "Health history"]}
              />
              <FeatureSection
                title="Synchronization"
                description="Track estrus synchronization protocols"
                items={["Protocol selection", "CL assessment", "P4 levels", "Timeline tracking"]}
              />
              <FeatureSection
                title="Embryo Transfer"
                description="Record transfer procedures"
                items={["Select embryo", "Transfer date", "Technique notes", "Immediate outcome"]}
              />
              <FeatureSection
                title="Pregnancy Outcome"
                description="Record pregnancy check results"
                items={["Ultrasound results", "Day 30/45 checks", "Pregnancy confirmation", "Data history"]}
              />
            </div>
          </div>
        );

      default:
        return (
          <div className="rounded-xl bg-gray-100 p-8">
            <p className="text-gray-600">Welcome to Ovulite. Your role does not have a specific dashboard yet.</p>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        {/* User Info Banner */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Welcome, {user?.full_name || user?.username}!</h2>
            <p className="text-gray-600">Role: <span className="font-semibold text-gray-900">{roleInfo.displayName}</span></p>
          </div>
          <div className="rounded-lg bg-white p-4 shadow-sm">
            <BarChart3 className="h-8 w-8 text-blue-600" />
          </div>
        </div>

        {/* Dashboard Content */}
        {getDashboardContent()}
      </div>
    </div>
  );
}

function KPICard({
  icon,
  title,
  value,
  subtitle,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  subtitle: string;
}) {
  return (
    <div className="rounded-lg bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div>{icon}</div>
      </div>
      <h3 className="text-gray-600 text-sm font-medium mb-1">{title}</h3>
      <p className="text-2xl font-bold text-gray-900 mb-2">{value}</p>
      <p className="text-xs text-gray-500">{subtitle}</p>
    </div>
  );
}

function FeatureSection({
  title,
  description,
  items,
}: {
  title: string;
  description: string;
  items: string[];
}) {
  return (
    <div className="rounded-lg bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-600 mb-4">{description}</p>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex items-center text-sm text-gray-700">
            <span className="inline-block w-2 h-2 bg-blue-600 rounded-full mr-3" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
