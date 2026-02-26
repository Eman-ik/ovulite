import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Activity, Database, Brain, CheckCircle } from "lucide-react";

const stats = [
  {
    title: "Total ET Records",
    value: "488",
    description: "Historical transfers",
    icon: Database,
  },
  {
    title: "Pregnancy Rate",
    value: "28.8%",
    description: "136/472 confirmed",
    icon: Activity,
  },
  {
    title: "Embryo Images",
    value: "482",
    description: "Blastocyst images",
    icon: Brain,
  },
  {
    title: "System Status",
    value: "Online",
    description: "Phase 0 — Foundation",
    icon: CheckCircle,
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Welcome to Ovulite — AI-Driven Reproductive Intelligence System
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.title}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Status card */}
      <Card>
        <CardHeader>
          <CardTitle>Phase 0 — Foundation Complete</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>
              The foundation scaffold is in place: Docker infrastructure,
              database schema, frontend skeleton, and authentication system.
            </p>
            <p>
              Next: Data intake & validation (Phase 1) — CSV ingestion,
              CRUD APIs, and data entry forms.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
