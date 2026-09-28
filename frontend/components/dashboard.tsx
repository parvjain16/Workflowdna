"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, ArrowDown, ArrowDownRight, ArrowRight, Beaker, BookOpen, Check, CheckCheck, ChevronDown, ChevronRight, CircleAlert, Clock3, Download, FileCheck2, FileText, FlaskConical, GitBranch, Layers3, Loader2, Network, Play, ReceiptText, RefreshCw, ShieldCheck, Sparkles, UserRound, Wallet, X } from "lucide-react";
import ModelLab from "@/components/model-lab";
import type { Analysis, Company, Evaluation, Scenario, Step, Training } from "@/lib/types";

type View = "overview" | "policy" | "model";
type DiagramView = "compare" | "current" | "recommended";
const dollars = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });

async function getJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...options, cache: "no-store" });
  if (!response.ok) {
    let message = `Request failed (${response.status}). Check that the Python backend is running.`;
    try { const body = await response.json(); if (typeof body.detail === "string") message = body.detail; else if (body.detail?.message) message = body.detail.message; } catch { /* Preserve actionable network message. */ }
    throw new Error(message);
  }
  return response.json();
}

function DNA({ small = false }: { small?: boolean }) {
  return <span className={`dna-mark ${small ? "small" : ""}`} aria-hidden="true"><GitBranch size={small ? 18 : 25} strokeWidth={2.2} /></span>;
}

function StepIcon({ step }: { step: Step }) {
  if (step.type === "submission") return <ReceiptText size={19} />;
  if (step.type === "payment") return <Wallet size={19} />;
  if (step.role === "finance") return <FileCheck2 size={19} />;
  return <UserRound size={19} />;
}

function WorkflowLane({ analysis, optimized = false, onPolicy }: { analysis: Analysis; optimized?: boolean; onPolicy: (id?: string) => void }) {
  const removed = new Set(analysis.removed_steps.map(s => s.id));
  return <div className={`workflow-lane ${optimized ? "optimized" : ""}`}>
    <div className="lane-heading"><span><span className={`lane-indicator ${optimized ? "green" : ""}`} />{optimized ? "Recommended workflow" : "Current workflow"}</span><span className="lane-total">{optimized ? analysis.metrics.proposed_days : analysis.metrics.current_days} <span>business days</span></span></div>
    <div className="workflow-scroll"><div className="workflow-nodes">
      {analysis.current_steps.map((step, i) => {
        const isRemoved = optimized && removed.has(step.id);
        return <div className="node-unit" key={step.id}>
          {i > 0 && <span className={`node-connector ${isRemoved ? "removed-connector" : ""}`}><ArrowRight size={15} /></span>}
          <button className={`workflow-node ${step.type} ${isRemoved ? "removed" : ""}`} onClick={() => onPolicy(isRemoved ? analysis.removed_steps.find(s => s.id === step.id)?.clause_ids?.[0] : undefined)} title={isRemoved ? `Why ${step.label} can be removed` : `View policy for ${step.label}`}>
            <span className="node-top"><span className="node-icon"><StepIcon step={step} /></span><span className="node-index">{String(i + 1).padStart(2, "0")}</span></span>
            <span className="node-name">{step.label}</span>
            <span className="node-time">{isRemoved ? <><X size={12} /> Not required</> : <><Clock3 size={12} /> {step.days} {step.days === 1 ? "day" : "days"}</>}</span>
          </button>
        </div>;
      })}
    </div></div>
  </div>;
}

export default function Dashboard() {
  const [view, setView] = useState<View>("overview");
  const [diagram, setDiagram] = useState<DiagramView>("compare");
  const [company, setCompany] = useState<Company | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [training, setTraining] = useState<Training | null>(null);
  const [amount, setAmount] = useState("750");
  const [exception, setException] = useState(false);
  const [receipt, setReceipt] = useState(true);
  const engine = "river" as const;
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const initialized = useRef(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [highlight, setHighlight] = useState<string | undefined>();
  const [exported, setExported] = useState(false);
  const mainRef = useRef<HTMLElement>(null);

  const initialize = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [companyData, trainingData, evaluationData] = await Promise.all([
        getJson<Company>("/api/company"), getJson<Training>("/api/training"), getJson<Evaluation>("/api/evaluation"),
      ]);
      setCompany(companyData); setTraining(trainingData); setEvaluation(evaluationData);
      if (trainingData.river.checkpoint && trainingData.river.status === "trained") {
        const result = await getJson<Analysis>("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ amount: 750, exception: false, receipt_present: true, engine: "river" }) });
        setAnalysis(result);
      }

    } catch (err) { setError(err instanceof Error ? err.message : "Unable to connect to WorkflowDNA."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { if (!initialized.current) { initialized.current = true; void initialize(); } }, [initialize]);

  const showView = (next: View) => { setView(next); window.scrollTo({ top: 0, behavior: "instant" }); };
  const showPolicy = (id?: string) => { setHighlight(id); showView("policy"); };
  const isDirty = !!analysis && (Number(amount) !== analysis.scenario.amount || exception !== analysis.scenario.exception || receipt !== analysis.scenario.receipt_present || engine !== analysis.engine);
  const runAnalysis = async (event: React.FormEvent) => {
    event.preventDefault(); setLoading(true); setError("");
    const scenario: Scenario = { amount: Number(amount), exception, receipt_present: receipt, engine };
    try {
      const result = await getJson<Analysis>("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(scenario) });
      setAnalysis(result);
    } catch (err) { setError(err instanceof Error ? err.message : "The analysis could not finish."); }
    finally { setLoading(false); }
  };
  const refreshTraining = async () => {
    setRefreshing(true); setError("");
    try { const [status, report] = await Promise.all([getJson<Training>("/api/training"), getJson<Evaluation>("/api/evaluation")]); setTraining(status); setEvaluation(report); } catch (err) { setError(err instanceof Error ? err.message : "Unable to refresh training status."); }
    finally { setRefreshing(false); }
  };
  const exportReport = () => {
    if (!analysis) return;
    const report = { exported_at: new Date().toISOString(), notice: "Fictional company. Projected savings from synthetic sequential business-day durations. Engine provenance is included below.", analysis, policy: company?.policy, training, evaluation };
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
    const a = document.createElement("a"); a.href = url; a.download = "workflowdna-atlas-analysis.json"; a.click(); URL.revokeObjectURL(url);
    setExported(true); window.setTimeout(() => setExported(false), 2500);
  };
  const riverReady = !!training?.river.checkpoint && ["completed", "trained", "ready"].includes(training.river.status);
  const navItems: { id: View; name: string; icon: typeof Activity; count?: string }[] = [
    { id: "overview", name: "Workflow overview", icon: Activity },
    { id: "policy", name: "Company policy", icon: BookOpen },
    { id: "model", name: "Model lab", icon: FlaskConical, count: "SFT" },
  ];

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <aside className="sidebar">
      <div className="brand"><DNA /><span>Workflow<span className="brand-light">DNA</span><small>WORKFLOW INTELLIGENCE</small></span></div>
      <div className="workspace"><span className="company-avatar">A<span /></span><div><strong>Atlas Technologies</strong><span>Demo workspace</span></div><ChevronDown size={15} aria-hidden="true" /></div>
      <div className="nav-caption">WORKSPACE</div>
      <nav aria-label="Main navigation">{navItems.map(item => <button key={item.id} className={`nav-item ${view === item.id ? "active" : ""}`} onClick={() => showView(item.id)} aria-current={view === item.id ? "page" : undefined}><item.icon size={18} /><span>{item.name}</span>{item.count && <span className="nav-tag">{item.count}</span>}</button>)}</nav>
      <div className="sidebar-workflow"><span className="nav-caption">YOUR WORKFLOW</span><button onClick={() => showView("overview")}><span className="workflow-small-icon"><ReceiptText size={16} /></span><span>Expense reimbursement<small>Finance operations</small></span></button></div>
      <div className="sidebar-bottom"><div className="connection-card"><Network size={19} /><strong>Grounded in your policy</strong><p>Every recommendation traces back to Atlas’s reimbursement policy.</p><span className="planned-tag">LOCAL POLICY · VERSION 1.0</span></div><div className="sidebar-footer"><span className="demo-dot" />Hackathon edition<span>v0.1</span></div></div>
    </aside>

    <main id="main-content" ref={mainRef}>
      <header className="topbar"><div className="breadcrumb">Workspace<ChevronRight size={14} /><span>{navItems.find(item => item.id === view)?.name}</span></div><span className="demo-label"><Beaker size={13} /> Fictional company · Real prototype</span></header>
      <div className="page-content">
        <div className="page-heading"><div><div className="eyebrow"><span />ATLAS TECHNOLOGIES <span className="eyebrow-divider">/</span> FINANCE</div><h1>{view === "overview" ? "Less waiting. Better workflows." : view === "policy" ? "Every improvement has a source." : "From examples to evidence."}</h1><p>{view === "overview" ? "A clearer path through your expense reimbursement process." : view === "policy" ? "The written policy behind Atlas’s reimbursement recommendations." : "Inspect the data, the River checkpoint, and actual evaluation results."}</p></div><button className="button secondary export-button" onClick={exportReport} disabled={!analysis || loading}><Download size={16} />{exported ? "Report downloaded" : "Export report"}</button></div>

        {error && <div className="error-banner" role="alert"><CircleAlert size={19} /><div><strong>We couldn’t complete that request</strong><p>{error}</p>{analysis && <p>The last successful analysis remains below.</p>}</div>{!analysis && <button onClick={() => void initialize()} className="button secondary">Retry</button>}</div>}
        {!analysis && loading && <div className="loading-panel" role="status"><Loader2 className="spin" size={28} /><h2>{company ? "Analyzing with your River model…" : "Reading the workflow and policy…"}</h2><p>{company ? "Loading the saved checkpoint and checking its recommendation against policy." : "Connecting to the local Python backend."}</p></div>}

        {view === "overview" && !analysis && !loading && !error && <div className="loading-panel"><FlaskConical size={28} /><h2>{riverReady ? "Your custom model is ready" : "River training is in progress"}</h2><p>{training?.river.message || "Model status has not loaded yet."}</p><button className="button primary" onClick={() => void initialize()}><RefreshCw size={15} />{riverReady ? "Analyze the workflow" : "Check training status"}</button><button className="text-button" onClick={() => showView("model")}>View model lab<ArrowRight size={15} /></button></div>}

        {view === "overview" && analysis && <>
          <div className="analysis-context"><div><span className="context-icon"><ReceiptText size={18} /></span><strong>Expense reimbursement</strong><span className="context-separator" /><span>{dollars.format(analysis.scenario.amount)} expense</span><span className="subtle-pill">{analysis.engine_label}</span></div><span className="status-caption"><span className="tiny-dot" />Analysis ready</span></div>
          <div className="metrics-grid" aria-label="Workflow time comparison">
            <article className="metric-card"><div className="metric-label">Current turnaround<Clock3 size={17} /></div><div className="metric-value" data-testid="current-days">{analysis.metrics.current_days}<span>days</span></div><div className="metric-foot">{analysis.metrics.current_approvals} approvals <span>·</span> Sequential process</div><div className="metric-track"><span /></div></article>
            <article className="metric-card"><div className="metric-label">Proposed turnaround<GitBranch size={17} /></div><div className="metric-value" data-testid="proposed-days">{analysis.metrics.proposed_days}<span>days</span><span className="mini-savings"><ArrowDown size={12} />{analysis.metrics.savings_percent}%</span></div><div className="metric-foot">{analysis.metrics.proposed_approvals} approvals <span>·</span> {analysis.compliance.status === "compliant" ? "Policy controls retained" : "Manual review required"}</div><div className="metric-track green"><span style={{ width: `${analysis.metrics.proposed_days / analysis.metrics.current_days * 100}%` }} /></div></article>
            <article className="metric-card savings-card"><div className="metric-label">Potential time saved<Sparkles size={18} /></div><div className="metric-value" data-testid="saved-days">{analysis.metrics.saved_days}<span>days / request</span></div><div className="metric-foot">{analysis.metrics.saved_days ? "More momentum. Same required controls." : "All current controls remain in place."}</div><span className="savings-badge">PROJECTED, NOT MEASURED</span></article>
          </div>

          <form className="scenario-bar" onSubmit={runAnalysis}>
            <div className="scenario-title"><span><Layers3 size={17} /> Explore a scenario</span><small>Change the inputs. See what’s required.</small></div>
            <label className="amount-field">Expense amount<div><span>$</span><input name="amount" aria-label="Expense amount" type="number" min="0.01" max="1000000000" step="0.01" required value={amount} onChange={event => setAmount(event.target.value)} /></div></label>
            <div className="engine-field"><span className="engine-caption">Analysis engine</span><div className="engine-fixed"><span className="tiny-dot" />River custom model</div></div>
            <div className="scenario-checks"><label><input type="checkbox" checked={receipt} onChange={event => setReceipt(event.target.checked)} /><span>Receipt attached</span></label><label><input type="checkbox" checked={exception} onChange={event => setException(event.target.checked)} /><span>Policy exception</span></label></div>
            <button className="button primary" type="submit" disabled={loading}>{loading ? <Loader2 size={16} className="spin" /> : <Play size={15} fill="currentColor" />}{loading ? "Analyzing…" : "Analyze workflow"}</button>
          </form>
          {isDirty && <div className="pending-note" role="status"><CircleAlert size={14} />Inputs changed. Run analysis to update the results below.</div>}

          <div className="analysis-grid">
            <section className="card workflow-card">
              <div className="card-heading"><div><h2>Workflow comparison</h2><p>Where time goes. Where it doesn’t have to.</p></div><div className="diagram-tabs" role="group" aria-label="Diagram view">{([['compare','Compare'],['current','Before'],['recommended','After']] as const).map(([id, label]) => <button key={id} aria-pressed={diagram === id} className={diagram === id ? "selected" : ""} onClick={() => setDiagram(id)}>{label}</button>)}</div></div>
              <div className="diagram-canvas">
                {diagram !== "recommended" && <WorkflowLane analysis={analysis} onPolicy={showPolicy} />}
                {diagram === "compare" && <div className="lane-divider"><span /><span className="difference-label"><ArrowDownRight size={14} />{analysis.removed_steps.length ? `${analysis.removed_steps.length} unnecessary approvals removed` : "Required controls preserved"}</span><span /></div>}
                {diagram !== "current" && <WorkflowLane analysis={analysis} optimized onPolicy={showPolicy} />}
              </div>
              <div className="diagram-footer"><span><i className="legend-box" />Retained step</span><span><i className="legend-box removed" />Not required by policy</span><span className="diagram-help">Select a step to inspect the policy<ArrowRight size={13} /></span></div>
            </section>

            <section className={`recommendation-card ${analysis.compliance.status !== "compliant" ? "review" : ""}`}>
              <div className="recommendation-kicker"><Sparkles size={16} />THE OPPORTUNITY</div><h2>{analysis.compliance.status !== "compliant" ? "Keep the controls. Get a review." : analysis.removed_steps.length ? `${analysis.metrics.proposed_approvals === 2 ? "Two" : analysis.metrics.proposed_approvals} approvals.\nSame safeguards.` : "Every approval\nhas a purpose."}</h2>
              <p className="recommendation-intro">{analysis.compliance.status !== "compliant" ? analysis.compliance.message : analysis.removed_steps.length ? `For this ${dollars.format(analysis.scenario.amount)} expense, the policy does not require ${analysis.removed_steps.map(s => s.label.toLowerCase()).join(" or ")}.` : "This expense needs all four approvals under the company’s policy."}</p>
              <div className="recommendation-findings">{analysis.removed_steps.map(step => <div key={step.id}><span className="finding-check"><Check size={13} /></span><div><strong>Skip {step.label.toLowerCase()}</strong><p>{step.days} days of waiting removed</p></div></div>)}{!analysis.removed_steps.length && <div><span className="finding-check"><ShieldCheck size={14} /></span><div><strong>No approvals removed</strong><p>{analysis.compliance.status === "compliant" ? "All policy thresholds are respected" : "Human review comes first"}</p></div></div>}</div>
              <button className="policy-link" onClick={() => showPolicy(analysis.compliance.clause_ids[0])}><ShieldCheck size={16} />{analysis.compliance.status === "compliant" ? "Grounded in company policy" : "Review the policy requirements"}<ArrowRight size={16} /></button>
            </section>
          </div>

          <div className="lower-grid">
            <section className="card evidence-card"><div className="section-title"><div className="section-icon"><BookOpen size={19} /></div><div><h2>The policy behind the recommendation</h2><p>Trace every change to a written rule.</p></div><button className="text-button" onClick={() => showPolicy()}>View policy<ArrowRight size={15} /></button></div><div className="evidence-list">{analysis.findings.slice(0, 3).map((finding, index) => <div className="evidence-row" key={index}><span className="evidence-number">0{index + 1}</span><div><h3>{finding.title}</h3><p>{finding.description}</p></div><div className="clause-chips">{finding.clause_ids.map(id => <button key={id} onClick={() => showPolicy(id)}>{id}<ArrowRight size={11} /></button>)}</div></div>)}</div></section>
            <section className="card provenance-card"><div className="section-title"><div className="section-icon"><FlaskConical size={19} /></div><div><h2>Know what’s running</h2><p>Transparent by design.</p></div></div><div className="provenance-row"><span>Current analysis</span><strong>{analysis.engine_label}</strong></div><div className="provenance-row"><span>Training / evaluation</span><strong>{training?.train_count ?? "—"} / {training?.eval_count ?? "—"} examples</strong></div><div className="provenance-row"><span>River checkpoint</span><strong className={riverReady ? "green-text" : "muted-text"}>{riverReady ? "Saved" : "Not created"}</strong></div><p className="provenance-note">{analysis.model.message}</p><button className="text-button" onClick={() => showView("model")}>Open model lab<ArrowRight size={15} /></button></section>
          </div>
          <div className="assumptions-note"><CircleAlert size={15} /><p><strong>About these estimates.</strong> {analysis.assumptions.join(" ")}</p></div>
        </>}

        {view === "policy" && company && <div className="policy-layout">
          <section className="card policy-document"><div className="policy-document-heading"><span className="document-icon"><FileText size={27} /></span><div><span className="eyebrow">POLICY LIBRARY / FINANCE</span><h2>{company.policy.title}</h2><p>Version {company.policy.version} <span>·</span> {company.policy.source}</p></div><span className="source-label">LOCAL JSON</span></div><div className="policy-clauses">{company.policy.clauses.map(clause => <article id={clause.id} key={clause.id} className={`policy-clause ${highlight === clause.id ? "highlight" : ""}`}><span className="clause-id">{clause.id}</span><p>{clause.text}</p>{analysis?.compliance.clause_ids.includes(clause.id) && <span className="used-clause"><Check size={12} />Used in this analysis</span>}</article>)}</div></section>
          <aside className="policy-aside"><div className="policy-aside-icon"><ShieldCheck size={27} /></div><h2>Policy first.<br />Optimization second.</h2><p>Required controls are checked before an approval can be removed. Missing receipts and exceptions stay in the current process for human review.</p><div className="honesty-note"><strong>How this MVP reads policy</strong><p>The written clauses and structured rules live together in a local JSON file. The rules are manually authored; automatic interpretation of arbitrary policy documents is not implemented.</p></div><div className="next-step"><Network size={20} /><div><strong>Local policy source</strong><p>The company policy is stored in data/company_policy.json. No GBrain integration is included.</p></div></div><button className="button secondary" onClick={() => showView("overview")}><ArrowRight size={15} />Back to workflow</button></aside>
        </div>}

        {view === "model" && training && <ModelLab training={training} evaluation={evaluation} refreshing={refreshing} onRefresh={() => void refreshTraining()} onTry={() => { showView("overview"); if (!analysis) void initialize(); }} />}


        <footer className="page-footer"><span><DNA small />WorkflowDNA<span className="footer-separator">/</span>Understand the process. Improve the path.</span><span>Atlas Technologies is fictional.</span></footer>
      </div>
    </main>
  </div>;
}
