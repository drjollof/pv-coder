import React from 'react';

function DemographicsPanel({ demographics }) {
  return (
    <div className="mobile-stack" style={{ display: 'flex', gap: '3rem', background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', border: '1px solid var(--glass-border)' }}>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Patient Age</span>
        <span style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{demographics?.age || <span style={{ color: 'var(--text-secondary)', fontWeight: 'normal' }}>Not specified</span>}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Gender</span>
        <span style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{demographics?.gender || <span style={{ color: 'var(--text-secondary)', fontWeight: 'normal' }}>Not specified</span>}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Weight</span>
        <span style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{demographics?.weight || <span style={{ color: 'var(--text-secondary)', fontWeight: 'normal' }}>Not specified</span>}</span>
      </div>
    </div>
  );
}

export default DemographicsPanel;
