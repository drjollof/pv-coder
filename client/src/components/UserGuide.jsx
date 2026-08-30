import React from 'react';

function UserGuide() {
  return (
    <div style={{ animation: 'slideIn 0.3s ease-out', lineHeight: '1.8' }}>
      <h2 style={{ marginBottom: '1.5rem', color: 'var(--accent-primary)' }}>How to Use PV-Coder</h2>

      <section style={{ marginBottom: '2rem' }}>
        <h3>1. What is PV-Coder?</h3>
        <p>PV-Coder is an AI-assisted Pharmacovigilance (PV) intake engine. When pharmaceutical companies receive emails or letters about side effects, a human usually has to manually read the text and look up standard MedDRA codes. PV-Coder automates this using Natural Language Processing (NLP) to instantly extract drugs and adverse events, and cross-reference them against the MedDRA dictionary.</p>
      </section>

      <section style={{ marginBottom: '2rem' }}>
        <h3>2. Single Intake & Human-in-the-Loop</h3>
        <p>In the <strong>Single Intake</strong> tab, you can paste a clinical narrative. The AI will highlight suspected adverse events and drugs.</p>
        <ul style={{ marginLeft: '1.5rem', color: 'var(--text-secondary)' }}>
          <li>If the AI is highly confident (e.g. mapping "heart attack" to "Myocardial Infarction"), it will mark the status as <span style={{ color: 'var(--success)' }}>Auto-coded</span>.</li>
          <li>If the AI is unsure, it will flag it as <span style={{ color: 'var(--warning)' }}>Review Needed</span>. A Human-in-the-Loop panel will appear below, allowing a human scientist to make the final decision.</li>
        </ul>
      </section>

      <section style={{ marginBottom: '2rem' }}>
        <h3>3. Advanced Overrides (Adding & Excluding Events)</h3>
        <p>PV-Coder gives you complete manual control over the extraction results. If you spot an error, you can easily correct it before validating the case:</p>
        <ul style={{ marginLeft: '1.5rem', color: 'var(--text-secondary)' }}>
          <li><strong>Excluding False Positives:</strong> If the AI extracts a word that is NOT an adverse event (e.g. "withdrawn"), simply click on the row and select the <strong>Exclude Event (False Positive)</strong> button. You can also press the <strong>`5`</strong> key on your keyboard while reviewing it. The event will be struck through and removed from all exports.</li>
          <li><strong>Adding False Negatives:</strong> If the AI missed an event entirely, scroll to the bottom of the table and click <strong>+ Add Missing Event</strong>. You can manually enter the Raw Text, MedDRA PT, and MedDRA ID to instantly inject it into the case payload.</li>
        </ul>
      </section>

      <section style={{ marginBottom: '2rem' }}>
        <h3>4. ZeroGPU Quotas & Authentication (BYOT)</h3>
        <p>The backend NLP models run on Hugging Face's free community GPU infrastructure (ZeroGPU). Because it is a shared resource, anonymous users are strictly limited to a short time quota (e.g., 90 seconds) and will see an error if they exceed it.</p>
        <ul style={{ marginLeft: '1.5rem', color: 'var(--text-secondary)' }}>
          <li>To permanently bypass this limit, you can generate a free <strong>Read Token</strong> from your <a href="https://huggingface.co/settings/tokens" target="_blank" rel="noopener noreferrer" style={{color: 'var(--accent-primary)'}}>Hugging Face account settings</a>.</li>
          <li>Paste that token into the <strong>HF Token (Optional)</strong> field in the top-right corner of this app.</li>
          <li>Your browser will securely save it locally, unlocking a massively increased personal GPU quota for all future sessions!</li>
        </ul>
      </section>

      <section style={{ marginBottom: '2rem' }}>
        <h3>5. Batch Uploads & E2B (R3) XML Exports</h3>
        <p>If you have thousands of historical reports in a spreadsheet, use the <strong>Batch Upload</strong> tab. Upload a CSV with a column named <code>narrative</code>, and the backend will process all cases silently and return a compiled ZIP of XMLs.</p>
        <p>After reviewing a single case, you can also export it to PDF (for internal team meetings) or to an E2B-style XML file. XML is the global standard format used to transmit cases between safety databases like Oracle Argus and regulatory agencies like the FDA or EMA.</p>
      </section>
    </div>
  )
}

export default UserGuide;
