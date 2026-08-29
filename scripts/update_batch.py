import codecs
import re

with codecs.open('client/src/App.jsx', 'r', 'utf-8') as f:
    text = f.read()

# Update imports
text = text.replace(
    "import { AlertTriangle, CheckCircle, Download, FileText, ChevronDown, ChevronRight, Info, Circle, CircleDot } from 'lucide-react'",
    "import { AlertTriangle, CheckCircle, Download, FileText, ChevronDown, ChevronRight, Info, Circle, CircleDot, Search, XCircle } from 'lucide-react'"
)

# New BatchUpload code
new_batch_upload = """function BatchUpload() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0, status: 'idle' })
  const [results, setResults] = useState(null)
  const fileInputRef = useRef(null)

  const [searchTerm, setSearchTerm] = useState('')
  const [filter, setFilter] = useState('All')
  const [expandedCaseId, setExpandedCaseId] = useState(null)

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
      setResults(null)
      setProgress({ current: 0, total: 0, status: 'idle' })
      setSearchTerm('')
      setFilter('All')
      setExpandedCaseId(null)
    }
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
    const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\\n")
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
    const validResults = results.filter(c => !c.error)
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
        if (e.review_status === 'auto-coded') autoCodedEvents++;
        if (e.review_status === 'review-required') needsReview = true;
        if (e.confidence) sumConfidence += e.confidence;
        
        ptCounts[e.meddra_pt] = (ptCounts[e.meddra_pt] || 0) + 1;
      });
      if (needsReview) reviewRequiredCount++;
    });
  }

  const autoCodedPct = totalEvents > 0 ? Math.round((autoCodedEvents / totalEvents) * 100) : 0;
  const avgConfidence = totalEvents > 0 ? Math.round((sumConfidence / totalEvents) * 100) : 0;
  const reviewRate = totalEvents > 0 ? Math.round(((totalEvents - autoCodedEvents) / totalEvents) * 100) : 0;

  const topPTs = Object.entries(ptCounts).sort((a,b) => b[1] - a[1]).slice(0, 4);
  const maxPT = topPTs.length > 0 ? topPTs[0][1] : 1;

  // Filtering
  const filteredResults = results ? results.filter(c => {
    let matchFilter = true;
    if (filter === 'Serious') matchFilter = c.is_serious_case;
    if (filter === 'Needs Review') matchFilter = c.events && c.events.some(e => e.review_status === 'review-required');
    if (filter === 'Auto-coded') matchFilter = c.events && c.events.every(e => e.review_status === 'auto-coded');
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
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--warning)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>{seriousCount} <AlertTriangle size={24}/></div>
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
                    <div style={{ height: '100%', width: `${totalProcessed ? (seriousCount/totalProcessed)*100 : 0}%`, background: 'var(--warning)' }}></div>
                  </div>
                </div>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                    <span>Non-serious</span>
                    <span>{totalProcessed - seriousCount - errorCount}</span>
                  </div>
                  <div style={{ width: '100%', height: '12px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${totalProcessed ? ((totalProcessed - seriousCount - errorCount)/totalProcessed)*100 : 0}%`, background: 'var(--success)' }}></div>
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
                      <div style={{ height: '100%', width: `${(count/maxPT)*100}%`, background: 'var(--accent-primary)' }}></div>
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
                        {expandedCaseId === c.case_id ? <ChevronDown size={16}/> : <ChevronRight size={16}/>}
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
                        {c.error ? <span style={{ color: 'var(--text-secondary)' }}><XCircle size={14} style={{verticalAlign: 'middle', marginRight: '4px'}}/> Processing Error</span> : (
                          c.events?.some(e => e.review_status === 'review-required') ?
                          <span style={{ color: 'var(--warning)' }}><AlertTriangle size={14} style={{verticalAlign: 'middle', marginRight: '4px'}}/> Needs Review</span> :
                          <span style={{ color: 'var(--success)' }}><CheckCircle size={14} style={{verticalAlign: 'middle', marginRight: '4px'}}/> Auto-coded</span>
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
                                    <th>Event</th>
                                    <th>MedDRA PT</th>
                                    <th>Suspected Drugs</th>
                                    <th>Status</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {c.events?.map((ev, idx) => (
                                    <tr key={idx}>
                                      <td>{ev.effect_text}</td>
                                      <td>{ev.meddra_pt}</td>
                                      <td>{ev.suspected_drugs.join(', ') || 'None'}</td>
                                      <td>{ev.review_status}</td>
                                    </tr>
                                  ))}
                                  {c.events?.length === 0 && <tr><td colSpan="4">No events found.</td></tr>}
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
"""

text = re.sub(r'function BatchUpload\(\) \{.*?\n\}\n\nfunction UserGuide', new_batch_upload + '\n\nfunction UserGuide', text, flags=re.DOTALL)

with codecs.open('client/src/App.jsx', 'w', 'utf-8') as f:
    f.write(text)

print('Updated App.jsx with new BatchUpload dashboard.')
