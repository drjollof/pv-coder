import React, { useState, useRef, useEffect } from 'react'
import { AlertTriangle, CheckCircle, Download, FileText, ChevronDown, ChevronRight, Info, Circle, CircleDot, Search, XCircle } from 'lucide-react'
import { Client } from "@gradio/client"

function App() {
  const [activeTab, setActiveTab] = useState('single')

  // Dynamically choose backend URL based on environment
  window.API_URL = import.meta.env.DEV
    ? "http://127.0.0.1:7860"
    : "https://drjollof-pv-coder-api.hf.space";

  return (
    <div>
      <header style={{ marginBottom: '2rem' }}>
        <h1>PV-Coder</h1>
        <p>NLP-assisted Pharmacovigilance Case Intake System.</p>
      </header>

      <div className="glass-panel">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'single' ? 'active' : ''}`}
            onClick={() => setActiveTab('single')}
          >
            Single Intake
          </button>
          <button
            className={`tab ${activeTab === 'batch' ? 'active' : ''}`}
            onClick={() => setActiveTab('batch')}
          >
            Batch Upload
          </button>
          <button
            className={`tab ${activeTab === 'guide' ? 'active' : ''}`}
            onClick={() => setActiveTab('guide')}
          >
            User Guide
          </button>
        </div>

        {activeTab === 'single' && <SingleIntake />}
        {activeTab === 'batch' && <BatchUpload />}
        {activeTab === 'guide' && <UserGuide />}
      </div>
    </div>
  )
}

function HighlightedText({ text, events, drugs, excluded }) {
  const spans = [];
  (events || []).forEach((e, i) => { if (e.start_char != null) spans.push({ start: e.start_char, end: e.end_char, type: 'event', label: 'Adverse Event', id: `ev_${i}`, color: '#f43f5e', bg: 'rgba(244, 63, 94, 0.15)' }); });
  (drugs || []).forEach((d, i) => { if (d.start_char != null) spans.push({ start: d.start_char, end: d.end_char, type: 'drug', label: d.canonical_name ? `Suspected Drug: ${d.canonical_name} (ID: ${d.identifiers?.rxnorm || 'Unknown'})` : 'Suspected Drug', id: `dr_${i}`, color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' }); });
  (excluded || []).forEach((x, i) => { if (x.start_char != null) spans.push({ start: x.start_char, end: x.end_char, type: 'excluded', label: `Excluded: ${x.reason}`, id: `ex_${i}`, color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.15)' }); });

  spans.sort((a, b) => a.start - b.start);

  // Greedy non-overlapping
  const validSpans = [];
  let lastEnd = 0;
  for (const s of spans) {
    if (s.start >= lastEnd && s.end > s.start) {
      validSpans.push(s);
      lastEnd = s.end;
    }
  }

  const parts = [];
  let cursor = 0;
  validSpans.forEach((s, idx) => {
    if (s.start > cursor) {
      parts.push(<span key={`t_${cursor}`}>{text.substring(cursor, s.start)}</span>);
    }
    parts.push(
      <span key={`${s.id}_${idx}`} style={{ backgroundColor: s.bg, color: s.color, padding: '2px 4px', borderRadius: '4px', border: `1px solid ${s.color}`, cursor: 'pointer', position: 'relative' }} title={s.label}>
        {text.substring(s.start, s.end)}
      </span>
    );
    cursor = s.end;
  });
  if (cursor < text.length) {
    parts.push(<span key={`t_${cursor}`}>{text.substring(cursor)}</span>);
  }

  return <div style={{ lineHeight: '1.8', whiteSpace: 'pre-wrap' }}>{parts}</div>;
}

function SingleIntake() {
  const [narrative, setNarrative] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [showJson, setShowJson] = useState(false)
  const [corrections, setCorrections] = useState({})
  const [manualInputs, setManualInputs] = useState({})
  const [validated, setValidated] = useState(false)
  const [expandedRows, setExpandedRows] = useState({})

  const [examples, setExamples] = useState([])

  useEffect(() => {
    async function loadExamples() {
      try {
        const client = await Client.connect(window.API_URL)
        const res = await client.predict("/examples")
        setExamples(JSON.parse(res.data[0]))
      } catch (err) {
        console.error("Could not load examples:", err)
      }
    }
    loadExamples()
  }, [])

  const resetCase = () => {
    setNarrative('')
    setResult(null)
    setCorrections({})
    setManualInputs({})
    setValidated(false)
    setExpandedRows({})
    setError('')
  }

  const toggleRow = (idx) => {
    setExpandedRows(prev => ({ ...prev, [idx]: !prev[idx] }));
  }

  const handleAnalyze = async () => {
    if (!narrative.trim()) return

    setLoading(true)
    setError('')
    setResult(null)
    setCorrections({})
    setValidated(false)
    setExpandedRows({})
    setShowJson(false)

    try {
      const client = await Client.connect(window.API_URL)
      const res = await client.predict("/analyze", [
        narrative,
        'WEB-' + Math.floor(Math.random() * 1000)
      ])
      const data = JSON.parse(res.data[0])
      if (data.error) {
        console.error("Backend Exception:", data.traceback)
        setError("Backend Error: " + data.error + "\n\n" + data.traceback)
        return
      }

      // Auto-expand rows that require review
      const autoExpand = {};
      data.events?.forEach((ev, i) => {
        if (ev.review_status === "Human Review") autoExpand[i] = true;
      });
      setExpandedRows(autoExpand);

      setResult(data)
    } catch (err) {
      console.error("Analysis Error:", err)
      setError("API Error: " + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async (format) => {
    if (format === 'json') {
      const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = "" + result.case_id + "_report.json"
      document.body.appendChild(a)
      a.click()
      URL.revokeObjectURL(url)
      return
    }
    try {
      const client = await Client.connect(window.API_URL)
      const endpoint = format === 'pdf' ? '/export_pdf' : '/export_xml'
      const res = await client.predict(endpoint, [JSON.stringify(result)])
      const payload = res.data[0]

      let blob
      if (format === 'pdf') {
        const bytes = Uint8Array.from(atob(payload), c => c.charCodeAt(0))
        blob = new Blob([bytes], { type: 'application/pdf' })
      } else {
        blob = new Blob([payload], { type: 'application/xml' })
      }

      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = "" + result.case_id + "_report." + format
      document.body.appendChild(a)
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert("Error generating " + format.toUpperCase())
    }
  }

  const handleCorrection = (eventIdx, selectedId, selectedPt) => {
    setCorrections(prev => ({
      ...prev,
      [eventIdx]: { pt: selectedPt, id: selectedId }
    }))
  }

  const handleManualInputChange = (eventIdx, field, value) => {
    setManualInputs(prev => ({
      ...prev,
      [eventIdx]: { ...prev[eventIdx], [field]: value }
    }))
    setCorrections(prev => ({
      ...prev,
      [eventIdx]: {
        ...prev[eventIdx],
        pt: field === 'pt' ? value : (manualInputs[eventIdx]?.pt || 'Reject / Other'),
        id: field === 'id' ? value : (manualInputs[eventIdx]?.id || 'REJECT')
      }
    }))
  }

  const reviewEvents = result?.events?.filter(e => e.review_status === "Human Review") || []

  const getWorkflowState = () => {
    if (!result && !loading) return 0;
    if (loading) return 1;
    if (result && reviewEvents.length > 0 && Object.keys(corrections).length < reviewEvents.length) return 2;
    if (result && !validated) return 3;
    if (result && validated) return 4;
    return 0;
  }
  const currentStep = getWorkflowState();
  const workflowSteps = ['Intake', 'Extraction', 'Review', 'Validation', 'Export'];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.2rem', color: 'var(--text-secondary)' }}>
          {result ? "Case " + result.case_id : 'New Case'}
        </h2>
        <button className="btn btn-secondary" onClick={resetCase}>New Case / Reset</button>
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
        {workflowSteps.map((step, idx) => (
          <span key={step} style={{
            color: idx === currentStep ? 'var(--accent-primary)' : (idx < currentStep ? 'var(--success)' : 'inherit'),
            fontWeight: idx === currentStep ? 'bold' : 'normal',
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem'
          }}>
            {idx < currentStep ? <CheckCircle size={14} /> : (idx === currentStep ? <CircleDot size={14} /> : <Circle size={14} />)}
            {step}
            {idx < workflowSteps.length - 1 && <span style={{ margin: '0 0.5rem', opacity: 0.3 }}>───</span>}
          </span>
        ))}
      </div>

      {!result && !loading && (
        <div style={{ marginBottom: '1.5rem', animation: 'slideIn 0.3s ease-out' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <h3>Clinical Narrative</h3>
            {examples.length > 0 && (
              <select
                className="select-dropdown"
                onChange={(e) => {
                  if (e.target.value !== "") setNarrative(examples[parseInt(e.target.value)])
                }}
              >
                <option value="">Load an example case...</option>
                {examples.map((ex, i) => (
                  <option key={i} value={i}>Clinical Case #{i + 1}</option>
                ))}
              </select>
            )}
          </div>
          <textarea
            className="textarea"
            placeholder="Paste unstructured clinical text here..."
            value={narrative}
            onChange={(e) => setNarrative(e.target.value)}
          />
          <button
            className="btn btn-primary"
            onClick={handleAnalyze}
            disabled={!narrative.trim()}
            style={{ width: '100%', marginTop: '1rem' }}
          >
            Analyze Case
          </button>
        </div>
      )}

      {loading && (
        <div style={{ padding: '2rem', textAlign: 'center', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', animation: 'slideIn 0.3s ease-out' }}>
          <div className="spinner" style={{ margin: '0 auto 1rem auto' }}></div>
          <h3>Analyzing case...</h3>
          <div style={{ color: 'var(--text-secondary)', marginTop: '1rem', textAlign: 'left', display: 'inline-block' }}>
            <p><CheckCircle size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Extracting entities</p>
            <p><CheckCircle size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Resolving clinical context</p>
            <p><CircleDot size={14} style={{ verticalAlign: 'middle', marginRight: '4px', color: 'var(--accent-primary)' }} /> Mapping MedDRA terms</p>
            <p><Circle size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Building case</p>
          </div>
        </div>
      )}

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: '2rem' }}>
          <h4>ANALYSIS FAILED</h4>
          <p style={{ marginTop: '0.5rem' }}>{error}</p>
          <button className="btn btn-secondary" style={{ marginTop: '1rem' }} onClick={() => setError('')}>Try Again</button>
        </div>
      )}

      {result && (
        <div style={{ animation: 'slideIn 0.3s ease-out' }}>

          {/* CASE OVERVIEW PANEL */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '1rem', background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', marginBottom: '2rem', border: '1px solid var(--glass-border)' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Seriousness</div>
              <div style={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.25rem', color: result.is_serious_case ? 'var(--warning)' : 'var(--success)' }}>
                {result.is_serious_case ? <><AlertTriangle size={16} /> Serious</> : <><CheckCircle size={16} /> Non-serious</>}
              </div>
              {result.is_serious_case && result.case_seriousness_reason && (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                  {result.case_seriousness_reason} detected.
                </div>
              )}
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Processing Status</div>
              <div style={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.25rem', color: reviewEvents.length > 0 ? 'var(--warning)' : 'var(--success)' }}>
                {reviewEvents.length > 0 ? <><AlertTriangle size={16} /> Review Required</> : <><CheckCircle size={16} /> Auto-coded</>}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Events Detected</div>
              <div style={{ fontWeight: 'bold' }}>{result.events.length}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Auto-coded</div>
              <div style={{ fontWeight: 'bold' }}>{result.events.length - reviewEvents.length}</div>
            </div>

            {/* Extended Seriousness Evidence */}
            {result.is_serious_case && result.case_seriousness_evidence && (
              <div style={{ gridColumn: '1 / -1', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--glass-border)', fontSize: '0.9rem' }}>
                <span style={{ color: 'var(--warning)' }}>Basis for Seriousness:</span>
                <em style={{ marginLeft: '0.5rem', color: 'var(--text-primary)' }}>"{result.case_seriousness_evidence}"</em>
              </div>
            )}
          </div>

          {/* HIGHLIGHTED NARRATIVE */}
          <div style={{ marginBottom: '2rem' }}>
            <h3 style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between' }}>
              Semantic Case View
              <span style={{ fontSize: '0.8rem', fontWeight: 'normal', color: 'var(--text-secondary)', display: 'flex', gap: '1rem' }}>
                <span><span style={{ display: 'inline-block', width: '10px', height: '10px', background: '#f43f5e', marginRight: '4px' }}></span> Adverse Event</span>
                <span><span style={{ display: 'inline-block', width: '10px', height: '10px', background: '#f59e0b', marginRight: '4px' }}></span> Suspected Drug</span>
                <span><span style={{ display: 'inline-block', width: '10px', height: '10px', background: '#94a3b8', marginRight: '4px' }}></span> Excluded</span>
              </span>
            </h3>
            <div style={{ padding: '1.5rem', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)', color: 'var(--text-primary)' }}>
              <HighlightedText
                text={result.narrative}
                events={result.events}
                drugs={result.extracted_drugs}
                excluded={result.excluded_findings}
              />
            </div>
          </div>

          {/* EXCLUDED FINDINGS */}
          {result.excluded_findings?.length > 0 && (
            <div style={{ marginBottom: '2rem' }}>
              <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Excluded / Filtered Findings ({result.excluded_findings.length})</h4>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {result.excluded_findings.map((x, i) => (
                  <span key={i} style={{ background: 'var(--bg-tertiary)', padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem', border: '1px solid var(--glass-border)' }}>
                    <span style={{ textDecoration: 'line-through', opacity: 0.7 }}>{x.text}</span> <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginLeft: '4px' }}>({x.reason})</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* EXTRACTION & REVIEW TABLE */}
          <div className="table-container" style={{ marginBottom: '2rem' }}>
            <h3 style={{ marginBottom: '1rem' }}>Extraction Results & Inline Review</h3>
            <table style={{ marginTop: '0.5rem', width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left' }}>Effect (Raw)</th>
                  <th style={{ textAlign: 'left' }}>Status</th>
                  <th style={{ textAlign: 'left' }}>MedDRA PT</th>
                  <th style={{ textAlign: 'left' }}>MedDRA ID</th>
                  <th style={{ textAlign: 'left' }}>Suspected Drugs</th>
                </tr>
              </thead>
              <tbody>
                {result.events.map((ev, i) => (
                  <React.Fragment key={i}>
                    <tr onClick={() => toggleRow(i)} style={{ cursor: 'pointer', borderBottom: '1px solid var(--glass-border)', background: expandedRows[i] ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                      <td style={{ padding: '1rem 0.5rem' }}>
                        {expandedRows[i] ? <ChevronDown size={14} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> : <ChevronRight size={14} style={{ marginRight: '8px', verticalAlign: 'middle' }} />}
                        {ev.effect_text}
                      </td>
                      <td style={{ padding: '1rem 0.5rem' }}>
                        {ev.review_status === 'Auto-coded' ?
                          <span style={{ color: 'var(--success)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><CheckCircle size={14} /> Auto-coded</span> :
                          <span style={{ color: 'var(--warning)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><AlertTriangle size={14} /> Review</span>}
                      </td>
                      <td style={{ padding: '1rem 0.5rem' }}>{corrections[i]?.pt || ev.meddra_pt}</td>
                      <td style={{ padding: '1rem 0.5rem' }}>{corrections[i]?.id || ev.meddra_pt_id}</td>
                      <td style={{ padding: '1rem 0.5rem' }}>{ev.suspected_drugs.length > 0 ? ev.suspected_drugs.map(d => typeof d === 'string' ? d : (d.canonical_name ? `${d.canonical_name} (${d.text})` : d.text)).join(', ') : 'None'}</td>
                    </tr>

                    {/* EXPANDED DETAIL ROW */}
                    {expandedRows[i] && (
                      <tr>
                        <td colSpan="5" style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderBottom: '1px solid var(--glass-border)' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                            {/* AI Decision Panel */}
                            <div>
                              <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.8rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Info size={14} /> AI DECISION DETAIL</h4>
                              <div style={{ background: 'var(--bg-tertiary)', padding: '1.2rem', borderRadius: 'var(--radius-md)' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.8rem' }}>
                                  <span style={{ color: 'var(--text-secondary)' }}>Confidence Score:</span>
                                  <span style={{ fontWeight: 'bold' }}>{(ev.confidence_score * 100).toFixed(1)}%</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.8rem' }}>
                                  <span style={{ color: 'var(--text-secondary)' }}>Seriousness:</span>
                                  <span style={{ color: ev.is_serious ? 'var(--warning)' : 'var(--text-primary)' }}>
                                    {ev.is_serious ? "Serious (" + ev.seriousness_reason + ")" : 'Non-serious'}
                                  </span>
                                </div>
                                {ev.seriousness_evidence && (
                                  <div style={{ marginTop: '0.8rem', paddingTop: '0.8rem', borderTop: '1px solid var(--glass-border)', fontSize: '0.9rem' }}>
                                    <span style={{ color: 'var(--text-secondary)' }}>Trigger Evidence:</span><br />
                                    <em style={{ color: 'var(--accent-primary)', display: 'inline-block', marginTop: '0.4rem' }}>"{ev.seriousness_evidence}"</em>
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* HITL Inline Review */}
                            <div>
                              {ev.review_status === "Human Review" && !validated ? (
                                <div>
                                  <h4 style={{ color: 'var(--warning)', marginBottom: '0.8rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><AlertTriangle size={14} /> REVIEW REQUIRED</h4>
                                  <div style={{ background: 'var(--bg-tertiary)', padding: '1.2rem', borderRadius: 'var(--radius-md)' }}>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                                      {ev.top_candidates?.map((cand, idx) => (
                                        <label key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                          <input
                                            type="radio"
                                            name={"review_"}
                                            checked={corrections[i]?.id === cand.id || (!corrections[i] && idx === 0)}
                                            onChange={() => handleCorrection(i, cand.id, cand.pt)}
                                          />
                                          {cand.pt} (ID: {cand.id}) - Score: {cand.score.toFixed(3)}
                                        </label>
                                      ))}
                                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                        <input
                                          type="radio"
                                          name={"review_"}
                                          checked={corrections[i]?.id === "REJECT" || (corrections[i] && !ev.top_candidates.find(c => c.id === corrections[i].id))}
                                          onChange={() => handleCorrection(i, manualInputs[i]?.id || "REJECT", manualInputs[i]?.pt || "Reject / Other")}
                                        />
                                        Reject / Manual Input
                                      </label>

                                      {(corrections[i]?.id === "REJECT" || (corrections[i] && !ev.top_candidates.find(c => c.id === corrections[i].id))) && (
                                        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', marginLeft: '1.5rem' }}>
                                          <input
                                            type="text"
                                            style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)', background: 'var(--bg-primary)', color: 'var(--text-primary)', flex: 1 }}
                                            placeholder="Enter MedDRA Preferred Term (PT)..."
                                            value={manualInputs[i]?.pt || ''}
                                            onChange={(e) => handleManualInputChange(i, 'pt', e.target.value)}
                                          />
                                          <input
                                            type="text"
                                            style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)', background: 'var(--bg-primary)', color: 'var(--text-primary)', width: '150px' }}
                                            placeholder="MedDRA ID"
                                            value={manualInputs[i]?.id || ''}
                                            onChange={(e) => handleManualInputChange(i, 'id', e.target.value)}
                                          />
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div>
                                  <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.8rem', fontSize: '0.85rem' }}>ALTERNATIVES</h4>
                                  <div style={{ background: 'var(--bg-tertiary)', padding: '1.2rem', borderRadius: 'var(--radius-md)' }}>
                                    <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                      {ev.top_candidates?.slice(1).map((cand, idx) => (
                                        <li key={idx} style={{ marginBottom: '0.4rem' }}>{cand.pt} <span style={{ opacity: 0.6 }}>(Score: {cand.score.toFixed(3)})</span></li>
                                      ))}
                                      {(!ev.top_candidates || ev.top_candidates.length <= 1) && <li>No other strong candidates.</li>}
                                    </ul>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
                {result.events.length === 0 && (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>No adverse events detected.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* CASE VALIDATION */}
          {!validated && (
            <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)', marginBottom: '2rem' }}>
              <h3 style={{ marginBottom: '1rem' }}>CASE VALIDATION</h3>
              <ul style={{ listStyleType: 'none', padding: 0, margin: '0 0 1.5rem 0', lineHeight: '1.8' }}>
                <li><CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> Clinical narrative present</li>
                <li>{result.events.length > 0 ? <CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> : <AlertTriangle size={16} style={{ color: 'var(--warning)', verticalAlign: 'middle', marginRight: '8px' }} />} Adverse event identified</li>
                <li>{result.events.some(e => e.suspected_drugs.length > 0) ? <CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> : <AlertTriangle size={16} style={{ color: 'var(--warning)', verticalAlign: 'middle', marginRight: '8px' }} />} Suspected drug identified</li>
                <li><CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> Seriousness assessed</li>
                {reviewEvents.length > 0 && (
                  <li>
                    {Object.keys(corrections).length === reviewEvents.length ?
                      <CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> :
                      <span style={{ display: 'inline-block', width: '16px', height: '16px', border: '2px solid var(--warning)', borderRadius: '50%', verticalAlign: 'middle', marginRight: '8px' }}></span>}
                    Reviewer confirmation required
                  </li>
                )}
              </ul>

              {result.events.length === 0 && (
                <p style={{ color: 'var(--warning)', fontSize: '0.9rem', marginBottom: '1rem' }}>Cannot validate case: No adverse events were identified.</p>
              )}

              <button
                className="btn btn-primary"
                disabled={result.events.length === 0 || (reviewEvents.length > 0 && Object.keys(corrections).length < reviewEvents.length)}
                onClick={() => setValidated(true)}
              >
                Validate Case
              </button>
            </div>
          )}

          {/* EXPORT CENTER */}
          {validated && (
            <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)', marginBottom: '2rem', animation: 'slideIn 0.3s ease-out' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--success)' }}>
                  <CheckCircle /> CASE VALIDATED
                </h3>
                <button className="btn btn-secondary" onClick={() => setValidated(false)}>
                  Edit Case / Undo Validation
                </button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1.5rem' }}>
                <div>
                  <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Regulatory / Interchange</h4>
                  <button className="btn btn-secondary" style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }} onClick={() => handleExport('xml')}>
                    <Download size={16} /> E2B(R3) XML
                  </button>
                </div>
                <div>
                  <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Documentation</h4>
                  <button className="btn btn-secondary" style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }} onClick={() => handleExport('pdf')}>
                    <Download size={16} /> PDF Report
                  </button>
                </div>
                <div>
                  <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Data</h4>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="btn btn-secondary" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }} onClick={() => handleExport('json')}>
                      <Download size={16} /> JSON
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Raw JSON View */}
          <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: '1.5rem' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setShowJson(!showJson)}
              style={{ width: '100%', display: 'flex', justifyContent: 'space-between' }}
            >
              <span>View Raw E2B(R3)-Style JSON</span>
              <span>{showJson ? '?' : '?'}</span>
            </button>
            {showJson && (
              <pre style={{
                background: '#0d0d12',
                padding: '1rem',
                borderRadius: 'var(--radius-md)',
                marginTop: '1rem',
                overflowX: 'auto',
                fontSize: '0.85rem',
                color: '#a5b4fc'
              }}>
                {JSON.stringify(result, null, 2)}
              </pre>
            )}
          </div>

        </div>
      )}
    </div>
  )
}
function BatchUpload() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0, status: 'idle' })
  const [results, setResults] = useState(null)
  const fileInputRef = useRef(null)

  const [searchTerm, setSearchTerm] = useState('')
  const [filter, setFilter] = useState('All')
  const [expandedCaseId, setExpandedCaseId] = useState(null)
  const [expandedEvents, setExpandedEvents] = useState({}) // caseId_eventIdx -> boolean
  const [batchCorrections, setBatchCorrections] = useState({})
  const [batchManualInputs, setBatchManualInputs] = useState({})

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
      setResults(null)
      setProgress({ current: 0, total: 0, status: 'idle' })
      setSearchTerm('')
      setFilter('All')
      setExpandedCaseId(null)
      setExpandedEvents({})
      setBatchCorrections({})
      setBatchManualInputs({})
    }
  }

  const handleBatchCorrection = (caseId, eventIdx, meddraId, pt) => {
    setBatchCorrections(prev => ({
      ...prev,
      [caseId]: { ...(prev[caseId] || {}), [eventIdx]: { id: meddraId, pt } }
    }))
  }

  const handleBatchManualInput = (caseId, eventIdx, field, value) => {
    setBatchManualInputs(prev => ({
      ...prev,
      [caseId]: { ...(prev[caseId] || {}), [eventIdx]: { ...(prev[caseId]?.[eventIdx] || {}), [field]: value } }
    }))
  }

  const toggleEventRow = (caseId, eventIdx) => {
    const key = `${caseId}_${eventIdx}`
    setExpandedEvents(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setProgress({ current: 0, total: 0, status: 'processing' })
    try {
      const arrayBuffer = await file.arrayBuffer()
      const bytes = new Uint8Array(arrayBuffer)
      let binary = ''
      bytes.forEach(b => binary += String.fromCharCode(b))
      const csvB64 = btoa(binary)

      const client = await Client.connect(window.API_URL)
      const job = client.submit("/batch", [csvB64])

      for await (const msg of job) {
        if (msg.data) {
          const parsed = JSON.parse(msg.data[0])
          if (parsed.status === 'processing') {
            setProgress({ current: parsed.current, total: parsed.total, status: 'processing' })
          } else if (parsed.status === 'complete') {
            setProgress({ current: parsed.results.length, total: parsed.results.length, status: 'complete' })
            setResults(parsed.results)
            setUploading(false)
          } else if (parsed.status === 'error') {
            alert("Error processing batch: " + parsed.error)
            setUploading(false)
            setProgress({ current: 0, total: 0, status: 'error' })
            break
          }
        }
      }
    } catch (err) {
      alert("Error processing batch: " + err.message)
      setUploading(false)
      setProgress({ current: 0, total: 0, status: 'error' })
    }
  }

  const exportCSV = () => {
    if (!results) return
    const rows = [["case_id", "is_serious_case", "effect_raw", "meddra_pt", "meddra_id", "suspected_drugs", "review_status"]]
    results.forEach(caseObj => {
      if (caseObj.error) {
        rows.push([caseObj.case_id, "ERROR", caseObj.error.replace(/"/g, '""'), "", "", "", ""])
        return
      }
      if (!caseObj.events || caseObj.events.length === 0) {
        rows.push([caseObj.case_id, caseObj.is_serious_case, "None", "None", "None", "None", "None"])
      } else {
        caseObj.events.forEach((event, idx) => {
          rows.push([
            caseObj.case_id,
            caseObj.is_serious_case,
            `"${event.effect_text.replace(/"/g, '""')}"`,
            `"${batchCorrections[caseObj.case_id]?.[idx]?.pt || event.meddra_pt}"`,
            batchCorrections[caseObj.case_id]?.[idx]?.id || event.meddra_pt_id,
            `"${event.suspected_drugs.map(d => typeof d === 'string' ? d : (d.canonical_name ? `${d.canonical_name} (${d.text})` : d.text)).join(', ')}"`,
            event.review_status
          ])
        })
      }
    })
    const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\n")
    const encodedUri = encodeURI(csvContent)
    const a = document.createElement('a')
    a.href = encodedUri
    a.download = "pv_coder_batch_results.csv"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const exportXMLZip = async () => {
    if (!results) return
    const validResults = results.filter(c => !c.error).map(c => {
      const newEvents = c.events?.map((ev, idx) => ({
        ...ev,
        meddra_pt: batchCorrections[c.case_id]?.[idx]?.pt || ev.meddra_pt,
        meddra_pt_id: batchCorrections[c.case_id]?.[idx]?.id || ev.meddra_pt_id
      })) || [];
      return { ...c, events: newEvents }
    })
    try {
      const client = await Client.connect(window.API_URL)
      const res = await client.predict("/batch_xml_zip", [JSON.stringify(validResults)])
      const zipB64 = res.data[0]
      const bytes = Uint8Array.from(atob(zipB64), c => c.charCodeAt(0))
      const blob = new Blob([bytes], { type: 'application/zip' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `pv_coder_batch_xmls.zip`
      document.body.appendChild(a)
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert("Error downloading XML ZIP")
    }
  }

  const exportValidatedJSON = () => {
    if (!results) return
    const modifiedResults = results.filter(c => !c.error).map(c => {
      const newEvents = c.events?.map((ev, idx) => ({
        ...ev,
        meddra_pt: batchCorrections[c.case_id]?.[idx]?.pt || ev.meddra_pt,
        meddra_pt_id: batchCorrections[c.case_id]?.[idx]?.id || ev.meddra_pt_id
      })) || [];
      return { ...c, events: newEvents }
    })
    const jsonStr = JSON.stringify(modifiedResults, null, 2)
    const blob = new Blob([jsonStr], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = "pv_coder_validated_batch.json"
    document.body.appendChild(a)
    a.click()
    URL.revokeObjectURL(url)
  }

  // Derived metrics
  let totalProcessed = 0;
  let errorCount = 0;
  let seriousCount = 0;
  let reviewRequiredCount = 0;
  let totalEvents = 0;
  let autoCodedEvents = 0;
  let sumConfidence = 0;
  let ptCounts = {};

  if (results) {
    totalProcessed = results.length;
    results.forEach(c => {
      if (c.error) {
        errorCount++;
        return;
      }
      if (c.is_serious_case) seriousCount++;

      let needsReview = false;
      c.events.forEach(e => {
        totalEvents++;
        if (e.review_status === 'Auto-coded') autoCodedEvents++;
        if (e.review_status === 'Human Review') needsReview = true;
        if (e.confidence_score) sumConfidence += e.confidence_score;

        ptCounts[e.meddra_pt] = (ptCounts[e.meddra_pt] || 0) + 1;
      });
      if (needsReview) reviewRequiredCount++;
    });
  }

  const autoCodedPct = totalEvents > 0 ? Math.round((autoCodedEvents / totalEvents) * 100) : 0;
  const avgConfidence = totalEvents > 0 ? Math.round((sumConfidence / totalEvents) * 100) : 0;
  const reviewRate = totalEvents > 0 ? Math.round(((totalEvents - autoCodedEvents) / totalEvents) * 100) : 0;

  const topPTs = Object.entries(ptCounts).sort((a, b) => b[1] - a[1]).slice(0, 4);
  const maxPT = topPTs.length > 0 ? topPTs[0][1] : 1;

  // Filtering
  const filteredResults = results ? results.filter(c => {
    let matchFilter = true;
    if (filter === 'Serious') matchFilter = c.is_serious_case;
    if (filter === 'Needs Review') matchFilter = c.events && c.events.some(e => e.review_status === 'Human Review');
    if (filter === 'Auto-coded') matchFilter = c.events && c.events.every(e => e.review_status === 'Auto-coded');
    if (filter === 'Errors') matchFilter = !!c.error;

    if (!matchFilter) return false;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      if (c.case_id && c.case_id.toLowerCase().includes(term)) return true;
      if (c.narrative && c.narrative.toLowerCase().includes(term)) return true;
      if (c.events && c.events.some(e => e.meddra_pt.toLowerCase().includes(term))) return true;
      return false;
    }
    return true;
  }) : [];

  return (
    <div style={{ animation: 'slideIn 0.3s ease-out' }}>
      {!results ? (
        <>
          <h3 style={{ marginBottom: '1rem' }}>Batch Process CSV</h3>
          <p>Upload a CSV file containing a <code>narrative</code> column. The system will extract and code all adverse events in the background.</p>

          <div className="file-drop-area" onClick={() => !uploading && fileInputRef.current?.click()} style={{ opacity: uploading ? 0.5 : 1, cursor: uploading ? 'default' : 'pointer' }}>
            <input type="file" accept=".csv" ref={fileInputRef} onChange={handleFileChange} disabled={uploading} />
            {file ? (
              <div>
                <h4 style={{ color: 'var(--accent-primary)' }}>{file.name}</h4>
                <p>{uploading ? 'Processing in progress...' : 'Ready to process'}</p>
              </div>
            ) : (
              <div>
                <h4>Click to browse or drag & drop</h4>
                <p>CSV files only</p>
              </div>
            )}
          </div>

          <button className="btn btn-primary" style={{ width: '100%', marginTop: '1.5rem' }} disabled={!file || uploading} onClick={handleUpload}>
            {uploading ? "Processing Batch..." : "Process Batch"}
          </button>

          {uploading && (
            <div style={{ marginTop: '2rem', background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                <span>Processing case {progress.current} of {progress.total}</span>
                <span>{progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0}%</span>
              </div>
              <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${progress.total > 0 ? (progress.current / progress.total) * 100 : 0}%`, background: 'var(--accent-primary)', transition: 'width 0.2s ease-out' }}></div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h2>Batch Dashboard</h2>
            <button className="btn btn-secondary" onClick={() => setResults(null)}>New Batch Upload</button>
          </div>

          {/* Metric Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Cases Processed</div>
              <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{totalProcessed}</div>
            </div>
            <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Events Detected</div>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--accent-primary)' }}>{totalEvents}</div>
            </div>
            <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--warning)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Serious Cases</div>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--warning)' }}>{seriousCount}</div>
            </div>
            <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Review Required</div>
              <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{reviewRequiredCount}</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
            <div style={{ background: 'var(--bg-tertiary)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Auto-coded</span>
                <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--success)' }}>{autoCodedPct}%</span>
              </div>
            </div>
            <div style={{ background: 'var(--bg-tertiary)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Review Rate</span>
                <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--warning)' }}>{reviewRate}%</span>
              </div>
            </div>
            <div style={{ background: 'var(--bg-tertiary)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Avg Confidence</span>
                <span style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{avgConfidence}%</span>
              </div>
            </div>
          </div>

          {/* Visualizations */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
            <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)' }}>
              <h4 style={{ marginBottom: '1.5rem' }}>Case Seriousness Breakdown</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                    <span>Serious</span>
                    <span>{seriousCount}</span>
                  </div>
                  <div style={{ width: '100%', height: '12px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${totalProcessed ? (seriousCount / totalProcessed) * 100 : 0}%`, background: 'var(--warning)' }}></div>
                  </div>
                </div>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                    <span>Non-serious</span>
                    <span>{totalProcessed - seriousCount - errorCount}</span>
                  </div>
                  <div style={{ width: '100%', height: '12px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${totalProcessed ? ((totalProcessed - seriousCount - errorCount) / totalProcessed) * 100 : 0}%`, background: 'var(--success)' }}></div>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)' }}>
              <h4 style={{ marginBottom: '1.5rem' }}>Most Frequent MedDRA PTs</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                {topPTs.map(([pt, count], i) => (
                  <div key={i}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem', fontSize: '0.85rem' }}>
                      <span>{pt}</span>
                      <span style={{ color: 'var(--text-secondary)' }}>{count}</span>
                    </div>
                    <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${(count / maxPT) * 100}%`, background: 'var(--accent-primary)' }}></div>
                    </div>
                  </div>
                ))}
                {topPTs.length === 0 && <div style={{ color: 'var(--text-secondary)' }}>No events coded.</div>}
              </div>
            </div>
          </div>

          {/* Export Actions */}
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
            <button className="btn btn-secondary" onClick={exportCSV} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Download size={18} /> Export Results (CSV)
            </button>
            <button className="btn btn-secondary" onClick={exportValidatedJSON} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={18} /> Export Validated JSON
            </button>
            <button className="btn btn-secondary" onClick={exportXMLZip} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Download size={18} /> Export E2B XMLs (.zip)
            </button>
          </div>

          <h3 style={{ marginBottom: '1rem' }}>Case Details</h3>

          {/* Filters & Search */}
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', flex: 1, minWidth: '250px' }}>
              <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
              <input
                type="text"
                placeholder="Search cases, narratives, or events..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                style={{ width: '100%', padding: '0.6rem 0.6rem 0.6rem 2.5rem', background: 'var(--bg-tertiary)', border: '1px solid var(--glass-border)', color: 'white', borderRadius: 'var(--radius-md)' }}
              />
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {['All', 'Serious', 'Needs Review', 'Auto-coded', 'Errors'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  style={{
                    padding: '0.4rem 1rem',
                    borderRadius: '20px',
                    fontSize: '0.85rem',
                    background: filter === f ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                    border: '1px solid var(--glass-border)',
                    cursor: 'pointer',
                    color: filter === f ? 'white' : 'var(--text-secondary)'
                  }}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th style={{ width: '40px' }}></th>
                  <th>Case ID</th>
                  <th>Serious?</th>
                  <th>Events</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((c, i) => (
                  <React.Fragment key={i}>
                    <tr onClick={() => setExpandedCaseId(expandedCaseId === c.case_id ? null : c.case_id)} style={{ cursor: 'pointer' }}>
                      <td>
                        {expandedCaseId === c.case_id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </td>
                      <td>{c.case_id}</td>
                      <td>
                        {c.error ? <span style={{ color: 'var(--text-secondary)' }}>-</span> : (
                          c.is_serious_case ?
                            <span style={{ color: 'var(--warning)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><AlertTriangle size={14} /> Yes</span> :
                            <span style={{ color: 'var(--success)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><CheckCircle size={14} /> No</span>
                        )}
                      </td>
                      <td>{c.error ? '-' : `${c.events?.length || 0} event(s)`}</td>
                      <td>
                        {c.error ? <span style={{ color: 'var(--text-secondary)' }}><XCircle size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Processing Error</span> : (
                          c.events?.some(e => e.review_status === 'Human Review') ?
                            <span style={{ color: 'var(--warning)' }}><AlertTriangle size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Needs Review</span> :
                            <span style={{ color: 'var(--success)' }}><CheckCircle size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Auto-coded</span>
                        )}
                      </td>
                    </tr>
                    {expandedCaseId === c.case_id && (
                      <tr style={{ background: 'var(--bg-tertiary)' }}>
                        <td colSpan="5" style={{ padding: '2rem' }}>
                          {c.error ? (
                            <div style={{ color: 'var(--warning)' }}>
                              <h4 style={{ marginBottom: '0.5rem' }}>Processing Error</h4>
                              <p style={{ fontFamily: 'monospace', background: 'rgba(0,0,0,0.5)', padding: '1rem', borderRadius: '4px' }}>{c.error}</p>
                            </div>
                          ) : (
                            <div>
                              <h4 style={{ color: 'var(--accent-primary)', marginBottom: '1rem' }}>Narrative</h4>
                              <HighlightedText
                                text={c.narrative}
                                events={c.events}
                                drugs={c.extracted_drugs}
                                excluded={c.excluded_findings}
                              />
                              <h4 style={{ color: 'var(--accent-primary)', marginTop: '2rem', marginBottom: '1rem' }}>Extracted Entities</h4>
                              <table style={{ background: 'var(--bg-primary)' }}>
                                <thead>
                                  <tr>
                                    <th style={{ width: '40px' }}></th>
                                    <th>Event</th>
                                    <th>MedDRA PT</th>
                                    <th>MedDRA ID</th>
                                    <th>Suspected Drugs</th>
                                    <th>Status</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {c.events?.map((ev, idx) => (
                                    <React.Fragment key={idx}>
                                      <tr onClick={() => toggleEventRow(c.case_id, idx)} style={{ cursor: 'pointer', borderBottom: '1px solid var(--glass-border)', background: expandedEvents[`${c.case_id}_${idx}`] ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                                        <td style={{ padding: '1rem 0.5rem' }}>
                                          {expandedEvents[`${c.case_id}_${idx}`] ? <ChevronDown size={14} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> : <ChevronRight size={14} style={{ marginRight: '8px', verticalAlign: 'middle' }} />}
                                        </td>
                                        <td>{ev.effect_text}</td>
                                        <td>{batchCorrections[c.case_id]?.[idx]?.pt || ev.meddra_pt}</td>
                                        <td>{batchCorrections[c.case_id]?.[idx]?.id || ev.meddra_pt_id}</td>
                                        <td>{ev.suspected_drugs.map(d => typeof d === 'string' ? d : (d.canonical_name ? `${d.canonical_name} (${d.text})` : d.text)).join(', ') || 'None'}</td>
                                        <td>
                                          {ev.review_status === 'Auto-coded' ?
                                            <span style={{ color: 'var(--success)' }}><CheckCircle size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Auto-coded</span> :
                                            <span style={{ color: 'var(--warning)' }}><AlertTriangle size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Review</span>}
                                        </td>
                                      </tr>

                                      {/* EXPANDED HITL ROW */}
                                      {expandedEvents[`${c.case_id}_${idx}`] && (
                                        <tr>
                                          <td colSpan="6" style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderBottom: '1px solid var(--glass-border)' }}>
                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                                              {/* AI Decision Panel */}
                                              <div>
                                                <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.8rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Info size={14} /> AI DECISION DETAIL</h4>
                                                <div style={{ background: 'var(--bg-tertiary)', padding: '1.2rem', borderRadius: 'var(--radius-md)' }}>
                                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.8rem' }}>
                                                    <span style={{ color: 'var(--text-secondary)' }}>Confidence Score:</span>
                                                    <span style={{ fontWeight: 'bold' }}>{(ev.confidence_score * 100).toFixed(1)}%</span>
                                                  </div>
                                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.8rem' }}>
                                                    <span style={{ color: 'var(--text-secondary)' }}>Seriousness:</span>
                                                    <span style={{ color: ev.is_serious ? 'var(--warning)' : 'var(--text-primary)' }}>
                                                      {ev.is_serious ? "Serious (" + ev.seriousness_reason + ")" : 'Non-serious'}
                                                    </span>
                                                  </div>
                                                  {ev.seriousness_evidence && (
                                                    <div style={{ marginTop: '0.8rem', paddingTop: '0.8rem', borderTop: '1px solid var(--glass-border)', fontSize: '0.9rem' }}>
                                                      <span style={{ color: 'var(--text-secondary)' }}>Trigger Evidence:</span><br />
                                                      <em style={{ color: 'var(--accent-primary)', display: 'inline-block', marginTop: '0.4rem' }}>"{ev.seriousness_evidence}"</em>
                                                    </div>
                                                  )}
                                                </div>
                                              </div>

                                              {/* HITL Inline Review */}
                                              <div>
                                                {ev.review_status === "Human Review" ? (
                                                  <div>
                                                    <h4 style={{ color: 'var(--warning)', marginBottom: '0.8rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><AlertTriangle size={14} /> REVIEW REQUIRED</h4>
                                                    <div style={{ background: 'var(--bg-tertiary)', padding: '1.2rem', borderRadius: 'var(--radius-md)' }}>
                                                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                                                        {ev.top_candidates?.map((cand, candIdx) => (
                                                          <label key={candIdx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                                            <input
                                                              type="radio"
                                                              name={`review_${c.case_id}_${idx}`}
                                                              checked={batchCorrections[c.case_id]?.[idx]?.id === cand.id || (!batchCorrections[c.case_id]?.[idx] && candIdx === 0)}
                                                              onChange={() => handleBatchCorrection(c.case_id, idx, cand.id, cand.pt)}
                                                            />
                                                            {cand.pt} (ID: {cand.id}) - Score: {cand.score.toFixed(3)}
                                                          </label>
                                                        ))}
                                                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                                          <input
                                                            type="radio"
                                                            name={`review_${c.case_id}_${idx}`}
                                                            checked={batchCorrections[c.case_id]?.[idx]?.id === "REJECT" || (batchCorrections[c.case_id]?.[idx] && !ev.top_candidates?.find(x => x.id === batchCorrections[c.case_id]?.[idx].id))}
                                                            onChange={() => handleBatchCorrection(c.case_id, idx, batchManualInputs[c.case_id]?.[idx]?.id || "REJECT", batchManualInputs[c.case_id]?.[idx]?.pt || "Reject / Other")}
                                                          />
                                                          Reject / Manual Input
                                                        </label>

                                                        {(batchCorrections[c.case_id]?.[idx]?.id === "REJECT" || (batchCorrections[c.case_id]?.[idx] && !ev.top_candidates?.find(x => x.id === batchCorrections[c.case_id]?.[idx].id))) && (
                                                          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', marginLeft: '1.5rem' }}>
                                                            <input
                                                              type="text"
                                                              style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)', background: 'var(--bg-primary)', color: 'var(--text-primary)', flex: 1 }}
                                                              placeholder="Enter MedDRA Preferred Term (PT)..."
                                                              value={batchManualInputs[c.case_id]?.[idx]?.pt || ''}
                                                              onChange={(e) => handleBatchManualInput(c.case_id, idx, 'pt', e.target.value)}
                                                            />
                                                            <input
                                                              type="text"
                                                              style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)', background: 'var(--bg-primary)', color: 'var(--text-primary)', width: '120px' }}
                                                              placeholder="ID (e.g. 1000)"
                                                              value={batchManualInputs[c.case_id]?.[idx]?.id || ''}
                                                              onChange={(e) => handleBatchManualInput(c.case_id, idx, 'id', e.target.value)}
                                                            />
                                                            <button
                                                              className="btn btn-primary"
                                                              style={{ padding: '0.5rem 1rem' }}
                                                              onClick={() => handleBatchCorrection(c.case_id, idx, batchManualInputs[c.case_id]?.[idx]?.id, batchManualInputs[c.case_id]?.[idx]?.pt)}
                                                            >
                                                              Apply
                                                            </button>
                                                          </div>
                                                        )}
                                                      </div>
                                                    </div>
                                                  </div>
                                                ) : (
                                                  <div>
                                                    <h4 style={{ color: 'var(--success)', marginBottom: '0.8rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><CheckCircle size={14} /> NO REVIEW REQUIRED</h4>
                                                    <div style={{ background: 'var(--bg-tertiary)', padding: '1.2rem', borderRadius: 'var(--radius-md)' }}>
                                                      <p style={{ color: 'var(--text-secondary)' }}>The AI confidence was high enough to automatically map this event.</p>
                                                    </div>
                                                  </div>
                                                )}
                                              </div>
                                            </div>
                                          </td>
                                        </tr>
                                      )}
                                    </React.Fragment>
                                  ))}
                                  {c.events?.length === 0 && <tr><td colSpan="6">No events found.</td></tr>}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
                {filteredResults.length === 0 && (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>No cases match the current filters.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}


function UserGuide() {
  return (
    <div style={{ animation: 'slideIn 0.3s ease-out', lineHeight: '1.8' }}>
      <h2 style={{ marginBottom: '1.5rem', color: 'var(--accent-primary)' }}>How to Use PV-Coder</h2>

      <section style={{ marginBottom: '2rem' }}>
        <h3>1. What is PV-Coder?</h3>
        <p>PV-Coder is an AI-assisted Pharmacovigilance (PV) intake engine. When pharmaceutical companies receive emails or letters about side effects, a human usually has to manually read the text and look up standard MedDRA codes. PV-Coder automates this using Natural Language Processing (NLP) to instantly extract drugs and adverse events, and cross-reference them against the MedDRA dictionary.</p>
      </section>

      <section style={{ marginBottom: '2rem' }}>
        <h3>2. Single Intake & Human-in-the-Loop</h3>
        <p>In the <strong>Single Intake</strong> tab, you can paste a clinical narrative. The AI will highlight suspected adverse events and drugs.</p>
        <ul style={{ marginLeft: '1.5rem', color: 'var(--text-secondary)' }}>
          <li>If the AI is highly confident (e.g. mapping "heart attack" to "Myocardial Infarction"), it will mark the status as <span style={{ color: 'var(--success)' }}>Auto-coded</span>.</li>
          <li>If the AI is unsure, it will flag it as <span style={{ color: 'var(--warning)' }}>Review Needed</span>. A Human-in-the-Loop panel will appear below, allowing a human scientist to make the final decision.</li>
          <li>If the text contains critical keywords (like "fatal" or "hospitalized"), it triggers a <strong>Serious Case</strong> alarm for expedited regulatory reporting (15-day timeline).</li>
        </ul>
      </section>

      <section style={{ marginBottom: '2rem' }}>
        <h3>3. Batch Uploads</h3>
        <p>If you have thousands of historical reports in a spreadsheet, use the <strong>Batch Upload</strong> tab. Upload a CSV with a column named <code>narrative</code>, and the backend will process all cases silently and return a compiled CSV with the MedDRA codes.</p>
      </section>

      <section>
        <h3>4. E2B (R3) XML & Reporting</h3>
        <p>After reviewing a single case, you can export it to PDF (for internal team meetings) or to an E2B-style XML file. XML is the global standard format used to transmit cases between safety databases like Oracle Argus and regulatory agencies like the FDA or EMA.</p>
      </section>
    </div>
  )
}

export default App
