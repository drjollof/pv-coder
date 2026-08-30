import React from 'react';
import { AlertTriangle, CheckCircle } from 'lucide-react';

function CaseOverviewPanel({ result, reviewEventsCount }) {
  return (
    <div className="mobile-grid-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '1rem', background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', marginBottom: '2rem', border: '1px solid var(--glass-border)' }}>
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
        <div style={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.25rem', color: reviewEventsCount > 0 ? 'var(--warning)' : 'var(--success)' }}>
          {reviewEventsCount > 0 ? <><AlertTriangle size={16} /> Review Required</> : <><CheckCircle size={16} /> Auto-coded</>}
        </div>
      </div>
      <div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Events Detected</div>
        <div style={{ fontWeight: 'bold' }}>{result.events.length}</div>
      </div>
      <div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Auto-coded</div>
        <div style={{ fontWeight: 'bold' }}>{result.events.length - reviewEventsCount}</div>
      </div>

      {/* Extended Seriousness Evidence */}
      {result.is_serious_case && result.case_seriousness_evidence && (
        <div style={{ gridColumn: '1 / -1', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--glass-border)', fontSize: '0.9rem' }}>
          <span style={{ color: 'var(--warning)' }}>Basis for Seriousness:</span>
          <em style={{ marginLeft: '0.5rem', color: 'var(--text-primary)' }}>"{result.case_seriousness_evidence}"</em>
        </div>
      )}
    </div>
  );
}

export default CaseOverviewPanel;
