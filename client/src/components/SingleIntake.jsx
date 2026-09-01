import React, { useState, useEffect } from 'react';
import { Circle, CircleDot, CheckCircle } from 'lucide-react';
import { Client } from "@gradio/client";
import HighlightedText from './HighlightedText';

import CaseOverviewPanel from './CaseOverviewPanel';
import DemographicsPanel from './DemographicsPanel';
import MedicationsPanel from './MedicationsPanel';
import ExtractionTable from './ExtractionTable';
import ValidationExportPanel from './ValidationExportPanel';
import IntakeForm from './IntakeForm';
import TechnicalDebugView from './TechnicalDebugView';

function SingleIntake() {
  const [narrative, setNarrative] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [showJson, setShowJson] = useState(false);
  const [corrections, setCorrections] = useState({});
  const [manualInputs, setManualInputs] = useState({});
  const [validated, setValidated] = useState(false);
  const [expandedRows, setExpandedRows] = useState({});
  const [showTechView, setShowTechView] = useState(false);
  const [showMedications, setShowMedications] = useState(false);
  const [showAddEvent, setShowAddEvent] = useState(false);
  const [newEvent, setNewEvent] = useState({ effect: '', pt: '', id: '' });
  const [examples, setExamples] = useState([]);
  const [previousCaseJson, setPreviousCaseJson] = useState(null);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      
      const expandedIdxStr = Object.keys(expandedRows).find(k => expandedRows[k]);
      if (!expandedIdxStr) return;
      
      const i = parseInt(expandedIdxStr);
      const ev = result?.events[i];
      if (!ev) return;

      const reviewableIndices = result?.events.map((evt, idx) => evt.review_status === "Human Review" ? idx : -1).filter(idx => idx !== -1) || [];
      const currentIdxInReviewable = reviewableIndices.indexOf(i);

      if (e.key === 'Escape') {
        setExpandedRows(prev => ({...prev, [i]: false}));
        return;
      }

      if (e.key === 'ArrowDown') {
         e.preventDefault();
         if (currentIdxInReviewable !== -1 && currentIdxInReviewable < reviewableIndices.length - 1) {
             const nextI = reviewableIndices[currentIdxInReviewable + 1];
             setExpandedRows({ [nextI]: true });
         } else if (i < result.events.length - 1) {
             setExpandedRows({ [i+1]: true });
         }
      }
      
      if (e.key === 'ArrowUp') {
         e.preventDefault();
         if (currentIdxInReviewable > 0) {
             const prevI = reviewableIndices[currentIdxInReviewable - 1];
             setExpandedRows({ [prevI]: true });
         } else if (i > 0) {
             setExpandedRows({ [i-1]: true });
         }
      }

      if (ev.review_status === "Human Review" && !validated) {
        const handleCorrection = (eventIdx, selectedId, selectedPt) => {
          setCorrections(prev => ({ ...prev, [eventIdx]: { pt: selectedPt, id: selectedId } }));
        };

        if (e.key >= '1' && e.key <= '3') {
          const candIdx = parseInt(e.key) - 1;
          if (ev.top_candidates && ev.top_candidates[candIdx]) {
            const cand = ev.top_candidates[candIdx];
            handleCorrection(i, cand.id, cand.pt);
          }
        } else if (e.key === '4') {
          handleCorrection(i, manualInputs[i]?.id || "REJECT", manualInputs[i]?.pt || "Reject / Other");
        } else if (e.key === '5') {
          handleCorrection(i, "EXCLUDED", "Excluded from case");
        } else if (e.key === 'Enter') {
          setExpandedRows(prev => ({...prev, [i]: false}));
          if (currentIdxInReviewable !== -1 && currentIdxInReviewable < reviewableIndices.length - 1) {
             const nextI = reviewableIndices[currentIdxInReviewable + 1];
             setExpandedRows(prev => ({...prev, [nextI]: true}));
          }
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [expandedRows, result, validated, manualInputs]);

  useEffect(() => {
    async function loadExamples() {
      try {
        const client = await Client.connect(window.API_URL, { hf_token: window.HF_TOKEN || undefined });
        const res = await client.predict("/examples");
        setExamples(JSON.parse(res.data[0]));
      } catch (err) {
        console.error("Could not load examples:", err);
      }
    }
    loadExamples();
  }, []);

  const resetCase = () => {
    setNarrative('');
    setResult(null);
    setCorrections({});
    setManualInputs({});
    setValidated(false);
    setExpandedRows({});
    setError('');
    setPreviousCaseJson(null);
  };

  const handleAnalyze = async () => {
    if (!narrative.trim()) return;

    setLoading(true);
    setError('');
    setResult(null);
    setCorrections({});
    setValidated(false);
    setExpandedRows({});
    setShowJson(false);

    try {
      const client = await Client.connect(window.API_URL, { hf_token: window.HF_TOKEN || undefined });
      const res = await client.predict("/analyze", [
        narrative,
        'WEB-' + Math.floor(Math.random() * 1000),
        previousCaseJson || ''
      ]);
      const data = JSON.parse(res.data[0]);
      if (data.error) {
        console.error("Backend Exception:", data.traceback);
        setError("Backend Error: " + data.error + "\n\n" + data.traceback);
        return;
      }

      const autoExpand = {};
      data.events?.forEach((ev, i) => {
        if (ev.review_status === "Human Review") autoExpand[i] = true;
      });
      setExpandedRows(autoExpand);

      setResult(data);
      if (window.addCaseToHistory) {
        window.addCaseToHistory(data);
      }
    } catch (err) {
      console.error("Analysis Error:", err);
      setError("API Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getFilteredResult = () => {
    if (!result) return null;
    const finalEvents = result.events.map((ev, i) => {
      if (corrections[i]) {
        return { ...ev, meddra_pt: corrections[i].pt, meddra_pt_id: corrections[i].id };
      }
      return ev;
    }).filter(ev => ev.meddra_pt_id !== 'EXCLUDED' && ev.meddra_pt_id !== 'REJECT');
    return { ...result, events: finalEvents };
  };

  const handleExport = async (format) => {
    const exportResult = getFilteredResult();
    
    if (format === 'json') {
      const blob = new Blob([JSON.stringify(exportResult, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `PV-Coder_${exportResult.case_id}_Report.json`;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(url);
      return;
    }
    try {
      const client = await Client.connect(window.API_URL, { hf_token: window.HF_TOKEN || undefined });
      const endpoint = format === 'pdf' ? '/export_pdf' : '/export_xml';
      const res = await client.predict(endpoint, [JSON.stringify(exportResult)]);
      const payload = res.data[0];

      let blob;
      if (format === 'pdf') {
        const bytes = Uint8Array.from(atob(payload), c => c.charCodeAt(0));
        blob = new Blob([bytes], { type: 'application/pdf' });
      } else {
        blob = new Blob([payload], { type: 'application/xml' });
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `PV-Coder_${result.case_id}_Report.${format}`;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("Error generating " + format.toUpperCase());
    }
  };

  const reviewEvents = result?.events?.filter(e => e.review_status === "Human Review") || [];

  const getWorkflowState = () => {
    if (!result && !loading) return 0;
    if (loading) return 1;
    if (result && reviewEvents.length > 0 && Object.keys(corrections).length < reviewEvents.length) return 2;
    if (result && !validated) return 3;
    if (result && validated) return 4;
    return 0;
  };
  const currentStep = getWorkflowState();
  const workflowSteps = ['Intake', 'Extraction', 'Review', 'Validation', 'Export'];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.2rem', color: 'var(--text-secondary)' }}>
          {result ? `Case ${result.case_id} (v${result.case_version || 1})` : 'New Case'}
        </h2>
        <button className="btn btn-secondary" onClick={resetCase}>New Case / Reset</button>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginBottom: '2rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
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
        <IntakeForm 
          narrative={narrative} 
          setNarrative={setNarrative}
          previousCaseJson={previousCaseJson}
          setPreviousCaseJson={setPreviousCaseJson}
          handleAnalyze={handleAnalyze} 
          examples={examples} 
          loading={loading} 
        />
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
          
          <DemographicsPanel demographics={result.demographics} />
          
          <MedicationsPanel 
            drugs={result.extracted_drugs} 
            showMedications={showMedications} 
            setShowMedications={setShowMedications} 
          />
          
          <CaseOverviewPanel 
            result={result} 
            reviewEventsCount={reviewEvents.length} 
          />

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
                events={getFilteredResult()?.events || result.events}
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

          <ExtractionTable 
            result={result}
            setResult={setResult}
            corrections={corrections}
            setCorrections={setCorrections}
            manualInputs={manualInputs}
            setManualInputs={setManualInputs}
            expandedRows={expandedRows}
            setExpandedRows={setExpandedRows}
            validated={validated}
            showAddEvent={showAddEvent}
            setShowAddEvent={setShowAddEvent}
            newEvent={newEvent}
            setNewEvent={setNewEvent}
          />

          <ValidationExportPanel 
            validated={validated}
            setValidated={setValidated}
            handleExport={handleExport}
            filteredEvents={getFilteredResult().events}
            reviewEventsCount={reviewEvents.length}
            correctionsCount={Object.keys(corrections).length}
            demographics={result.demographics}
            isSeriousCase={result.is_serious_case}
            caseSeriousnessReason={result.case_seriousness_reason}
            extractedDrugs={result.extracted_drugs}
          />

          {/* Technical / Debug View */}
          <details style={{ marginTop: '2rem' }}>
            <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)', padding: '0.5rem', userSelect: 'none' }}>
              Show Technical / Debug View
            </summary>
            <TechnicalDebugView result={getFilteredResult()} />
          </details>

        </div>
      )}
    </div>
  );
}

export default SingleIntake;
