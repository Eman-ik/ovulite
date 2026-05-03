import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  Menu,
  X,
  Sparkles,
  ChevronRight,
  Microscope,
  Brain,
  GitMerge,
  FlaskConical,
  BarChart3,
  Database,
  ShieldCheck,
  ScanLine,
  Beaker,
  Users,
  Dna,
  Activity,
  CircleCheckBig,
  ArrowUpRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const navLinks = ["Home", "Product", "Features", "Science", "Use Cases", "Contact"];

const valueCards = [
  {
    title: "Predict Outcomes",
    body: "Use ET, progesterone, CL, blood flow, and embryo metadata to estimate pregnancy success probability.",
    icon: Activity,
  },
  {
    title: "Grade with AI",
    body: "Support embryo quality assessment using image plus metadata fusion with transparent confidence indicators.",
    icon: Microscope,
  },
  {
    title: "Act with Traceability",
    body: "Track protocols, validate records, and connect every decision to biological and operational context.",
    icon: ShieldCheck,
  },
];

const features = [
  {
    title: "Pregnancy Success Prediction",
    body: "Estimate transfer-level likelihood with confidence-aware outputs built for biological interpretation.",
    icon: Brain,
    metric: "Confidence-Aware",
  },
  {
    title: "AI Embryo Grading",
    body: "Combine image and metadata intelligence to support reproducible grading workflows.",
    icon: ScanLine,
    metric: "Image + Metadata",
  },
  {
    title: "Embryo-Recipient Matching",
    body: "Prioritize biologically aligned matching recommendations with explicit rationale.",
    icon: GitMerge,
    metric: "Match Quality Index",
  },
  {
    title: "Protocol Effectiveness Analytics",
    body: "Compare protocol outcomes across programs, cohorts, and operational timelines.",
    icon: BarChart3,
    metric: "Protocol Delta",
  },
  {
    title: "Data Intake and Validation",
    body: "Standardize records, surface quality gaps, and keep analysis pipelines decision-ready.",
    icon: Database,
    metric: "Validation Layer",
  },
];

const trustPrinciples = [
  "Biology-first explanations",
  "Explicit uncertainty awareness",
  "Outcome accountability",
  "Human-in-the-loop decision support",
  "Practical lab workflow impact",
];

const useCases = [
  {
    title: "Embryology Labs",
    body: "For embryo grading support, image review, and quality decision workflows.",
    icon: Beaker,
  },
  {
    title: "ET / Transfer Programs",
    body: "For matching embryos to recipients and improving transfer outcomes.",
    icon: Dna,
  },
  {
    title: "Research and Analytics Teams",
    body: "For protocol comparison, trend analysis, and traceable reproductive data systems.",
    icon: Users,
  },
];

const impact = [
  { value: "94%", label: "Data Validation Readiness" },
  { value: "82%", label: "Confidence-Aware Review Coverage" },
  { value: "5", label: "Core Intelligence Modules" },
  { value: "1", label: "Unified Reproductive Data Layer" },
];

export default function OvuliteLandingPage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <div
      className="min-h-screen overflow-x-hidden text-[#3a0d1d]"
      style={{
        fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif",
        background:
          "radial-gradient(circle at 12% -10%, rgba(126,242,177,0.30), transparent 42%), radial-gradient(circle at 88% 8%, rgba(168,213,186,0.35), transparent 40%), linear-gradient(135deg, #fff3f8 0%, #d9efe1 28%, #cbe7d8 60%, #b8ddca 100%)",
      }}
    >
      <BackgroundOrbs />

      <header className="fixed inset-x-0 top-0 z-50 px-3 pt-3 sm:px-5 lg:px-8">
        <div className="mx-auto max-w-7xl rounded-2xl border border-white/50 bg-white/35 px-4 py-3 shadow-[0_10px_40px_rgba(11,61,46,0.14)] backdrop-blur-2xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#e7a0b9] to-[#7a2341] text-[#4b0f25] shadow-md">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <div className="text-sm font-extrabold tracking-[0.16em] text-[#4b0f25]">OVULITE</div>
                <div className="text-[10px] uppercase tracking-[0.22em] text-[#7a606b]">Embryo Intelligence</div>
              </div>
            </div>

            <nav className="hidden items-center gap-7 lg:flex">
              {navLinks.map((link) => (
                <a key={link} href="#" className="text-sm font-medium text-[#5a1a33] transition hover:text-[#4b0f25]">
                  {link}
                </a>
              ))}
            </nav>

            <div className="hidden items-center gap-2 sm:flex">
              <Button variant="ghost" className="text-[#4b0f25] hover:bg-white/40" onClick={() => navigate("/login")}>
                Log In
              </Button>
              <Button className="bg-gradient-to-r from-[#7a2341] to-[#9b3553] text-[#fff3f8] hover:brightness-110">
                Request Demo
              </Button>
            </div>

            <button
              type="button"
              className="rounded-lg p-2 text-[#4b0f25] hover:bg-white/30 lg:hidden"
              onClick={() => setMobileOpen((v) => !v)}
              aria-label="Toggle navigation"
            >
              {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>

          {mobileOpen && (
            <div className="overflow-hidden lg:hidden">
              <div className="mt-3 space-y-2 border-t border-white/40 pt-3">
                {navLinks.map((link) => (
                  <a key={link} href="#" className="block rounded-lg px-3 py-2 text-sm font-medium text-[#6b2140] hover:bg-white/30">
                    {link}
                  </a>
                ))}
                <div className="flex gap-2 pt-2">
                  <Button variant="outline" className="flex-1 border-white/60 bg-white/30 text-[#4b0f25]">
                    Log In
                  </Button>
                  <Button className="flex-1 bg-gradient-to-r from-[#7a2341] to-[#9b3553] text-[#fff3f8]">
                    Request Demo
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </header>

      <main className="relative mx-auto max-w-7xl px-4 pb-20 pt-32 sm:px-6 lg:px-8">
        <section className="grid items-center gap-10 lg:grid-cols-2 lg:gap-14">
          <div className="space-y-6">
            <div>
              <Badge className="border-white/60 bg-white/45 px-3 py-1 text-[#4b0f25] shadow-sm">
                Premium Biotech AI Platform
              </Badge>
            </div>

            <h1 className="max-w-xl text-4xl font-extrabold leading-tight tracking-tight text-[#3a0d1d] sm:text-5xl lg:text-[3.4rem]">
              AI-powered embryo intelligence for traceable reproductive decisions
            </h1>

            <p className="max-w-xl text-base leading-relaxed text-[#7a606b] sm:text-lg">
              Ovulite helps IVF and embryo transfer programs predict outcomes, grade embryos, match recipients,
              and improve protocol performance through biology-first AI.
            </p>

            <div className="flex flex-wrap gap-3">
              <Button className="h-11 bg-gradient-to-r from-[#4b0f25] to-[#7a2341] px-6 text-[#fff3f8] hover:brightness-110">
                Request Demo
              </Button>
              <Button variant="outline" className="h-11 border-white/70 bg-white/35 px-6 text-[#4b0f25] hover:bg-white/50" onClick={() => navigate("/login")}>
                Explore Platform <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            </div>

            <p className="text-sm text-[#7a606b]">
              Built for embryology labs, reproductive programs, and data-driven decision support.
            </p>

            <div className="flex flex-wrap gap-2">
              {[
                "Pregnancy Prediction",
                "AI Embryo Grading",
                "Recipient Matching",
              ].map((chip) => (
                <Badge key={chip} className="rounded-full border border-white/60 bg-white/40 px-3 py-1 text-[#4b0f25]">
                  {chip}
                </Badge>
              ))}
            </div>
          </div>

          <div className="relative">
            <HeroPreview />
          </div>
        </section>

        <SectionWrap className="mt-24" title="From embryo data to explainable reproductive insight">
          <p className="mx-auto max-w-3xl text-center text-base leading-relaxed text-[#7a606b] sm:text-lg">
            Ovulite is a decision-support system that combines embryo image analysis, recipient biology, ET records,
            and protocol history into actionable intelligence for reproductive teams.
          </p>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {valueCards.map((item) => (
              <div key={item.title}>
                <GlassCard className="h-full p-6">
                  <item.icon className="mb-4 h-5 w-5 text-[#7a2341]" />
                  <h3 className="text-lg font-semibold text-[#451122]">{item.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-[#7a606b]">{item.body}</p>
                </GlassCard>
              </div>
            ))}
          </div>
        </SectionWrap>

        <SectionWrap className="mt-24" title="Designed for modern embryo intelligence workflows">
          <div className="mt-10 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            {features.map((feature) => (
              <div key={feature.title}>
                <GlassCard className="group h-full p-5 transition duration-300 hover:-translate-y-1 hover:border-[#e7a0b9]/70">
                  <div className="mb-4 inline-flex rounded-xl bg-white/50 p-2">
                    <feature.icon className="h-4 w-4 text-[#7a2341]" />
                  </div>
                  <h3 className="text-base font-semibold text-[#4a1327]">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-[#7a606b]">{feature.body}</p>
                  <div className="mt-4 inline-flex items-center rounded-full border border-white/60 bg-white/35 px-2.5 py-1 text-[11px] font-medium text-[#7a2e4d]">
                    {feature.metric}
                  </div>
                </GlassCard>
              </div>
            ))}
          </div>
        </SectionWrap>

        <SectionWrap className="mt-24" title="A command center for reproductive performance">
          <div className="relative mt-10">
            <GlassCard className="relative overflow-hidden p-6 sm:p-8">
              <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-3">
                    {[
                      { label: "Active Cases", value: "128" },
                      { label: "Prediction Confidence", value: "82.4%" },
                      { label: "Validated Records", value: "12,402" },
                    ].map((kpi) => (
                      <div key={kpi.label} className="rounded-xl border border-white/50 bg-white/35 p-3">
                        <p className="text-[11px] uppercase tracking-[0.1em] text-[#7a606b]">{kpi.label}</p>
                        <p className="mt-1 text-xl font-bold text-[#56192f]">{kpi.value}</p>
                      </div>
                    ))}
                  </div>

                  <div className="rounded-xl border border-white/45 bg-white/30 p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <p className="text-sm font-semibold text-[#581a31]">Protocol Outcome Signal</p>
                      <span className="text-xs text-[#7a606b]">Last 12 cycles</span>
                    </div>
                    <div className="flex h-20 items-end gap-1.5">
                      {[34, 42, 39, 50, 46, 58, 62, 57, 66, 71, 68, 76].map((h, i) => (
                        <div
                          key={i}
                          style={{ height: `${h}%` }}
                          className="w-full rounded-t bg-gradient-to-t from-[#7a2341] to-[#e7a0b9]"
                        />
                      ))}
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-white/45 bg-white/28 p-4">
                  <p className="text-sm font-semibold text-[#581a31]">Embryo Grading Queue</p>
                  <div className="mt-3 space-y-2.5">
                    {["E-147", "E-182", "E-211"].map((id, idx) => (
                      <div key={id} className="rounded-lg border border-white/45 bg-white/35 p-3">
                        <div className="flex items-center justify-between text-sm font-medium text-[#56192f]">
                          <span>{id}</span>
                          <span className="text-[#7a2341]">{92 - idx * 5}% conf</span>
                        </div>
                        <p className="mt-1 text-xs text-[#7a606b]">Day 7 · Grade A support signal</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </GlassCard>

            <div className="pointer-events-none absolute -left-1 top-5 hidden rounded-full border border-white/60 bg-white/50 px-3 py-1 text-xs text-[#732947] shadow-sm lg:block">
              Confidence-aware predictions
            </div>
            <div className="pointer-events-none absolute -right-2 bottom-20 hidden rounded-full border border-white/60 bg-white/50 px-3 py-1 text-xs text-[#732947] shadow-sm lg:block">
              Biology-first analysis
            </div>
            <div className="pointer-events-none absolute left-24 -bottom-2 hidden rounded-full border border-white/60 bg-white/50 px-3 py-1 text-xs text-[#732947] shadow-sm lg:block">
              Traceable recommendations
            </div>
          </div>
        </SectionWrap>

        <SectionWrap className="mt-24" title="Built around biology, not black-box automation">
          <div className="mt-10 grid gap-5 lg:grid-cols-2">
            <GlassCard className="p-7">
              <p className="text-base leading-relaxed text-[#6b2a41] sm:text-lg">
                Ovulite is engineered to support embryologists and clinical teams with measurable intelligence,
                transparent confidence ranges, and traceable reasoning. The platform augments decision quality while
                preserving expert oversight at every critical step.
              </p>
            </GlassCard>

            <div className="space-y-3">
              {trustPrinciples.map((item) => (
                <GlassCard key={item} className="flex items-center gap-3 p-4">
                  <CircleCheckBig className="h-4 w-4 text-[#7a2341]" />
                  <p className="text-sm font-medium text-[#163329]">{item}</p>
                </GlassCard>
              ))}
            </div>
          </div>
        </SectionWrap>

        <SectionWrap className="mt-24" title="Made for reproductive teams that need more than spreadsheets">
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {useCases.map((item) => (
              <div key={item.title}>
                <GlassCard className="h-full p-6">
                  <item.icon className="mb-4 h-5 w-5 text-[#7a2341]" />
                  <h3 className="text-lg font-semibold text-[#4a1327]">{item.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-[#7a606b]">{item.body}</p>
                </GlassCard>
              </div>
            ))}
          </div>
        </SectionWrap>

        <SectionWrap className="mt-24" title="Operational impact in one intelligence layer">
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {impact.map((item) => (
              <div key={item.label}>
                <GlassCard className="p-5 text-center">
                  <p className="text-3xl font-extrabold text-[#4b0f25]">{item.value}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.08em] text-[#7a606b]">{item.label}</p>
                </GlassCard>
              </div>
            ))}
          </div>
        </SectionWrap>

        <SectionWrap className="mt-24" title="The future of reproductive intelligence is explainable">
          <GlassCard className="mt-10 p-7 sm:p-10">
            <p className="mx-auto max-w-4xl text-center text-lg leading-relaxed text-[#6b2140] sm:text-xl">
              "Ovulite exists to connect embryology, clinical reasoning, and machine intelligence into one traceable
              operating system for better reproductive decisions. We are building for teams who value rigor, clarity,
              and outcomes that can be explained with biological confidence."
            </p>
          </GlassCard>
        </SectionWrap>

        <section className="relative mt-24 overflow-hidden rounded-[2rem] border border-white/55 bg-white/28 px-6 py-12 shadow-[0_28px_70px_rgba(11,61,46,0.16)] backdrop-blur-2xl sm:px-10 sm:py-16">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(126,242,177,0.40),transparent_46%),radial-gradient(circle_at_85%_85%,rgba(31,111,94,0.30),transparent_45%)]" />
          <div className="relative z-10 text-center">
            <h2 className="mx-auto max-w-4xl text-3xl font-bold tracking-tight text-[#3a0d1d] sm:text-4xl">
              Bring intelligence, traceability, and clarity to embryo decision workflows
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-[#7a606b]">
              Launch a premium decision-support layer across your reproductive program with confidence-aware AI and
              accountable biological insight.
            </p>
            <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
              <Button className="h-11 bg-gradient-to-r from-[#4b0f25] to-[#7a2341] px-6 text-[#fff3f8] hover:brightness-110">
                Request Demo
              </Button>
              <Button variant="outline" className="h-11 border-white/65 bg-white/40 px-6 text-[#4b0f25] hover:bg-white/55" onClick={() => navigate("/login")}>
                Get Started <ArrowUpRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        </section>
      </main>

      <footer className="mt-16 border-t border-white/50 bg-white/28 px-4 py-10 backdrop-blur-xl sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-extrabold tracking-[0.16em] text-[#4b0f25]">OVULITE</div>
            <p className="mt-2 text-sm text-[#7a606b]">AI-powered embryo intelligence for traceable reproductive decisions.</p>
          </div>

          <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-[#7b314d]">
            <a href="#" className="hover:text-[#4b0f25]">Product</a>
            <a href="#" className="hover:text-[#4b0f25]">Science</a>
            <a href="#" className="hover:text-[#4b0f25]">Use Cases</a>
            <a href="#" className="hover:text-[#4b0f25]">Contact</a>
            <a href="mailto:contact@ovulite.ai" className="hover:text-[#4b0f25]">contact@ovulite.ai</a>
          </div>
        </div>
        <div className="mx-auto mt-6 max-w-7xl text-xs text-[#7a606b]">© {new Date().getFullYear()} Ovulite. All rights reserved.</div>
      </footer>
    </div>
  );
}

function SectionWrap({
  title,
  children,
  className,
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={className}>
      <div>
        <h2 className="text-center text-3xl font-bold tracking-tight text-[#3a0d1d] sm:text-4xl">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function GlassCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <Card
      className={`rounded-2xl border border-white/55 bg-white/32 shadow-[0_18px_45px_rgba(11,61,46,0.12)] backdrop-blur-2xl ${className}`}
    >
      <CardContent className="p-0">{children}</CardContent>
    </Card>
  );
}

function BackgroundOrbs() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div
        className="absolute -left-20 -top-16 h-72 w-72 rounded-full"
        style={{ background: "radial-gradient(circle, rgba(126,242,177,0.34), transparent 65%)", filter: "blur(26px)" }}
      />
      <div
        className="absolute right-0 top-20 h-80 w-80 rounded-full"
        style={{ background: "radial-gradient(circle, rgba(31,111,94,0.30), transparent 66%)", filter: "blur(28px)" }}
      />
      <div
        className="absolute -bottom-16 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full"
        style={{ background: "radial-gradient(circle, rgba(168,213,186,0.36), transparent 64%)", filter: "blur(30px)" }}
      />
    </div>
  );
}

function HeroPreview() {
  return (
    <div className="relative mx-auto max-w-xl">
      <GlassCard className="relative overflow-hidden p-5 sm:p-6">
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm font-semibold text-[#5a1a32]">Ovulite Intelligence Preview</p>
          <Badge className="border-white/60 bg-white/45 text-[#7a2341]">Live Signal</Badge>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-white/50 bg-white/35 p-3">
            <p className="text-[11px] uppercase tracking-[0.08em] text-[#7a606b]">Pregnancy Probability</p>
            <p className="mt-1 text-2xl font-bold text-[#4b0f25]">68.4%</p>
            <p className="text-xs text-[#7a606b]">Risk band: Medium</p>
          </div>
          <div className="rounded-xl border border-white/50 bg-white/35 p-3">
            <p className="text-[11px] uppercase tracking-[0.08em] text-[#7a606b]">Embryo Grade Signal</p>
            <p className="mt-1 text-2xl font-bold text-[#4b0f25]">A2</p>
            <p className="text-xs text-[#7a606b]">Confidence: 92%</p>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-white/50 bg-white/35 p-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium text-[#5a1a32]">Recipient Matching Window</p>
            <GitMerge className="h-4 w-4 text-[#7a2341]" />
          </div>
          <div className="space-y-2">
            {["R-302", "R-447", "R-215"].map((id, idx) => (
              <div key={id} className="flex items-center justify-between rounded-lg bg-white/45 px-2.5 py-2 text-xs">
                <span className="font-medium text-[#55182e]">{id}</span>
                <span className="text-[#7a2341]">{91 - idx * 4}% match</span>
              </div>
            ))}
          </div>
        </div>
      </GlassCard>

      <div className="absolute -right-5 -top-4 hidden rounded-xl border border-white/60 bg-white/50 p-3 shadow-lg sm:block">
        <div className="flex items-center gap-2 text-xs text-[#7a2341]">
          <FlaskConical className="h-4 w-4" />
          Biology-first scoring
        </div>
      </div>

      <div className="absolute -bottom-6 left-6 hidden rounded-xl border border-white/60 bg-white/50 p-3 shadow-lg sm:block">
        <div className="flex items-center gap-2 text-xs text-[#7a2341]">
          <BarChart3 className="h-4 w-4" />
          Protocol responsiveness
        </div>
      </div>
    </div>
  );
}

