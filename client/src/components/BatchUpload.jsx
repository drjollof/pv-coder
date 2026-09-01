import React, { useState, useRef, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Download, FileText, ChevronDown, ChevronRight, Info, Search, XCircle, CircleDot, Play } from 'lucide-react';
import { Client } from "@gradio/client";
import HighlightedText from './HighlightedText';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import TechnicalDebugView from './TechnicalDebugView';

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

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.target.tagName === 'INPUT' && e.target.type !== 'radio') || e.target.tagName === 'TEXTAREA') return;
      
      const expandedKey = Object.keys(expandedEvents).find(k => expandedEvents[k]);
      if (!expandedKey) return;
      
      const [cId, idxStr] = expandedKey.split('_');
      const idx = parseInt(idxStr);
      
      const c = results?.find(x => x.case_id === cId);
      if (!c) return;
      
      const ev = c.events?.[idx];
      if (!ev) return;

      const reviewableIndices = c.events.map((evt, i) => evt.review_status === "Human Review" ? i : -1).filter(i => i !== -1);
      const currentIdxInReviewable = reviewableIndices.indexOf(idx);

      if (e.key === 'Escape') {
        setExpandedEvents(prev => ({...prev, [expandedKey]: false}));
        return;
      }
      
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
         e.preventDefault();
         if (ev.review_status === "Human Review") {
           const optionsCount = (ev.top_candidates?.length || 0) + 1;
           let currentIndex = 0;
           const currentCorrection = batchCorrections[cId]?.[idx];
           if (currentCorrection) {
             if (currentCorrection.id === "REJECT" || (currentCorrection.id && !ev.top_candidates?.find(x => x.id === currentCorrection.id))) {
               currentIndex = optionsCount - 1;
             } else {
               currentIndex = ev.top_candidates.findIndex(cand => cand.id === currentCorrection.id);
               if (currentIndex === -1) currentIndex = 0;
             }
           }
           
           let nextIndex = currentIndex;
           if (e.key === 'ArrowDown') {
             nextIndex = (currentIndex + 1) % optionsCount;
           } else {
             nextIndex = (currentIndex - 1 + optionsCount) % optionsCount;
           }

           if (nextIndex < (ev.top_candidates?.length || 0)) {
             const cand = ev.top_candidates[nextIndex];
             handleBatchCorrection(cId, idx, cand.id, cand.pt);
           } else {
             handleBatchCorrection(cId, idx, batchManualInputs[cId]?.[idx]?.id || "REJECT", batchManualInputs[cId]?.[idx]?.pt || "Reject / Other");
           }
         }
      }

      if (ev.review_status === "Human Review") {
        if (e.key >= '1' && e.key <= '3') {
          const candIdx = parseInt(e.key) - 1;
          if (ev.top_candidates && ev.top_candidates[candIdx]) {
            const cand = ev.top_candidates[candIdx];
            handleBatchCorrection(cId, idx, cand.id, cand.pt);
          }
        } else if (e.key === '4') {
          handleBatchCorrection(cId, idx, batchManualInputs[cId]?.[idx]?.id || "REJECT", batchManualInputs[cId]?.[idx]?.pt || "Reject / Other");
        } else if (e.key === 'Enter') {
          e.preventDefault();
          if (!e.shiftKey && !batchCorrections[cId]?.[idx]) {
            if (ev.top_candidates && ev.top_candidates[0]) {
              handleBatchCorrection(cId, idx, ev.top_candidates[0].id, ev.top_candidates[0].pt);
            }
          }
          if (e.shiftKey) {
            let prevI = -1;
            for (let i = idx - 1; i >= 0; i--) {
              if (c.events[i].review_status === "Human Review") { prevI = i; break; }
            }
            if (prevI !== -1) {
              setExpandedEvents({ [`${cId}_${prevI}`]: true });
            } else {
              const currentCaseIdx = results.findIndex(x => x.case_id === cId);
              let foundPrev = false;
              for (let i = currentCaseIdx - 1; i >= 0; i--) {
                const prevCase = results[i];
                if (prevCase.error) continue;
                let prevReviewIdx = -1;
                if (prevCase.events) {
                  for (let k = prevCase.events.length - 1; k >= 0; k--) {
                    if (prevCase.events[k].review_status === "Human Review") { prevReviewIdx = k; break; }
                  }
                }
                if (prevReviewIdx !== -1) {
                  setExpandedCaseId(prevCase.case_id);
                  setExpandedEvents({ [`${prevCase.case_id}_${prevReviewIdx}`]: true });
                  foundPrev = true;
                  break;
                }
              }
            }
          } else {
            const nextI = c.events.findIndex((evt, i) => i > idx && evt.review_status === "Human Review" && !batchCorrections[cId]?.[i]);
            if (nextI !== -1) {
               setExpandedEvents({ [`${cId}_${nextI}`]: true });
            } else {
               const currentCaseIdx = results.findIndex(x => x.case_id === cId);
               let foundNext = false;
               for (let i = currentCaseIdx + 1; i < results.length; i++) {
                 const nextCase = results[i];
                 if (nextCase.error) continue;
                 const nextReviewIdx = nextCase.events?.findIndex((evt, k) => evt.review_status === "Human Review" && !batchCorrections[nextCase.case_id]?.[k]);
                 if (nextReviewIdx !== undefined && nextReviewIdx !== -1) {
                   setExpandedCaseId(nextCase.case_id);
                   setExpandedEvents({ [`${nextCase.case_id}_${nextReviewIdx}`]: true });
                   foundNext = true;
                   break;
                 }
               }
               if (!foundNext) {
                 setExpandedCaseId(null);
                 setExpandedEvents({});
               }
            }
          }
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [expandedEvents, results, batchManualInputs, batchCorrections]);

  // Auto-scroll to newly expanded event
  useEffect(() => {
    const expandedKey = Object.keys(expandedEvents).find(k => expandedEvents[k]);
    if (expandedKey) {
      const [cId, idx] = expandedKey.split('_');
      setTimeout(() => {
        document.getElementById(`event-${cId}-${idx}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 150);
    }
  }, [expandedEvents]);

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

  const handleBatchCorrection = (caseId, idx, newId, newPt) => {
    setBatchCorrections(prev => ({
      ...prev,
      [caseId]: {
        ...prev[caseId],
        [idx]: { id: newId, pt: newPt }
      }
    }))
    
    // Add to case history when manually interacted with
    if (window.addCaseToHistory && results) {
      const c = results.find(x => x.case_id === caseId);
      if (c) window.addCaseToHistory(c);
    }
  }

  const handleBatchManualInput = (caseId, eventIdx, field, value) => {
    setBatchManualInputs(prev => ({
      ...prev,
      [caseId]: { ...(prev[caseId] || {}), [eventIdx]: { ...(prev[caseId]?.[eventIdx] || {}), [field]: value } }
    }))
  }

  const toggleEventRow = (caseId, eventIdx) => {
    const key = `${caseId}_${eventIdx}`
    setExpandedEvents(prev => {
      if (prev[key]) return {}; // if already open, close it
      return { [key]: true }; // open this one and close everything else
    });
  }

  const startReviewQueue = () => {
    if (!results) return;
    for (let i = 0; i < results.length; i++) {
      const c = results[i];
      if (c.error) continue;
      const reviewIdx = c.events?.findIndex((e, k) => e.review_status === "Human Review" && !batchCorrections[c.case_id]?.[k]);
      if (reviewIdx !== undefined && reviewIdx !== -1) {
        setExpandedCaseId(c.case_id);
        setExpandedEvents({ [`${c.case_id}_${reviewIdx}`]: true });
        setFilter('Needs Review');
        return;
      }
    }
  };

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

      const client = await Client.connect(window.API_URL, { hf_token: window.HF_TOKEN || undefined })
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
            batchCorrections[caseObj.case_id]?.[idx] ? "Reviewed" : event.review_status
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
        meddra_pt_id: batchCorrections[c.case_id]?.[idx]?.id || ev.meddra_pt_id,
        review_status: batchCorrections[c.case_id]?.[idx] ? "Reviewed" : ev.review_status
      })) || [];
      return { ...c, events: newEvents }
    })
    try {
      const client = await Client.connect(window.API_URL, { hf_token: window.HF_TOKEN || undefined })
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
        meddra_pt_id: batchCorrections[c.case_id]?.[idx]?.id || ev.meddra_pt_id,
        review_status: batchCorrections[c.case_id]?.[idx] ? "Reviewed" : ev.review_status
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
      c.events.forEach((e, idx) => {
        totalEvents++;
        const isReviewed = !!batchCorrections[c.case_id]?.[idx];
        if (e.review_status === 'Auto-coded' || isReviewed) autoCodedEvents++;
        if (e.review_status === 'Human Review' && !isReviewed) needsReview = true;
        if (e.confidence_score) sumConfidence += e.confidence_score;

        const actualPt = batchCorrections[c.case_id]?.[idx]?.pt || e.meddra_pt;
        ptCounts[actualPt] = (ptCounts[actualPt] || 0) + 1;
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
            <div style={{ marginTop: '2rem', background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)' }}>
              <h4 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-primary)' }}><CircleDot size={16}/> PROCESSING BATCH</h4>
              {progress.total === 0 ? (
                <div style={{ color: 'var(--text-secondary)' }}>Reading and parsing cases...</div>
              ) : (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    <span>Processing case {progress.current} of {progress.total}</span>
                    <span>{Math.round((progress.current / progress.total) * 100)}%</span>
                  </div>
                  <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${(progress.current / progress.total) * 100}%`, background: 'var(--accent-primary)', transition: 'width 0.2s ease-out' }}></div>
                  </div>
                </>
              )}
            </div>
          )}
        </>
      ) : (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h2>Batch Dashboard</h2>
            <div style={{ display: 'flex', gap: '1rem' }}>
              {reviewRequiredCount > 0 && (
                <button className="btn btn-primary" onClick={startReviewQueue} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Play size={16} /> Start Review Queue ({reviewRequiredCount})
                </button>
              )}
              <button className="btn btn-secondary" onClick={() => setResults(null)}>New Batch Upload</button>
            </div>
          </div>

          {/* KPIs */}
          <div className="mobile-grid-2" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
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

          <div className="mobile-grid-1" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
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
          <div className="mobile-grid-1" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
            <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)' }}>
              <h4 style={{ marginBottom: '1.5rem' }}>Case Seriousness Breakdown</h4>
              <div style={{ height: '200px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Serious', value: seriousCount, fill: '#f59e0b' },
                        { name: 'Non-serious', value: totalProcessed - seriousCount - errorCount, fill: '#10b981' }
                      ]}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      <Cell key="cell-0" fill="#f59e0b" />
                      <Cell key="cell-1" fill="#10b981" />
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-sm)' }}
                      itemStyle={{ color: 'var(--text-primary)' }}
                    />
                    <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: '0.85rem' }}/>
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)' }}>
              <h4 style={{ marginBottom: '1.5rem' }}>Most Frequent MedDRA PTs</h4>
              <div style={{ height: '200px' }}>
                {topPTs.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      layout="vertical"
                      data={topPTs.map(([pt, count]) => ({ pt, count }))}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <XAxis type="number" hide />
                      <YAxis dataKey="pt" type="category" width={120} tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-sm)' }}
                        itemStyle={{ color: 'var(--accent-primary)' }}
                        cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                      />
                      <Bar dataKey="count" fill="var(--accent-primary)" radius={[0, 4, 4, 0]} barSize={20} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>No events coded.</div>
                )}
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
                          c.events?.some((e, k) => e.review_status === 'Human Review' && !batchCorrections[c.case_id]?.[k]) ?
                            <span style={{ color: 'var(--warning)' }}><AlertTriangle size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Needs Review</span> :
                            <span style={{ color: 'var(--success)' }}><CheckCircle size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> {c.events?.some(e => e.review_status === 'Human Review') ? 'Reviewed' : 'Auto-coded'}</span>
                        )}
                      </td>
                    </tr>
                    {expandedCaseId === c.case_id && (
                      <tr style={{ background: 'var(--bg-tertiary)' }}>
                        <td colSpan="5" style={{ padding: '2rem' }}>
                          {c.error ? (
                            <div style={{ background: 'var(--bg-primary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', borderLeft: '4px solid var(--warning)' }}>
                              <h4 style={{ color: 'var(--warning)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><XCircle size={18}/> Processing Error</h4>
                              <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>Reason:</p>
                              <p style={{ fontFamily: 'monospace', background: 'rgba(0,0,0,0.5)', padding: '1rem', borderRadius: '4px', color: '#f87171', overflowX: 'auto' }}>{c.error}</p>
                              <div style={{ marginTop: '1rem' }}>
                                <button className="btn btn-secondary" onClick={() => alert("Full Narrative:\n\n" + c.narrative)}>View Details (Narrative)</button>
                              </div>
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
                                      <tr id={`event-${c.case_id}-${idx}`} onClick={() => toggleEventRow(c.case_id, idx)} style={{ cursor: 'pointer', borderBottom: '1px solid var(--glass-border)', background: expandedEvents[`${c.case_id}_${idx}`] ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                                        <td style={{ padding: '1rem 0.5rem' }}>
                                          {expandedEvents[`${c.case_id}_${idx}`] ? <ChevronDown size={14} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> : <ChevronRight size={14} style={{ marginRight: '8px', verticalAlign: 'middle' }} />}
                                        </td>
                                        <td>{ev.effect_text}</td>
                                        <td>{batchCorrections[c.case_id]?.[idx]?.pt || ev.meddra_pt}</td>
                                        <td>{batchCorrections[c.case_id]?.[idx]?.id || ev.meddra_pt_id}</td>
                                        <td>{ev.suspected_drugs.map(d => typeof d === 'string' ? d : (d.canonical_name ? `${d.canonical_name} (${d.text})` : d.text)).join(', ') || 'None'}</td>
                                        <td>
                                          {batchCorrections[c.case_id]?.[idx] ?
                                            <span style={{ color: 'var(--success)' }}><CheckCircle size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Reviewed</span> :
                                            ev.review_status === 'Auto-coded' ?
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
                                                            <span style={{color: 'var(--text-secondary)'}}>[{candIdx + 1}]</span> {cand.pt} (ID: {cand.id}) - Score: {cand.score.toFixed(3)}
                                                          </label>
                                                        ))}
                                                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                                          <input
                                                            type="radio"
                                                            name={`review_${c.case_id}_${idx}`}
                                                            checked={batchCorrections[c.case_id]?.[idx]?.id === "REJECT" || (batchCorrections[c.case_id]?.[idx] && !ev.top_candidates?.find(x => x.id === batchCorrections[c.case_id]?.[idx].id))}
                                                            onChange={() => handleBatchCorrection(c.case_id, idx, batchManualInputs[c.case_id]?.[idx]?.id || "REJECT", batchManualInputs[c.case_id]?.[idx]?.pt || "Reject / Other")}
                                                          />
                                                          <span style={{color: 'var(--text-secondary)'}}>[4]</span> Reject / Manual Input
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
                                                          <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                                                            <span><kbd>Enter</kbd> to save</span>
                                                            <span><kbd>Shift</kbd>+<kbd>Enter</kbd> to go back</span>
                                                            <span><kbd>Esc</kbd> to close</span>
                                                            <span><kbd>↑</kbd> <kbd>↓</kbd> to change option</span>
                                                          </div>
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

                          <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                            <button className="btn btn-secondary" onClick={async () => {
                              try {
                                const client = await Client.connect(window.API_URL, { hf_token: window.HF_TOKEN || undefined });
                                const res = await client.predict('/export_pdf', [JSON.stringify(c)]);
                                const payload = res.data[0];
                                const bytes = Uint8Array.from(atob(payload), ch => ch.charCodeAt(0));
                                const blob = new Blob([bytes], { type: 'application/pdf' });
                                const url = window.URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = `PV-Coder_${c.case_id}_Report.pdf`;
                                document.body.appendChild(a);
                                a.click();
                                a.remove();
                              } catch (e) {
                                alert('Error generating PDF');
                                console.error(e);
                              }
                            }} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <Download size={16} /> Download PDF Report
                            </button>
                          </div>

                          <details style={{ marginTop: '2rem' }}>
                            <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)', padding: '0.5rem', userSelect: 'none' }}>
                              Show Technical / Debug View
                            </summary>
                            <TechnicalDebugView result={c} />
                          </details>
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



export default BatchUpload;
