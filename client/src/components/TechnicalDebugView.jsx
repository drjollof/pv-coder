import React, { useState } from 'react';

export default function TechnicalDebugView({ result }) {
  const [showJson, setShowJson] = useState(false);

  if (!result) return null;

  return (
    <div style={{ 
      padding: '1.5rem', 
      background: 'var(--bg-secondary)', 
      borderRadius: '12px', 
      fontFamily: 'Inter, system-ui, sans-serif',
      border: '1px solid var(--glass-border)',
      color: 'var(--text-primary)',
      boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid var(--glass-border)' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: 'var(--accent-purple)' }}>⚙</span> Technical Diagnostics
        </h3>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* 1. Pipeline Timing */}
        {result.pipeline_timings && (
          <div style={{ background: 'var(--bg-tertiary)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--glass-border)' }}>
            <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem', marginTop: 0 }}>Processing Time</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {Object.entries(result.pipeline_timings).map(([stage, time]) => (
                <div key={stage} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  paddingBottom: '0.5rem', 
                  borderBottom: stage === 'Total' ? 'none' : '1px dashed var(--glass-border)',
                  fontWeight: stage === 'Total' ? '700' : '400',
                  color: stage === 'Total' ? 'var(--accent-purple)' : 'var(--text-primary)',
                  fontSize: '0.9rem'
                }}>
                  <span>{stage}</span>
                  <span style={{ fontFamily: 'monospace' }}>{time.toFixed(3)}s</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 2. NER & Context */}
        <div style={{ background: 'var(--bg-tertiary)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--glass-border)' }}>
          <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem', marginTop: 0 }}>Extraction Summary</h4>
          
          <div style={{ marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Extracted Events ({result.events?.length || 0})</span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
              {result.events?.map((e, i) => (
                <span key={i} style={{ 
                  background: e.is_serious ? 'rgba(239, 68, 68, 0.1)' : 'rgba(59, 130, 246, 0.1)', 
                  color: e.is_serious ? 'var(--error-red)' : 'var(--accent-blue)',
                  padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', border: `1px solid ${e.is_serious ? 'rgba(239, 68, 68, 0.2)' : 'rgba(59, 130, 246, 0.2)'}`
                }}>
                  {e.effect_text}
                </span>
              ))}
            </div>
          </div>

          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Excluded Contexts ({result.excluded_findings?.length || 0})</span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
              {result.excluded_findings?.map((x, i) => (
                <span key={i} style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', border: '1px solid var(--glass-border)', textDecoration: 'line-through' }}>
                  {x.text}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 3. Normalization Candidates */}
      <div style={{ background: 'var(--bg-tertiary)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--glass-border)', marginBottom: '1.5rem' }}>
        <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem', marginTop: 0 }}>Top Normalization Candidates</h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {result.events?.map((e, i) => (
            <div key={i} style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ marginBottom: '0.75rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Target:</span> 
                <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{e.effect_text}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)', paddingBottom: '0.5rem', borderBottom: '1px solid var(--glass-border)' }}>
                <div>MedDRA PT</div>
                <div>Code</div>
                <div style={{ textAlign: 'right' }}>Confidence</div>
              </div>
              {e.top_candidates?.map((c, j) => (
                <div key={j} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '0.5rem', fontSize: '0.85rem', padding: '0.5rem 0', borderBottom: j < e.top_candidates.length - 1 ? '1px dashed rgba(255,255,255,0.05)' : 'none', color: j === 0 ? 'var(--success-green)' : 'var(--text-primary)' }}>
                  <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.pt}</div>
                  <div style={{ fontFamily: 'monospace' }}>{c.id}</div>
                  <div style={{ textAlign: 'right', fontFamily: 'monospace' }}>{(c.score * 100).toFixed(1)}%</div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* 4. Raw JSON */}
      <div style={{ background: 'var(--bg-tertiary)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--glass-border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>Raw Case Payload</h4>
          <button onClick={() => setShowJson(!showJson)} style={{ background: 'none', border: '1px solid var(--glass-border)', color: 'var(--text-primary)', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem', transition: 'all 0.2s' }}>
            {showJson ? 'Hide JSON' : 'View JSON'}
          </button>
        </div>
        {showJson && (
          <div style={{ marginTop: '1rem', background: '#0d1117', padding: '1rem', borderRadius: '6px', maxHeight: '400px', overflowY: 'auto', overflowX: 'auto', border: '1px solid rgba(255,255,255,0.1)' }}>
            <pre style={{ margin: 0, color: '#c9d1d9', fontSize: '0.8rem', fontFamily: 'monospace', lineHeight: '1.5' }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>

    </div>
  );
}
