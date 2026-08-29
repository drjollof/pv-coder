function HighlightedText({ text, events, drugs, excluded }) {
  const spans = [];
  (events || []).forEach((e, i) => { if(e.start_char != null) spans.push({ start: e.start_char, end: e.end_char, type: 'event', label: 'Adverse Event', id: "ev_", color: 'var(--accent-primary)', bg: 'rgba(99, 102, 241, 0.2)' }); });
  (drugs || []).forEach((d, i) => { if(d.start_char != null) spans.push({ start: d.start_char, end: d.end_char, type: 'drug', label: 'Suspected Drug', id: "dr_", color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.2)' }); });
  (excluded || []).forEach((x, i) => { if(x.start_char != null) spans.push({ start: x.start_char, end: x.end_char, type: 'excluded', label: "Excluded: " + x.reason, id: "ex_", color: '#6b7280', bg: 'rgba(107, 114, 128, 0.2)' }); });
  
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
  validSpans.forEach(s => {
    if (s.start > cursor) {
      parts.push(<span key={"t_"}>{text.substring(cursor, s.start)}</span>);
    }
    parts.push(
      <span key={s.id} style={{ backgroundColor: s.bg, color: s.color, padding: '2px 4px', borderRadius: '4px', border: "1px solid " + s.color, cursor: 'pointer', position: 'relative' }} title={s.label}>
        {text.substring(s.start, s.end)}
      </span>
    );
    cursor = s.end;
  });
  if (cursor < text.length) {
    parts.push(<span key={"t_"}>{text.substring(cursor)}</span>);
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
    setExpandedRows(prev => ({...prev, [idx]: !prev[idx]}));
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
        'WEB-' + Math.floor(Math.random()*1000)
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
            fontWeight: idx === currentStep ? 'bold' : 'normal'
          }}>
            {idx < currentStep ? '?' : (idx === currentStep ? '?' : '?')} {step}
            {idx < workflowSteps.length - 1 && ' ---'}
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
                  <option key={i} value={i}>Clinical Case #{i+1}</option>
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
            <p>? Extracting entities</p>
            <p>? Resolving clinical context</p>
            <p>? Mapping MedDRA terms</p>
            <p>? Building case</p>
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
              <div style={{ fontWeight: 'bold', color: result.is_serious_case ? 'var(--warning)' : 'var(--success)' }}>
                {result.is_serious_case ? '? Serious' : '? Non-serious'}
              </div>
              {result.is_serious_case && result.case_seriousness_reason && (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                  {result.case_seriousness_reason} detected.
                </div>
              )}
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Processing Status</div>
              <div style={{ fontWeight: 'bold', color: reviewEvents.length > 0 ? 'var(--warning)' : 'var(--success)' }}>
                {reviewEvents.length > 0 ? '? Review Required' : '? Auto-coded'}
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
                <span><span style={{ display: 'inline-block', width: '10px', height: '10px', background: 'var(--accent-primary)', marginRight: '4px' }}></span> Adverse Event</span>
                <span><span style={{ display: 'inline-block', width: '10px', height: '10px', background: '#3b82f6', marginRight: '4px' }}></span> Suspected Drug</span>
                <span><span style={{ display: 'inline-block', width: '10px', height: '10px', background: '#6b7280', marginRight: '4px' }}></span> Excluded</span>
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
                        {expandedRows[i] ? <ChevronDown size={14} style={{ marginRight: '8px', verticalAlign: 'middle' }}/> : <ChevronRight size={14} style={{ marginRight: '8px', verticalAlign: 'middle' }}/>}
                        {ev.effect_text}
                      </td>
                      <td style={{ padding: '1rem 0.5rem' }}>
                        {ev.review_status === 'Auto-coded' ? 
                          <span style={{ color: 'var(--success)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><CheckCircle size={14} /> Auto-coded</span> : 
                          <span style={{ color: 'var(--warning)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><AlertTriangle size={14} /> Review</span>}
                      </td>
                      <td style={{ padding: '1rem 0.5rem' }}>{corrections[i]?.pt || ev.meddra_pt}</td>
                      <td style={{ padding: '1rem 0.5rem' }}>{corrections[i]?.id || ev.meddra_pt_id}</td>
                      <td style={{ padding: '1rem 0.5rem' }}>{ev.suspected_drugs.length > 0 ? ev.suspected_drugs.join(', ') : 'None'}</td>
                    </tr>
                    
                    {/* EXPANDED DETAIL ROW */}
                    {expandedRows[i] && (
                      <tr>
                        <td colSpan="5" style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderBottom: '1px solid var(--glass-border)' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                            {/* AI Decision Panel */}
                            <div>
                              <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.8rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Info size={14}/> AI DECISION DETAIL</h4>
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
                                    <span style={{ color: 'var(--text-secondary)' }}>Trigger Evidence:</span><br/>
                                    <em style={{ color: 'var(--accent-primary)', display: 'inline-block', marginTop: '0.4rem' }}>"{ev.seriousness_evidence}"</em>
                                  </div>
                                )}
                              </div>
                            </div>
                            
                            {/* HITL Inline Review */}
                            <div>
                              {ev.review_status === "Human Review" && !validated ? (
                                <div>
                                  <h4 style={{ color: 'var(--warning)', marginBottom: '0.8rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><AlertTriangle size={14}/> REVIEW REQUIRED</h4>
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
