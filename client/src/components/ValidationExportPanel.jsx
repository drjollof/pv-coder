import React from 'react';
import { AlertTriangle, CheckCircle, Download, FileText } from 'lucide-react';

function ValidationExportPanel({ validated, setValidated, handleExport, filteredEvents, reviewEventsCount, correctionsCount }) {
  return (
    <>
      {/* CASE VALIDATION */}
      {!validated && (
        <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)', marginBottom: '2rem' }}>
          <h3 style={{ marginBottom: '1rem' }}>CASE VALIDATION</h3>
          <ul style={{ listStyleType: 'none', padding: 0, margin: '0 0 1.5rem 0', lineHeight: '1.8' }}>
            <li><CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> Clinical narrative present</li>
            <li>{filteredEvents.length > 0 ? <CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> : <AlertTriangle size={16} style={{ color: 'var(--warning)', verticalAlign: 'middle', marginRight: '8px' }} />} Adverse event identified</li>
            <li>{filteredEvents.some(e => e.suspected_drugs.length > 0) ? <CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> : <AlertTriangle size={16} style={{ color: 'var(--warning)', verticalAlign: 'middle', marginRight: '8px' }} />} Suspected drug identified</li>
            <li><CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> Seriousness assessed</li>
            {reviewEventsCount > 0 && (
              <li>
                {correctionsCount === reviewEventsCount ?
                  <CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> :
                  <span style={{ display: 'inline-block', width: '16px', height: '16px', border: '2px solid var(--warning)', borderRadius: '50%', verticalAlign: 'middle', marginRight: '8px' }}></span>}
                Reviewer confirmation required
              </li>
            )}
          </ul>

          {filteredEvents.length === 0 && (
            <p style={{ color: 'var(--warning)', fontSize: '0.9rem', marginBottom: '1rem' }}>Cannot validate case: No adverse events were identified.</p>
          )}

          <button
            className="btn btn-primary"
            disabled={filteredEvents.length === 0 || (reviewEventsCount > 0 && correctionsCount < reviewEventsCount)}
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
                <FileText size={16} /> PDF Report
              </button>
            </div>
            <div>
              <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Data Science</h4>
              <button className="btn btn-secondary" style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }} onClick={() => handleExport('json')}>
                <Download size={16} /> Raw JSON
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default ValidationExportPanel;
