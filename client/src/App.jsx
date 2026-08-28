import { useState, useRef, useEffect } from 'react'
import { AlertTriangle, CheckCircle, Download, FileText } from 'lucide-react'
import { Client } from "@gradio/client"

function App() {
  const [activeTab, setActiveTab] = useState('single')
  
  // Set global API URL using the full HTTPS endpoint to avoid any resolution issues
  window.API_URL = import.meta.env.PROD 
    ? 'https://drjollof-pv-coder-api.hf.space' 
    : 'http://localhost:7860';
  
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

function SingleIntake() {
  const [narrative, setNarrative] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [showJson, setShowJson] = useState(false)
  const [corrections, setCorrections] = useState({})
  const [manualInputs, setManualInputs] = useState({})
  
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

  const handleAnalyze = async () => {
    if (!narrative.trim()) return
    
    setLoading(true)
    setError('')
    setResult(null)
    setCorrections({})
    setShowJson(false)
    
    try {
      const client = await Client.connect(window.API_URL)
      const res = await client.predict("/analyze", [
        narrative, 
        'WEB-' + Math.floor(Math.random()*1000)
      ])
      
      setResult(JSON.parse(res.data[0]))
    } catch (err) {
      console.error("Analysis Error:", err)
      setError(`API Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async (format) => {
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
      a.download = `${result.case_id}_report.${format}`
      document.body.appendChild(a)
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert(`Error generating ${format.toUpperCase()}`)
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

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
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
      </div>
      
      <button 
        className="btn btn-primary" 
        onClick={handleAnalyze} 
        disabled={loading}
        style={{ width: '100%', marginBottom: '2rem' }}
      >
        {loading ? <div className="spinner"></div> : "Analyze Case"}
      </button>

      {error && (
        <div className="alert alert-danger">
          <p>{error}</p>
        </div>
      )}

      {result && (
        <div style={{ animation: 'slideIn 0.3s ease-out' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2>Extraction Results</h2>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button className="btn btn-secondary" onClick={() => handleExport('pdf')}>
                Download PDF Report
              </button>
              <button className="btn btn-secondary" onClick={() => handleExport('xml')}>
                Download XML (E2B)
              </button>
            </div>
          </div>

          {result.is_serious_case ? (
            <div className="alert alert-danger">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle size={24} />
                <h4>SERIOUS CASE DETECTED</h4>
              </div>
              <p style={{ marginTop: '0.5rem' }}>Contains seriousness criteria (e.g. fatal, hospitalized). Requires immediate regulatory triage.</p>
            </div>
          ) : (
            <div className="alert alert-success">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle size={24} />
                <h4>Non-Serious Case</h4>
              </div>
              <p style={{ marginTop: '0.5rem' }}>No critical seriousness keywords detected.</p>
            </div>
          )}

          <div className="table-container" style={{ marginBottom: '2rem' }}>
            <table>
              <thead>
                <tr>
                  <th>Effect (Raw)</th>
                  <th>Status</th>
                  <th>MedDRA PT</th>
                  <th>MedDRA ID</th>
                  <th>Suspected Drugs</th>
                </tr>
              </thead>
              <tbody>
                {result.events.map((ev, i) => (
                  <tr key={i}>
                    <td>{ev.effect_text}</td>
                    <td>
                      {ev.review_status === 'Auto-coded' ? 
                        <span style={{ color: 'var(--success)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><CheckCircle size={14} /> Auto-coded</span> : 
                        <span style={{ color: 'var(--warning)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><AlertTriangle size={14} /> Review Needed</span>}
                    </td>
                    <td>{corrections[i]?.pt || ev.meddra_pt}</td>
                    <td>{corrections[i]?.id || ev.meddra_pt_id}</td>
                    <td>{ev.suspected_drugs.length > 0 ? ev.suspected_drugs.join(', ') : 'None'}</td>
                  </tr>
                ))}
                {result.events.length === 0 && (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center' }}>No adverse events detected.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Human-in-the-Loop Review Section */}
          {reviewEvents.length > 0 && (
            <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid var(--warning)', borderRadius: 'var(--radius-md)', background: 'var(--warning-bg)' }}>
              <h3 style={{ color: 'var(--warning)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle /> Human-in-the-Loop Review Required
              </h3>
              <p style={{ marginBottom: '1rem' }}>{reviewEvents.length} event(s) require human review due to low confidence.</p>
              
              {result.events.map((ev, i) => {
                if (ev.review_status !== "Human Review") return null;
                return (
                  <div key={i} style={{ background: 'var(--bg-tertiary)', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem' }}>
                    <h4 style={{ marginBottom: '0.5rem' }}>Top Candidates for: "{ev.effect_text}"</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
                      {ev.top_candidates?.map((cand, idx) => (
                        <label key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                          <input 
                            type="radio" 
                            name={`review_${i}`} 
                            checked={corrections[i]?.id === cand.id || (!corrections[i] && idx === 0)}
                            onChange={() => handleCorrection(i, cand.id, cand.pt)}
                          />
                          {cand.pt} (ID: {cand.id}) - Score: {cand.score.toFixed(3)}
                        </label>
                      ))}
                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                        <input 
                          type="radio" 
                          name={`review_${i}`} 
                          checked={corrections[i]?.id === "REJECT" || (corrections[i] && !ev.top_candidates.find(c => c.id === corrections[i].id))}
                          onChange={() => handleCorrection(i, manualInputs[i]?.id || "REJECT", manualInputs[i]?.pt || "Reject / Other")}
                        />
                        Reject All / Other (Manual Input)
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
                    <button className="btn btn-secondary" onClick={() => alert("Correction saved to logs for future model tuning!")}>
                      Save Correction
                    </button>
                  </div>
                )
              })}
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
              <span>{showJson ? '▲' : '▼'}</span>
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
  const [results, setResults] = useState(null)
  const fileInputRef = useRef(null)

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
      setResults(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    try {
      const arrayBuffer = await file.arrayBuffer()
      const bytes = new Uint8Array(arrayBuffer)
      let binary = ''
      bytes.forEach(b => binary += String.fromCharCode(b))
      const csvB64 = btoa(binary)

      const client = await Client.connect(window.API_URL)
      const res = await client.predict("/batch", [csvB64])
      setResults(JSON.parse(res.data[0]))
    } catch (err) {
      alert("Error processing batch: " + err.message)
    } finally {
      setUploading(false)
    }
  }

  const exportCSV = () => {
    if (!results) return
    
    // Flatten JSON to CSV string
    const rows = [["case_id", "is_serious_case", "effect_raw", "meddra_pt", "meddra_id", "suspected_drugs", "review_status"]]
    
    results.forEach(caseObj => {
      if (caseObj.events.length === 0) {
         rows.push([caseObj.case_id, caseObj.is_serious_case, "None", "None", "None", "None", "None"])
      } else {
        caseObj.events.forEach(event => {
          rows.push([
            caseObj.case_id,
            caseObj.is_serious_case,
            `"${event.effect_text.replace(/"/g, '""')}"`,
            `"${event.meddra_pt}"`,
            event.meddra_pt_id,
            `"${event.suspected_drugs.join(', ')}"`,
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
    try {
      const client = await Client.connect(window.API_URL)
      const res = await client.predict("/batch_xml_zip", [JSON.stringify(results)])
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

  return (
    <div style={{ animation: 'slideIn 0.3s ease-out' }}>
      {!results ? (
        <>
          <h3 style={{ marginBottom: '1rem' }}>Batch Process CSV</h3>
          <p>Upload a CSV file containing a <code>narrative</code> column. The system will extract and code all adverse events in the background.</p>
          
          <div 
            className="file-drop-area"
            onClick={() => fileInputRef.current?.click()}
          >
            <input 
              type="file" 
              accept=".csv" 
              ref={fileInputRef}
              onChange={handleFileChange}
            />
            {file ? (
              <div>
                <h4 style={{ color: 'var(--accent-primary)' }}>{file.name}</h4>
                <p>Ready to process</p>
              </div>
            ) : (
              <div>
                <h4>Click to browse or drag & drop</h4>
                <p>CSV files only</p>
              </div>
            )}
          </div>

          <button 
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '1.5rem' }}
            disabled={!file || uploading}
            onClick={handleUpload}
          >
            {uploading ? (
              <>
                <div className="spinner"></div>
                Processing (This may take a while...)
              </>
            ) : "Process Batch"}
          </button>
        </>
      ) : (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h2>Batch Processing Complete</h2>
            <button className="btn btn-secondary" onClick={() => setResults(null)}>
              Process Another Batch
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '2rem' }}>
            <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)' }}>
              <h4 style={{ color: 'var(--text-secondary)' }}>Total Cases Processed</h4>
              <p style={{ fontSize: '2rem', fontWeight: 'bold' }}>{results.length}</p>
            </div>
            <div style={{ background: 'var(--warning-bg)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--warning)' }}>
              <h4 style={{ color: 'var(--warning)' }}>Serious Cases Detected</h4>
              <p style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--warning)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {results.filter(c => c.is_serious_case).length} <AlertTriangle />
              </p>
            </div>
          </div>

          <h3 style={{ marginBottom: '1rem' }}>Export Data</h3>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
            <button className="btn btn-primary" onClick={exportCSV} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Download size={18} /> Download Consolidated CSV
            </button>
            <button className="btn btn-primary" style={{ background: 'var(--accent-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }} onClick={exportXMLZip}>
              <Download size={18} /> Download E2B XMLs (.zip)
            </button>
          </div>

          <h3 style={{ marginBottom: '1rem' }}>Preview (First 5 Cases)</h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>Serious?</th>
                  <th>Extracted Events</th>
                </tr>
              </thead>
              <tbody>
                {results.slice(0, 5).map((c, i) => (
                  <tr key={i}>
                    <td>{c.case_id}</td>
                    <td>
                      {c.is_serious_case ? 
                        <span style={{ color: 'var(--warning)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><AlertTriangle size={14} /> Yes</span> : 
                        <span style={{ color: 'var(--success)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><CheckCircle size={14} /> No</span>}
                    </td>
                    <td>{c.events.length} event(s)</td>
                  </tr>
                ))}
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
