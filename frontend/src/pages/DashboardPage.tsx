import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  Activity, Database, Brain, Users, 
  Search
} from "lucide-react";

type KPIStat = {
  title: string;
  value: string;
  description: string;
  icon: typeof Activity;
};

export default function DashboardPage() {
  const [timeRange, setTimeRange] = useState<"Year" | "Month" | "Week">("Year");

  const stats: KPIStat[] = [
    {
      title: "Transfer Cycles",
      value: "1,284",
      description: "Completed ET cycles in current period",
      icon: Activity,
    },
    {
      title: "Data Records",
      value: "24.1K",
      description: "Processed outcomes and biomarker entries",
      icon: Database,
    },
    {
      title: "Model Confidence",
      value: "87.3%",
      description: "Prediction consistency across validation folds",
      icon: Brain,
    },
    {
      title: "Active Users",
      value: "39",
      description: "Clinicians and lab technicians online",
      icon: Users,
    },
  ];

  return (
    <div className="min-h-screen bg-transparent text-slate-200 p-6 space-y-8">
      
      {/* Top Header Bar */}
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-white">Analytics report</h1>
          <p className="text-sm text-slate-500">Analytics report from 2024 to 2025</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input 
              className="bg-black/20 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#00d2ff] backdrop-blur-sm" 
              placeholder="Search dashboard..." 
            />
          </div>
          <button className="bg-[#ff0096] hover:bg-[#ff0096]/80 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 glow-shadow-pink transition-all border border-[#ff0096]/50">
            + Create report
          </button>
        </div>
      </header>

      {/* High-Level KPI Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {stats.map((stat, i) => (
          <div key={stat.title} className="glass-panel p-5 rounded-2xl group hover:-translate-y-1 transition-all">
            <div className="flex justify-between items-start mb-2">
              <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">{stat.title}</span>
              <stat.icon className={`w-4 h-4 ${i % 2 === 0 ? 'text-[#ff0096]' : 'text-[#00d2ff]'}`} />
            </div>
            <div className="flex items-end gap-2">
              <span className="text-2xl font-bold text-white tracking-tight">{stat.value}</span>
              <span className="text-[10px] text-[#00ffcc] mb-1 font-bold">+12.4%</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">{stat.description}</p>
          </div>
        ))}
      </div>

      {/* Main Analytics Section */}
      <div className="grid grid-cols-12 gap-6">
        
        {/* Large Chart Area (Total Balance / Trends) */}
        <Card className="col-span-12 lg:col-span-8 glass-panel border-white/10 rounded-2xl overflow-hidden bg-transparent">
          <CardHeader className="flex flex-row items-center justify-between border-b border-white/10">
            <div>
              <CardTitle className="text-slate-400 text-sm font-normal uppercase tracking-wider">Reproductive Trends</CardTitle>
              <div className="text-2xl font-bold text-white">$240.8K <span className="text-sm text-[#00ffcc] font-normal ml-2 glow-shadow-cyan">↑ 24.5%</span></div>
            </div>
            <div className="flex gap-2 bg-black/40 p-1 rounded-lg border border-white/10 backdrop-blur-md">
              {(["Year", "Month", "Week"] as const).map((t) => (
                <button
                  key={t}
                  className={`px-3 py-1 text-[10px] rounded-md transition-all ${t === timeRange ? "bg-[#00d2ff]/20 text-[#00d2ff] border border-[#00d2ff]/50 glow-shadow-blue" : "text-slate-500 hover:text-white"}`}
                  onClick={() => setTimeRange(t)}
                  type="button"
                >
                  {t}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent className="h-[300px] pt-6">
             {/* Replace with actual Recharts component for the wave effect */}
             <div className="w-full h-full flex items-center justify-center border border-dashed border-white/20 rounded-lg text-slate-500 bg-white/5">
                [Interactive Area Chart Component Placeholder]
             </div>
          </CardContent>
        </Card>

        {/* Right Side Small Widget (System Health / Efficiency) */}
        <Card className="col-span-12 lg:col-span-4 glass-panel border-white/10 rounded-2xl bg-transparent">
          <CardHeader>
            <CardTitle className="text-sm font-medium uppercase tracking-wider">Efficiency</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center py-6">
            {/* Circular Progress Ring */}
            <div className="relative w-32 h-32 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90 filter drop-shadow-[0_0_8px_rgba(157,0,255,0.5)]">
                <circle cx="64" cy="64" r="58" stroke="rgba(255,255,255,0.05)" strokeWidth="8" fill="transparent" />
                <circle cx="64" cy="64" r="58" stroke="#9d00ff" strokeWidth="8" fill="transparent" strokeDasharray="364" strokeDashoffset="100" strokeLinecap="round" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-white tracking-tight">78%</span>
                <span className="text-[10px] text-[#00d2ff] uppercase tracking-wider font-bold">Utilization</span>
              </div>
            </div>
            <div className="mt-6 w-full space-y-3">
               <div className="flex justify-between text-xs bg-black/20 p-2 rounded-lg border border-white/5"><span className="text-slate-400">Fresh Success</span><span className="text-[#00ffcc] font-bold">82%</span></div>
               <div className="flex justify-between text-xs bg-black/20 p-2 rounded-lg border border-white/5"><span className="text-slate-400">Frozen Success</span><span className="text-white font-bold">64%</span></div>
            </div>
          </CardContent>
        </Card>

      </div>

      {/* Bottom Row - Detailed Tables / List */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 glass-panel border-white/10 rounded-2xl bg-transparent">
          <CardHeader className="flex flex-row items-center justify-between border-b border-white/10 pb-4">
            <CardTitle className="text-sm font-medium uppercase tracking-wider">Recent Records</CardTitle>
            <button className="text-[#00d2ff] text-xs font-bold uppercase tracking-widest hover:text-white transition-colors">View all</button>
          </CardHeader>
          <CardContent className="pt-4">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-slate-500 border-b border-white/10 uppercase text-xs tracking-wider">
                  <th className="pb-3 font-medium">Entity</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Date</th>
                </tr>
              </thead>
              <tbody className="text-slate-300">
                <tr className="border-b border-white/5 group hover:bg-white/[0.02] transition-colors">
                  <td className="py-4 flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#ff0096] to-[#9d00ff] p-[1px] glow-shadow-pink">
                       <div className="w-full h-full bg-[#05060f] rounded-full" />
                    </div>
                    <span className="font-semibold tracking-tight text-white">Donor #829</span>
                  </td>
                  <td className="py-4"><span className="px-2 py-1 bg-[#00ffcc]/10 text-[#00ffcc] border border-[#00ffcc]/30 rounded text-[10px] font-bold tracking-widest uppercase">ACTIVE</span></td>
                  <td className="py-4 text-slate-500 text-xs font-mono">Oct 24, 2025</td>
                </tr>
                {/* Repeat rows */}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}