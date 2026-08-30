import React from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

function MedicationsPanel({ drugs, showMedications, setShowMedications }) {
  if (!drugs || drugs.length === 0) return null;

  return (
    <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', border: '1px solid var(--glass-border)' }}>
      <button 
        onClick={() => setShowMedications(!showMedications)}
        style={{ 
          background: 'none', 
          border: 'none', 
          color: 'var(--text-primary)', 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.5rem', 
          cursor: 'pointer', 
          padding: 0, 
          fontSize: '1rem', 
          fontWeight: 'bold',
          width: '100%',
          justifyContent: 'space-between'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {showMedications ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          Medications & Regimens ({drugs.length})
        </div>
      </button>
      
      {showMedications && (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', marginTop: '1rem', animation: 'slideIn 0.2s ease-out' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--glass-border)', color: 'var(--text-secondary)', textAlign: 'left' }}>
              <th style={{ padding: '0.5rem' }}>Drug Name</th>
              <th style={{ padding: '0.5rem' }}>Dose</th>
              <th style={{ padding: '0.5rem' }}>Frequency</th>
              <th style={{ padding: '0.5rem' }}>Route</th>
            </tr>
          </thead>
          <tbody>
            {drugs.map((drug, i) => (
              <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.75rem 0.5rem' }}>
                  {drug.canonical_name ? (
                    <>
                      <strong>{drug.canonical_name}</strong>
                      <span style={{ color: 'var(--text-secondary)', marginLeft: '0.5rem', fontSize: '0.8rem' }}>({drug.text})</span>
                    </>
                  ) : (
                    <strong>{drug.text}</strong>
                  )}
                </td>
                <td style={{ padding: '0.75rem 0.5rem' }}>{drug.dose || <span style={{ color: 'var(--text-secondary)', opacity: 0.5 }}>-</span>}</td>
                <td style={{ padding: '0.75rem 0.5rem' }}>{drug.frequency || <span style={{ color: 'var(--text-secondary)', opacity: 0.5 }}>-</span>}</td>
                <td style={{ padding: '0.75rem 0.5rem' }}>{drug.route || <span style={{ color: 'var(--text-secondary)', opacity: 0.5 }}>-</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default MedicationsPanel;
