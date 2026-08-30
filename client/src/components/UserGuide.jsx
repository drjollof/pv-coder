import React from 'react';
import { Play, CheckSquare, AlertTriangle, FileCheck, Download, Layers, ShieldAlert, ArrowDown, Cpu, Activity, Search, ShieldCheck, UserCheck } from 'lucide-react';

function UserGuide() {
  return (
    <div style={{ animation: 'slideIn 0.3s ease-out', lineHeight: '1.8', maxWidth: '800px', margin: '0 auto', paddingBottom: '3rem' }}>
      <h2 style={{ marginBottom: '0.5rem', color: 'var(--accent-primary)', fontSize: '2rem' }}>PV-Coder Workflow Guide</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '2.5rem', fontSize: '1.1rem' }}>
        A comprehensive guide to processing Pharmacovigilance cases from intake to E2B export.
      </p>

      {/* How the AI Works Section */}
      <section style={{ marginBottom: '3rem', background: 'var(--bg-tertiary)', padding: '2rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)' }}>
        <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Cpu size={20} style={{ color: 'var(--accent-primary)' }} /> How the AI Works
        </h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
          PV-Coder uses a multi-stage NLP pipeline to automatically process unstructured narratives.
        </p>
        
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 'var(--radius-sm)', width: '100%', textAlign: 'center', border: '1px solid var(--glass-border)' }}>
            <strong>1. Clinical Narrative</strong>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Raw unstructured text input</div>
          </div>
          <ArrowDown size={20} style={{ color: 'var(--accent-primary)' }} />
          
          <div style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 'var(--radius-sm)', width: '100%', textAlign: 'center', border: '1px solid var(--glass-border)' }}>
            <strong>2. Entity Extraction</strong>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Biomedical NER Model (PyTorch/ONNX) extracts Drugs & Events</div>
          </div>
          <ArrowDown size={20} style={{ color: 'var(--accent-primary)' }} />
          
          <div style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 'var(--radius-sm)', width: '100%', textAlign: 'center', border: '1px solid var(--glass-border)' }}>
            <strong>3. Context Filtering</strong>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Rule-based filtering removes historical/negated events</div>
          </div>
          <ArrowDown size={20} style={{ color: 'var(--accent-primary)' }} />
          
          <div style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 'var(--radius-sm)', width: '100%', textAlign: 'center', border: '1px solid var(--glass-border)' }}>
            <strong>4. MedDRA Semantic Coding</strong>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>SapBERT embeddings + FAISS dense retrieval mapping</div>
          </div>
          <ArrowDown size={20} style={{ color: 'var(--accent-primary)' }} />
          
          <div style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 'var(--radius-sm)', width: '100%', textAlign: 'center', border: '1px solid var(--warning)' }}>
            <strong>5. Human Review</strong>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Scientist validates AI suggestions & low-confidence terms</div>
          </div>
          <ArrowDown size={20} style={{ color: 'var(--warning)' }} />
          
          <div style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: 'var(--radius-sm)', width: '100%', textAlign: 'center', border: '1px solid var(--success)' }}>
            <strong>6. E2B / PDF Export</strong>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Final structured output generation</div>
          </div>
        </div>
      </section>

      {/* Workflow Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
        
        <section>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}><Play size={20} /> 1. Start a Case</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Navigate to the <strong>Single Intake</strong> tab. Paste your clinical narrative into the text area. You can also fill out optional demographics (Age, Gender, Weight) and metadata. Click <strong>Analyze Narrative</strong> to start the NLP pipeline.
          </p>
        </section>

        <section>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}><Search size={20} /> 2. Review Extracted Events</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            The AI will highlight suspected adverse events and drugs directly in the text. Scroll down to the <strong>Extracted Entities</strong> table to view the structured results. 
          </p>
          <ul style={{ marginLeft: '1.5rem', color: 'var(--text-secondary)' }}>
            <li><span style={{ color: 'var(--success)' }}>Auto-coded</span>: High confidence matches that require no action.</li>
            <li><span style={{ color: 'var(--warning)' }}>Review Needed</span>: Ambiguous or low-confidence matches requiring your expertise.</li>
          </ul>
        </section>

        <section>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}><UserCheck size={20} /> 3. Resolve Review-Needed Terms</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Click on any row marked for review to expand the Human-in-the-Loop (HITL) panel.
          </p>
          <div style={{ background: 'var(--bg-tertiary)', padding: '1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)', marginBottom: '1rem' }}>
            <h4 style={{ marginBottom: '1rem', color: 'var(--accent-primary)' }}>Keyboard Shortcuts</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.9rem' }}>
              <div><kbd>1</kbd> - <kbd>3</kbd> Select Top Candidate</div>
              <div><kbd>4</kbd> Custom Manual Input / Reject</div>
              <div><kbd>5</kbd> Exclude Event (False Positive)</div>
              <div><kbd>↑</kbd> <kbd>↓</kbd> Change option / Navigate rows</div>
              <div><kbd>Enter</kbd> Save and move to next</div>
              <div><kbd>Shift</kbd>+<kbd>Enter</kbd> Go back to previous review</div>
              <div><kbd>Esc</kbd> Close panel</div>
            </div>
          </div>
          <p style={{ color: 'var(--text-secondary)' }}>
            If the AI missed an event completely (False Negative), use the <strong>+ Add Missing Event</strong> button at the bottom of the table.
          </p>
        </section>

        <section>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}><ShieldCheck size={20} /> 4. Validate the Case</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Once all events are reviewed, scroll to the <strong>Validation & Export</strong> panel. The system runs real-time E2B structural checks (e.g., verifying at least one valid MedDRA event and one suspected drug exist). You cannot export until the case passes validation.
          </p>
        </section>

        <section>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}><Download size={20} /> 5. Export the Case</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            After validation passes, you can export the case in multiple formats:
          </p>
          <ul style={{ marginLeft: '1.5rem', color: 'var(--text-secondary)' }}>
            <li><strong>JSON Payload</strong>: For programmatic integration with other internal tools.</li>
            <li><strong>PDF Report</strong>: A human-readable summary for medical review meetings.</li>
            <li><strong>E2B (R3) XML</strong>: The global regulatory standard format for transmitting cases to Oracle Argus, FDA, or EMA.</li>
          </ul>
        </section>

        <section>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}><Layers size={20} /> 6. Process a Batch</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            For historical backlogs, use the <strong>Batch Upload</strong> tab. Upload a CSV containing a <code>narrative</code> column. The system will process all rows in the background and generate a rich dashboard showing KPIs (Review Rate, Serious Cases, Top MedDRA PTs). You can export the entire batch as a ZIP of E2B XMLs.
          </p>
        </section>

        <section>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}><Activity size={20} /> 7. Understand Status and Confidence</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            The AI provides transparency into its decision-making. In the expanded review panel, the <strong>AI Decision Detail</strong> card shows:
          </p>
          <ul style={{ marginLeft: '1.5rem', color: 'var(--text-secondary)' }}>
            <li><strong>Confidence Score:</strong> The semantic similarity (0-100%) between the extracted text and the MedDRA dictionary term.</li>
            <li><strong>Seriousness Evidence:</strong> If an event is marked as <span style={{ color: 'var(--warning)' }}>Serious</span>, the AI highlights the exact sentence fragment that triggered the seriousness rule (e.g. "patient was hospitalized").</li>
          </ul>
        </section>

        <section>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}><ShieldAlert size={20} /> 8. ZeroGPU Quotas & Authentication (BYOT)</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            The backend NLP models run on Hugging Face's free community GPU infrastructure (ZeroGPU). Because it is a shared resource, anonymous users are strictly limited to a short time quota (e.g., 90 seconds) and will see an error if they exceed it.
          </p>
          <ul style={{ marginLeft: '1.5rem', color: 'var(--text-secondary)' }}>
            <li>To permanently bypass this limit, you can generate a free <strong>Read Token</strong> from your <a href="https://huggingface.co/settings/tokens" target="_blank" rel="noopener noreferrer" style={{color: 'var(--accent-primary)'}}>Hugging Face account settings</a>.</li>
            <li>Paste that token into the <strong>HF Token (Optional)</strong> field in the top-right corner of this app.</li>
            <li>Your browser will securely save it locally, unlocking a massively increased personal GPU quota for all future sessions!</li>
          </ul>
        </section>

      </div>
    </div>
  );
}

export default UserGuide;
