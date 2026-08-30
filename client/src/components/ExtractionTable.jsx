import React from 'react';
import { AlertTriangle, CheckCircle, ChevronDown, ChevronRight, Info, Plus, XCircle } from 'lucide-react';

function ExtractionTable({
  result, setResult, corrections, setCorrections, manualInputs, setManualInputs,
  expandedRows, setExpandedRows, validated, showAddEvent, setShowAddEvent, newEvent, setNewEvent
}) {

  const toggleRow = (idx) => {
    setExpandedRows(prev => ({ ...prev, [idx]: !prev[idx] }));
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

  const handleAddEvent = () => {
    if (!newEvent.effect.trim()) {
      alert("Please enter the Raw Effect text.");
      return;
    }
    
    const addedEvent = {
      effect_text: newEvent.effect,
      start_char: 0,
      end_char: 0,
      meddra_pt: newEvent.pt || newEvent.effect,
      meddra_pt_id: newEvent.id || "Unknown",
      confidence_score: 1.0,
      review_status: "Manually Added",
      top_candidates: [],
      suspected_drugs: [],
      is_serious: false,
      seriousness_reason: null,
      seriousness_evidence: null,
      is_speculated: false
    };

    setResult(prev => ({
      ...prev,
      events: [...prev.events, addedEvent]
    }));
    
    setNewEvent({ effect: '', pt: '', id: '' });
    setShowAddEvent(false);
  };

  return (
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
              <tr onClick={() => toggleRow(i)} style={{ cursor: 'pointer', borderBottom: '1px solid var(--glass-border)', background: expandedRows[i] ? 'rgba(255,255,255,0.02)' : 'transparent', opacity: corrections[i]?.id === 'EXCLUDED' ? 0.5 : 1 }}>
                <td style={{ padding: '1rem 0.5rem', textDecoration: corrections[i]?.id === 'EXCLUDED' ? 'line-through' : 'none' }}>
                  {expandedRows[i] ? <ChevronDown size={14} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> : <ChevronRight size={14} style={{ marginRight: '8px', verticalAlign: 'middle' }} />}
                  {ev.effect_text}
                </td>
                <td style={{ padding: '1rem 0.5rem' }}>
                  {corrections[i]?.id === 'EXCLUDED' ?
                    <span style={{ color: 'var(--text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><XCircle size={14} /> Excluded</span> :
                    ev.review_status === 'Auto-coded' ?
                    <span style={{ color: 'var(--success)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><CheckCircle size={14} /> Auto-coded</span> :
                    ev.review_status === 'Manually Added' ?
                    <span style={{ color: 'var(--accent-primary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><Plus size={14} /> Manual</span> :
                    <span style={{ color: 'var(--warning)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><AlertTriangle size={14} /> Review</span>}
                </td>
                <td style={{ padding: '1rem 0.5rem', textDecoration: corrections[i]?.id === 'EXCLUDED' ? 'line-through' : 'none' }}>{corrections[i]?.pt || ev.meddra_pt}</td>
                <td style={{ padding: '1rem 0.5rem', textDecoration: corrections[i]?.id === 'EXCLUDED' ? 'line-through' : 'none' }}>{corrections[i]?.id || ev.meddra_pt_id}</td>
                <td style={{ padding: '1rem 0.5rem', textDecoration: corrections[i]?.id === 'EXCLUDED' ? 'line-through' : 'none' }}>
                  {ev.suspected_drugs.length > 0 ? 
                    ev.suspected_drugs.map(d => typeof d === 'string' ? d : (d.canonical_name || d.text)).join(', ') 
                    : 'None'}
                </td>
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
                                      name={"review_" + i}
                                      checked={corrections[i]?.id === cand.id || (!corrections[i] && idx === 0)}
                                      onChange={() => handleCorrection(i, cand.id, cand.pt)}
                                    />
                                    <span style={{color: 'var(--text-secondary)'}}>[{idx + 1}]</span> {cand.pt} (ID: {cand.id}) - Score: {cand.score.toFixed(3)}
                                  </label>
                                ))}
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                  <input
                                    type="radio"
                                    name={"review_" + i}
                                    checked={corrections[i]?.id === "REJECT" || (corrections[i] && !ev.top_candidates.find(c => c.id === corrections[i].id) && corrections[i]?.id !== "EXCLUDED")}
                                    onChange={() => handleCorrection(i, manualInputs[i]?.id || "REJECT", manualInputs[i]?.pt || "Reject / Other")}
                                  />
                                  <span style={{color: 'var(--text-secondary)'}}>[4]</span> Reject / Manual Input
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                  <input
                                    type="radio"
                                    name={"review_" + i}
                                    checked={corrections[i]?.id === "EXCLUDED"}
                                    onChange={() => handleCorrection(i, "EXCLUDED", "Excluded from case")}
                                  />
                                  <span style={{color: 'var(--text-secondary)'}}>[5]</span> Exclude Event (False Positive)
                                </label>

                                {(corrections[i]?.id === "REJECT" || (corrections[i] && !ev.top_candidates.find(c => c.id === corrections[i].id) && corrections[i]?.id !== "EXCLUDED")) && (
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
                                <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', gap: '1rem' }}>
                                  <span><kbd>Enter</kbd> to save</span>
                                  <span><kbd>Esc</kbd> to close</span>
                                  <span><kbd>↑</kbd> <kbd>↓</kbd> to navigate</span>
                                </div>
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
                              
                              {!validated && (
                                <div style={{ marginTop: '1rem', borderTop: '1px solid var(--glass-border)', paddingTop: '1rem' }}>
                                  {corrections[i]?.id === "EXCLUDED" ? (
                                    <button className="btn btn-secondary" onClick={() => {
                                      setCorrections(prev => {
                                        const next = {...prev};
                                        delete next[i];
                                        return next;
                                      });
                                    }} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', color: 'var(--text-primary)', borderColor: 'var(--glass-border)' }}>
                                      <CheckCircle size={14} /> Restore Event
                                    </button>
                                  ) : (
                                    <button className="btn btn-secondary" onClick={() => handleCorrection(i, "EXCLUDED", "Excluded from case")} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', color: 'var(--warning)', borderColor: 'rgba(245, 158, 11, 0.3)' }}>
                                      <XCircle size={14} /> Exclude Event (False Positive)
                                    </button>
                                  )}
                                </div>
                              )}
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
      
      <div style={{ marginTop: '1rem', borderTop: '1px dashed var(--glass-border)', paddingTop: '1rem' }}>
        {!showAddEvent ? (
          <button className="btn btn-secondary" onClick={() => setShowAddEvent(true)} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
            <Plus size={14} /> Add Missing Event
          </button>
        ) : (
          <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)', display: 'flex', gap: '1rem', alignItems: 'flex-end', animation: 'slideIn 0.2s ease-out' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>Effect (Raw Text)</label>
              <input type="text" style={{ width: '100%', padding: '0.6rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }} placeholder="e.g. squamous cell carcinoma" value={newEvent.effect} onChange={e => setNewEvent({...newEvent, effect: e.target.value})} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>MedDRA PT</label>
              <input type="text" style={{ width: '100%', padding: '0.6rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }} placeholder="e.g. Squamous cell carcinoma" value={newEvent.pt} onChange={e => setNewEvent({...newEvent, pt: e.target.value})} />
            </div>
            <div style={{ width: '150px' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>MedDRA ID</label>
              <input type="text" style={{ width: '100%', padding: '0.6rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }} placeholder="ID" value={newEvent.id} onChange={e => setNewEvent({...newEvent, id: e.target.value})} />
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button className="btn btn-primary" onClick={handleAddEvent}>Add</button>
              <button className="btn btn-secondary" onClick={() => setShowAddEvent(false)}>Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ExtractionTable;
