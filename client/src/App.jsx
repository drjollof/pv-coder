import React, { useState, useRef, useEffect } from 'react'
import { AlertTriangle, CheckCircle, Download, FileText, ChevronDown, ChevronRight, Info, Circle, CircleDot, Search, XCircle, Clock, Database, Server, X } from 'lucide-react'
import { Client } from "@gradio/client"

import SingleIntake from './components/SingleIntake';
import BatchUpload from './components/BatchUpload';
import UserGuide from './components/UserGuide';

function App() {
  const [activeTab, setActiveTab] = useState('single')

  // Dynamically choose backend URL based on environment
  window.API_URL = import.meta.env.DEV
    ? "http://127.0.0.1:7860"
    : "https://drjollof-pv-coder-api.hf.space";

  const [systemStatus, setSystemStatus] = useState({
    engineReady: false,
    runtime: "Connecting...",
    meddraVersion: "Unknown"
  });
  
  const [historyOpen, setHistoryOpen] = useState(false);
  const [caseHistory, setCaseHistory] = useState([]);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    // Load history
    const saved = localStorage.getItem('pv_coder_history');
    if (saved) {
      try {
        setCaseHistory(JSON.parse(saved));
      } catch (e) {
        console.error("Error parsing history", e);
      }
    }

    // Poll status
    const fetchStatus = async () => {
      try {
        const client = await Client.connect(window.API_URL);
        const res = await client.predict("/status", []);
        if (res && res.data) {
          const parsed = JSON.parse(res.data[0]);
          setSystemStatus({
            engineReady: parsed.engine_ready,
            runtime: parsed.runtime,
            meddraVersion: parsed.meddra_version
          });
        }
      } catch (err) {
        console.error("Status fetch failed", err);
        setSystemStatus({
          engineReady: false,
          runtime: "Offline",
          meddraVersion: "Unknown"
        });
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (historyOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => { document.body.style.overflow = 'unset'; }
  }, [historyOpen]);

  // Make caseHistory and setCaseHistory globally available for SingleIntake
  // In a real app we'd use context, but attaching to window is a quick way to pass it without huge refactors
  window.addCaseToHistory = (caseObj) => {
    const summary = {
      id: caseObj.case_id,
      date: new Date().toISOString(),
      serious: caseObj.is_serious_case,
      eventsCount: caseObj.events?.length || 0,
      needsReview: caseObj.events?.some(e => e.review_status === "Human Review")
    };
    setCaseHistory(prev => {
      const newHistory = [summary, ...prev.filter(h => h.id !== summary.id)].slice(0, 50);
      localStorage.setItem('pv_coder_history', JSON.stringify(newHistory));
      return newHistory;
    });
  };

  return (
    <div>
      <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>PV-Coder</h1>
          <p>NLP-assisted Pharmacovigilance Case Intake System.</p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '0.85rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <CircleDot size={12} color={systemStatus.engineReady ? "#4ade80" : "#f87171"} />
              {systemStatus.engineReady ? "NLP Engine Ready" : "NLP Engine Offline"}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#94a3b8' }}>
              <Server size={12} />
              {systemStatus.runtime}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#94a3b8' }}>
              <Database size={12} />
              MedDRA {systemStatus.meddraVersion}
            </span>
          </div>
        </div>
      </header>

      <div className="glass-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--glass-border)', marginBottom: '2rem' }}>
          <div className="tabs" style={{ borderBottom: 'none', marginBottom: 0 }}>
            <button
              className={`tab ${activeTab === 'single' ? 'active' : ''}`}
              onClick={() => setActiveTab('single')}
            >
              Single Intake
            </button>
            <button
              className={`tab ${activeTab === 'batch' ? 'active' : ''}`}
              onClick={() => setActiveTab('batch')}
            >
              Batch Upload
            </button>
            <button
              className={`tab ${activeTab === 'guide' ? 'active' : ''}`}
              onClick={() => setActiveTab('guide')}
            >
              User Guide
            </button>
          </div>
          <button 
            onClick={() => setHistoryOpen(true)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', marginRight: '1rem', marginBottom: '8px' }}
            className="btn btn-secondary"
          >
            <Clock size={16} />
            Case History
          </button>
        </div>

        {activeTab === 'single' && <SingleIntake />}
        {activeTab === 'batch' && <BatchUpload />}
        {activeTab === 'guide' && <UserGuide />}
      </div>

      {historyOpen && (
        <>
          {/* Backdrop */}
          <div 
            onClick={() => setHistoryOpen(false)}
            style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 999 }}
          />
          {/* Drawer */}
          <div style={{
            position: 'fixed', top: 0, right: 0, width: '350px', height: '100vh',
          backgroundColor: '#0B0F19', borderLeft: '1px solid #1e293b',
          zIndex: 1000, padding: '24px', display: 'flex', flexDirection: 'column',
          boxShadow: '-4px 0 15px rgba(0,0,0,0.5)', overflowY: 'auto'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <h4 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1rem', color: 'var(--text-primary)' }}><Clock size={16} /> Case History</h4>
            <button 
              onClick={() => setHistoryOpen(false)}
              style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', padding: '4px' }}
            >
              <X size={20} />
            </button>
          </div>
          
          <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '24px', padding: '12px', backgroundColor: '#11151F', borderRadius: '4px', borderLeft: '3px solid #3b82f6' }}>
            <strong>Privacy Note:</strong> Only metadata is saved locally in your browser. Full clinical narratives are not persisted.
          </div>

          {caseHistory.length === 0 ? (
            <div style={{ color: '#94a3b8', textAlign: 'center', marginTop: '40px' }}>
              No recent cases.<br />Analyzed cases will appear here.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {caseHistory.map((h, i) => (
                <div 
                  key={i} 
                  onClick={() => {
                    navigator.clipboard.writeText(h.id);
                    setCopiedId(h.id);
                    setTimeout(() => setCopiedId(null), 2000);
                  }}
                  title="Click to copy Case ID"
                  style={{ 
                    padding: '16px', 
                    backgroundColor: '#1A1D24', 
                    borderRadius: '8px', 
                    borderLeft: `3px solid ${h.serious ? '#f87171' : (h.needsReview ? '#fbbf24' : '#4ade80')}`,
                    cursor: 'pointer',
                    transition: 'background-color 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#252933'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#1A1D24'}
                >
                  <div style={{ fontWeight: '600', marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    {h.id}
                    {copiedId === h.id ? (
                      <span style={{ fontSize: '0.75rem', color: '#4ade80', display: 'flex', alignItems: 'center', gap: '4px' }}><CheckCircle size={12}/> Copied!</span>
                    ) : (
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Copy ID</span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '8px' }}>
                    {new Date(h.date).toLocaleDateString()} · {h.eventsCount} events
                  </div>
                  <div style={{ fontSize: '0.8rem', display: 'flex', gap: '8px' }}>
                    <span style={{ color: h.serious ? '#f87171' : '#4ade80' }}>
                      {h.serious ? 'Serious' : 'Non-serious'}
                    </span>
                    <span style={{ color: '#64748b' }}>·</span>
                    <span style={{ color: h.needsReview ? '#fbbf24' : '#4ade80' }}>
                      {h.needsReview ? 'Review Required' : 'Validated'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
          </div>
        </>
      )}
    </div>
  )
}


export default App;
