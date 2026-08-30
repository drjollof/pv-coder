import React from 'react';
import { AlertTriangle, CheckCircle, Download, FileText } from 'lucide-react';

function ValidationExportPanel({ 
  validated, setValidated, handleExport, 
  filteredEvents, reviewEventsCount, correctionsCount,
  demographics, isSeriousCase, caseSeriousnessReason, extractedDrugs
}) {

  const hasDemographics = demographics && (demographics.age !== null || demographics.gender !== null || demographics.weight !== null);
  const hasEvent = filteredEvents.length > 0;
  const hasDrug = extractedDrugs?.length > 0 || filteredEvents.some(e => e.suspected_drugs?.length > 0);
  const allCoded = reviewEventsCount === 0 || correctionsCount === reviewEventsCount;
  const seriousReasonOk = !isSeriousCase || (isSeriousCase && !!caseSeriousnessReason);

  const canValidate = hasEvent && hasDrug && allCoded && seriousReasonOk;

  return (
    <>
      {/* CASE VALIDATION */}
      {!validated && (
        <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)', marginBottom: '2rem' }}>
          <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            E2B(R3) Pre-Flight Checks
          </h3>
          <ul style={{ listStyleType: 'none', padding: 0, margin: '0 0 1.5rem 0', lineHeight: '2' }}>
            <li>
              {hasDemographics ? 
                <CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> : 
                <AlertTriangle size={16} style={{ color: 'var(--warning)', verticalAlign: 'middle', marginRight: '8px' }} />}
              <strong style={{ color: hasDemographics ? 'inherit' : 'var(--warning)' }}>Patient Identifiers:</strong> At least one demographic (Age, Gender, Weight) {hasDemographics ? 'present' : 'missing (NullFlavor will be applied)'}
            </li>
            
            <li>
              {hasDrug ? 
                <CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> : 
                <AlertTriangle size={16} style={{ color: '#f43f5e', verticalAlign: 'middle', marginRight: '8px' }} />}
              <strong style={{ color: hasDrug ? 'inherit' : '#f43f5e' }}>Reporter Criteria:</strong> At least one Suspected Drug {hasDrug ? 'identified' : 'missing'}
            </li>

            <li>
              {hasEvent ? 
                <CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> : 
                <AlertTriangle size={16} style={{ color: '#f43f5e', verticalAlign: 'middle', marginRight: '8px' }} />}
              <strong style={{ color: hasEvent ? 'inherit' : '#f43f5e' }}>Event Criteria:</strong> At least one Adverse Event {hasEvent ? 'identified' : 'missing'}
            </li>

            <li>
              {allCoded ? 
                <CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> : 
                <AlertTriangle size={16} style={{ color: '#f43f5e', verticalAlign: 'middle', marginRight: '8px' }} />}
              <strong style={{ color: allCoded ? 'inherit' : '#f43f5e' }}>Coding Completeness:</strong> All events mapped to MedDRA PT {allCoded ? '' : '(Pending Human Review)'}
            </li>

            <li>
              {seriousReasonOk ? 
                <CheckCircle size={16} style={{ color: 'var(--success)', verticalAlign: 'middle', marginRight: '8px' }} /> : 
                <AlertTriangle size={16} style={{ color: '#f43f5e', verticalAlign: 'middle', marginRight: '8px' }} />}
              <strong style={{ color: seriousReasonOk ? 'inherit' : '#f43f5e' }}>Seriousness Criteria:</strong> {isSeriousCase ? 'Case is Serious and Reason is provided' : 'Case is Non-Serious or adequately assessed'}
            </li>
          </ul>

          {!canValidate && (
            <p style={{ color: '#f43f5e', fontSize: '0.9rem', marginBottom: '1rem' }}>
              Cannot validate case: Please resolve the red errors above.
            </p>
          )}

          <button
            className="btn btn-primary"
            disabled={!canValidate}
            onClick={() => setValidated(true)}
          >
            Validate Case & Lock
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
