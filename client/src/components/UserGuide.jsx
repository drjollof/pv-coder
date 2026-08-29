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
          <li>If the text contains critical keywords (like "fatal" or "hospitalized"), it triggers a <strong>Serious Case</strong> alarm for expedited regulatory reporting (15-day timeline).</li>
        </ul>
      </section>

      <section style={{ marginBottom: '2rem' }}>
        <h3>3. Batch Uploads</h3>
        <p>If you have thousands of historical reports in a spreadsheet, use the <strong>Batch Upload</strong> tab. Upload a CSV with a column named <code>narrative</code>, and the backend will process all cases silently and return a compiled CSV with the MedDRA codes.</p>
      </section>

      <section>
        <h3>4. E2B (R3) XML & Reporting</h3>
        <p>After reviewing a single case, you can export it to PDF (for internal team meetings) or to an E2B-style XML file. XML is the global standard format used to transmit cases between safety databases like Oracle Argus and regulatory agencies like the FDA or EMA.</p>
      </section>
    </div>
  )
}


export default UserGuide;
