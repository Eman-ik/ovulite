import { useNavigate } from "react-router-dom";
import { Sparkles, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function OvuliteLandingPageSimple() {
  const navigate = useNavigate();

  return (
    <div style={{ minHeight: "100vh", padding: "2rem" }}>
      <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
        {/* Header */}
        <header style={{ marginBottom: "4rem", paddingBottom: "2rem", borderBottom: "1px solid #ddd" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "2rem" }}>
            <div style={{ width: "40px", height: "40px", backgroundColor: "#7a2341", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center", color: "white" }}>
              <Sparkles size={24} />
            </div>
            <div>
              <div style={{ fontSize: "18px", fontWeight: "bold", color: "#3a0d1d" }}>OVULITE</div>
              <div style={{ fontSize: "12px", color: "#999" }}>Embryo Intelligence</div>
            </div>
          </div>
          
          <div style={{ display: "flex", gap: "1rem" }}>
            <Button variant="ghost" onClick={() => navigate("/login")}>Log In</Button>
            <Button onClick={() => alert("Request Demo button clicked")}>Request Demo</Button>
          </div>
        </header>

        {/* Hero */}
        <section style={{ marginBottom: "4rem" }}>
          <Badge style={{ marginBottom: "1rem" }}>Premium Biotech AI Platform</Badge>
          <h1 style={{ fontSize: "3rem", fontWeight: "bold", color: "#3a0d1d", marginBottom: "1rem", maxWidth: "600px" }}>
            AI-powered embryo intelligence for traceable reproductive decisions
          </h1>
          <p style={{ fontSize: "1.1rem", color: "#666", marginBottom: "1.5rem", maxWidth: "600px" }}>
            Ovulite helps IVF and embryo transfer programs predict outcomes, grade embryos, match recipients,
            and improve protocol performance through biology-first AI.
          </p>
          <div style={{ display: "flex", gap: "1rem" }}>
            <Button onClick={() => alert("Request Demo")}>Request Demo</Button>
            <Button variant="outline" onClick={() => navigate("/login")}>
              Explore Platform <ChevronRight size={16} style={{ marginLeft: "0.5rem" }} />
            </Button>
          </div>
        </section>

        {/* Quick Features */}
        <section style={{ marginBottom: "4rem" }}>
          <h2 style={{ fontSize: "2rem", fontWeight: "bold", color: "#3a0d1d", marginBottom: "2rem", textAlign: "center" }}>
            Core Capabilities
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "2rem" }}>
            {[
              { title: "Predict Outcomes", desc: "Estimate pregnancy success with confidence intervals" },
              { title: "Grade Embryos", desc: "AI-powered embryo quality assessment from images" },
              { title: "Match Recipients", desc: "Biologically-aligned embryo-recipient pairing" },
            ].map((item) => (
              <div key={item.title} style={{ padding: "1.5rem", border: "1px solid #ddd", borderRadius: "8px", backgroundColor: "#f9f9f9" }}>
                <h3 style={{ fontSize: "1.1rem", fontWeight: "bold", color: "#3a0d1d", marginBottom: "0.5rem" }}>
                  {item.title}
                </h3>
                <p style={{ color: "#666", fontSize: "0.95rem" }}>{item.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section style={{ padding: "3rem", backgroundColor: "#f0f8f5", borderRadius: "12px", textAlign: "center" }}>
          <h2 style={{ fontSize: "1.8rem", fontWeight: "bold", color: "#3a0d1d", marginBottom: "1rem" }}>
            Ready to transform your reproductive program?
          </h2>
          <p style={{ marginBottom: "1.5rem", color: "#666" }}>Get started with Ovulite today</p>
          <div style={{ display: "flex", gap: "1rem", justifyContent: "center" }}>
            <Button onClick={() => alert("Request Demo")}>Request Demo</Button>
            <Button variant="outline" onClick={() => navigate("/login")}>Sign In</Button>
          </div>
        </section>
      </div>
    </div>
  );
}
