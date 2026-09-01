import React from 'react';

export default function TechnicalDebugView({ result }) {
  if (!result) return null;

  return (
    <div style={{ padding: '1rem', background: 'var(--bg-tertiary)', borderRadius: '8px', overflowX: 'auto', fontFamily: 'monospace', fontSize: '0.85rem', border: '1px solid var(--glass-border)', color: 'var(--text-primary)' }}>
      <h3 style={{ color: 'var(--text-primary)', marginBottom: '1rem', fontSize: '1rem', borderBottom: '1px solid var(--glass-border)', paddingBottom: '0.5rem' }}>Technical Details</h3>
      
      {/* 1. Pipeline Timing */}
      {result.pipeline_timings && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ color: 'var(--accent-purple)', marginBottom: '0.5rem' }}>PROCESSING TIME</h4>
          <table style={{ width: '100%', maxWidth: '300px', borderCollapse: 'collapse' }}>
            <tbody>
              {Object.entries(result.pipeline_timings).map(([stage, time]) => (
                <tr key={stage} style={{ borderBottom: stage === 'Total' ? 'none' : '1px solid var(--glass-border)' }}>
                  <td style={{ padding: '4px 0', fontWeight: stage === 'Total' ? 'bold' : 'normal' }}>{stage}</td>
                  <td style={{ padding: '4px 0', textAlign: 'right', fontWeight: stage === 'Total' ? 'bold' : 'normal' }}>{time} s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 2. NER Entities & Context Modifiers */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h4 style={{ color: 'var(--accent-purple)', marginBottom: '0.5rem' }}>NER & CONTEXT</h4>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div>
            <strong>Extracted Events:</strong>
            <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem', color: 'var(--text-secondary)' }}>
              {result.events?.map((e, i) => (
                <li key={i}>{e.effect_text} {e.is_serious ? <span style={{color: 'var(--error-red)'}}>(Serious)</span> : ''}</li>
              ))}
            </ul>
          </div>
          <div>
            <strong>Excluded/Modified Contexts:</strong>
            <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem', color: 'var(--text-secondary)' }}>
              {result.excluded_findings?.map((x, i) => (
                <li key={i} style={{ textDecoration: 'line-through' }}>{x.text} ({x.reason})</li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* 3. Normalization Candidates */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h4 style={{ color: 'var(--accent-purple)', marginBottom: '0.5rem' }}>NORMALIZATION CANDIDATES</h4>
        {result.events?.map((e, i) => (
          <div key={i} style={{ marginBottom: '1rem', padding: '0.5rem', background: 'rgba(0,0,0,0.1)', borderRadius: '4px' }}>
            <div style={{ marginBottom: '0.5rem' }}><strong>Target:</strong> {e.effect_text}</div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ color: 'var(--text-secondary)', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }}>
                  <th style={{ padding: '4px' }}>MedDRA PT</th>
                  <th style={{ padding: '4px' }}>ID</th>
                  <th style={{ padding: '4px' }}>Score</th>
                </tr>
              </thead>
              <tbody>
                {e.top_candidates?.map((c, j) => (
                  <tr key={j}>
                    <td style={{ padding: '4px', color: j === 0 ? 'var(--success-green)' : 'inherit' }}>{c.pt}</td>
                    <td style={{ padding: '4px' }}>{c.id}</td>
                    <td style={{ padding: '4px' }}>{(c.score * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>

      {/* 4. Raw JSON */}
      <div>
        <h4 style={{ color: 'var(--accent-purple)', marginBottom: '0.5rem' }}>RAW E2B-STYLE JSON</h4>
        <pre style={{ margin: 0, padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', overflowX: 'auto' }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      </div>

    </div>
  );
}
