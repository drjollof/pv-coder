import React from 'react';

function IntakeForm({ narrative, setNarrative, handleAnalyze, examples, loading }) {
  return (
    <div style={{ marginBottom: '1.5rem', animation: 'slideIn 0.3s ease-out' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <h3>Clinical Narrative</h3>
        {examples && examples.length > 0 && (
          <select
            className="select-dropdown"
            onChange={(e) => {
              if (e.target.value !== "") setNarrative(examples[parseInt(e.target.value)])
            }}
          >
            <option value="">Load an example case...</option>
            {examples.map((ex, i) => (
              <option key={i} value={i}>Clinical Case #{i + 1}</option>
            ))}
          </select>
        )}
      </div>
      <textarea
        className="textarea"
        placeholder="Paste unstructured clinical text here..."
        value={narrative}
        onChange={(e) => setNarrative(e.target.value)}
      />
      <button
        className="btn btn-primary"
        onClick={handleAnalyze}
        disabled={!narrative.trim() || loading}
        style={{ width: '100%', marginTop: '1rem' }}
      >
        Analyze Case
      </button>
    </div>
  );
}

export default IntakeForm;
