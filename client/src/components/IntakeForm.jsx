import React from 'react';

function IntakeForm({ narrative, setNarrative, previousCaseJson, setPreviousCaseJson, handleAnalyze, examples, loading }) {
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      setPreviousCaseJson(evt.target.result);
    };
    reader.readAsText(file);
  };

  return (
    <div style={{ marginBottom: '1.5rem', animation: 'slideIn 0.3s ease-out' }}>
      <div className="mobile-stack" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
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
        placeholder={previousCaseJson ? "Paste new follow-up narrative here..." : "Paste unstructured clinical text here..."}
        value={narrative}
        onChange={(e) => setNarrative(e.target.value)}
      />

      <div style={{ marginTop: '1rem', background: 'var(--bg-tertiary)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)' }}>
        <h4 style={{ marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Is this a Follow-up Case? (Optional)</h4>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          Upload a previously exported Case JSON. The new narrative above will be processed and merged with the existing case to create a new version.
        </p>
        <div className="mobile-stack" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <label 
            className="btn btn-secondary btn-mobile-full" 
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <input 
              type="file" 
              accept=".json" 
              onChange={handleFileUpload} 
              disabled={loading}
              style={{ display: 'none' }}
            />
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
            Select Previous Case (.json)
          </label>
          
          {previousCaseJson ? (
            <span style={{ color: 'var(--success)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
               <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
               Prior Case Loaded
            </span>
          ) : (
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>No file chosen</span>
          )}
        </div>
      </div>
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
