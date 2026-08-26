import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

function money(value) {
  return `₹${Number(value || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 0,
  })}`;
}

async function getJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || data.message || "Request failed");
  return data;
}

function App() {
  const [metrics, setMetrics] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [batch, setBatch] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

  async function load() {
    try {
      setError("");
      const [m, t] = await Promise.all([
        getJson(`${API}/metrics`),
        getJson(`${API}/transactions?limit=100`),
      ]);
      setMetrics(m);
      setTransactions(t);
    } catch (err) {
      setError(err.message);
    }
  }

  async function openTransaction(id) {
    try {
      const data = await getJson(`${API}/transactions/${id}`);
      setSelected(data);
      setAiAnalysis(null);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function analyzeWithGemini(id) {
    setAnalyzing(true);
    setAiAnalysis(null);
    try {
      const data = await getJson(`${API}/transactions/${id}/analyze`, { method: "POST" });
      setAiAnalysis(data.ai_analysis);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  }

  async function recover(id) {
    try {
      const result = await getJson(`${API}/recovery/${id}`, { method: "POST" });
      setMessage(result.message);
      await load();
      await openTransaction(id);
    } catch (err) {
      setError(err.message);
    }
  }

  async function runBatchEvaluation() {
    try {
      setError("");
      setBatch(await getJson(`${API}/batch-evaluation?limit=100`));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (!metrics) return <div className="loading">Loading RecoverAI...</div>;

  const modeLabel = metrics.recovery_mode === "razorpay_test" ? "Razorpay Test Mode" : "Demo Mode";

  return (
    <div className="app">
      <header>
        <div>
          <div className="eyebrow">RAZORPAY AI BUILDER • TRACK 3</div>
          <h1>RecoverAI</h1>
          <p>AI-powered revenue recovery agent</p>
        </div>
        <div className="header-right">
          <div className="mode">{modeLabel}</div>
          <div className="status"><span /> System Online</div>
        </div>
      </header>

      <main>
        {error && <div className="notice error">{error}</div>}
        {message && <div className="notice">{message}</div>}

        <section className="metrics">
          <Metric title="Revenue at Risk" value={money(metrics.revenue_at_risk)} />
          <Metric title={metrics.recovery_mode === "demo" ? "Demo Recovered Value" : "Revenue Recovered"} value={money(metrics.revenue_recovered)} />
          <Metric title="Recovery Attempts" value={metrics.recovery_attempts} />
          <Metric title="Recovery Rate" value={`${metrics.recovery_rate}%`} />
        </section>

        <section className="panel overview">
          <div>
            <h2>Closed-loop recovery</h2>
            <p>Gemini diagnoses the failure. A deterministic policy engine decides whether an action is safe. Recovery is only counted after a confirmed outcome.</p>
          </div>
          <div className="chips">
            <span>Max retries: 2</span>
            <span>Auto-action cap: ₹10,000</span>
            <span>Approval: {metrics.approval_required}</span>
            <span>Escalated: {metrics.escalated_cases}</span>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Transaction Recovery Queue</h2>
              <p>{metrics.pending_cases} failed/abandoned cases still in the recovery workflow</p>
            </div>
            <button onClick={load}>Refresh</button>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Transaction</th><th>Customer</th><th>Amount</th><th>Status</th>
                  <th>Policy Action</th><th>Recoverability</th><th>Action Status</th><th />
                </tr>
              </thead>
              <tbody>
                {transactions.filter((x) => x.status !== "paid").slice(0, 30).map((x) => (
                  <tr key={x.transaction_id}>
                    <td>{x.transaction_id}</td>
                    <td>{x.customer_name}</td>
                    <td>{money(x.amount)}</td>
                    <td><span className={`badge ${x.status}`}>{x.status}</span></td>
                    <td><strong>{x.recommended_action}</strong></td>
                    <td>{x.recoverability}%</td>
                    <td><span className="status-pill">{x.action_status}</span></td>
                    <td><button className="small" onClick={() => openTransaction(x.transaction_id)}>Inspect</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel batch-panel">
          <div className="panel-header">
            <div>
              <h2>Batch evidence</h2>
              <p>100-case deterministic synthetic evaluation for demo evidence. It does not mutate transactions or claim live payments.</p>
            </div>
            <button className="primary" onClick={runBatchEvaluation}>Run 100-case evaluation</button>
          </div>
          {batch && (
            <div>
              <div className="batch-grid">
                <Metric title="Cases" value={batch.counts.total} />
                <Metric title="Auto Eligible" value={batch.counts.auto_eligible} />
                <Metric title="Simulated Recovered" value={batch.counts.simulated_recovered} />
                <Metric title="Simulated Recovered Value" value={money(batch.simulated_recovered_value)} />
              </div>
              <div className="batch-summary">
                <span>Approval required: <b>{batch.counts.approval_required}</b></span>
                <span>Escalated: <b>{batch.counts.escalated}</b></span>
                <span>Simulated recovery rate: <b>{batch.simulated_recovery_rate}%</b></span>
                <span>At-risk value in batch: <b>{money(batch.at_risk_value)}</b></span>
              </div>
            </div>
          )}
        </section>

        {selected && (
          <section className="panel detail">
            <div className="panel-header">
              <div><h2>{selected.transaction.transaction_id}</h2><p>Recovery decision and audit trail</p></div>
              <button onClick={() => setSelected(null)}>Close</button>
            </div>

            <div className="decision-grid">
              <Decision title="Amount" value={money(selected.transaction.amount)} />
              <Decision title="Recoverability" value={`${selected.transaction.recoverability}%`} />
              <Decision title="Policy Action" value={selected.decision.action} />
              <Decision title="Policy Gate" value={selected.decision.allowed ? "ALLOWED" : "BLOCKED / WAIT"} />
            </div>

            <div className="reason">
              <h3>Deterministic policy explanation</h3>
              <p>{selected.decision.reason}</p>
              <p className="muted">The AI layer cannot override this policy.</p>
            </div>

            {selected.transaction.recovery_link_url && (
              <div className="link-box">
                <strong>Razorpay recovery link created</strong>
                <a href={selected.transaction.recovery_link_url} target="_blank" rel="noreferrer">Open payment link</a>
                <span>Recovery is counted only after a verified payment_link.paid webhook.</span>
              </div>
            )}

            <div className="ai-section">
              <div className="ai-header">
                <div><h3>✨ Gemini AI Diagnosis</h3><p>Diagnosis only — no payment authorization.</p></div>
                <button className="primary" disabled={analyzing} onClick={() => analyzeWithGemini(selected.transaction.transaction_id)}>
                  {analyzing ? "Analyzing..." : "Analyze with Gemini"}
                </button>
              </div>
              {aiAnalysis?.success && (
                <div className="ai-result">
                  <div className="ai-result-header"><span>Gemini {aiAnalysis.model}</span><span className="ai-success">Connected</span></div>
                  <div className="ai-fields">
                    <span><b>Risk</b>{aiAnalysis.diagnosis?.risk_level}</span>
                    <span><b>Confidence</b>{aiAnalysis.diagnosis?.confidence}%</span>
                    <span><b>Cause</b>{aiAnalysis.diagnosis?.likely_cause}</span>
                    <span><b>Strategy</b>{aiAnalysis.diagnosis?.recommended_recovery_strategy}</span>
                  </div>
                  <p>{aiAnalysis.diagnosis?.explanation}</p>
                </div>
              )}
              {aiAnalysis && !aiAnalysis.success && <div className="ai-error">Gemini analysis unavailable.</div>}
            </div>

            {selected.decision.allowed && selected.decision.action !== "NO_ACTION" && (
              <button className="primary" onClick={() => recover(selected.transaction.transaction_id)}>
                Execute Bounded Recovery
              </button>
            )}

            <div className="audit">
              <h3>Audit Trail</h3>
              {selected.audit.length === 0 ? <p>No actions recorded yet.</p> : selected.audit.map((x, i) => (
                <div className="audit-row" key={i}>
                  <strong>{x.event}</strong><span>{x.details}</span><small>{new Date(x.created_at).toLocaleString()}</small>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function Metric({ title, value }) { return <div className="metric"><span>{title}</span><strong>{value}</strong></div>; }
function Decision({ title, value }) { return <div className="decision-card"><span>{title}</span><strong>{value}</strong></div>; }

export default App;
