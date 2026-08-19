"use client";

import React, { useState, useEffect } from "react";
import ChatInterface from "@/components/chat-interface";
import ProgressIndicator, { LogEntry } from "@/components/progress-indicator";
import ResultsTable, { Company } from "@/components/results-table";

type ViewState = "chat" | "discovery" | "results";

export default function Home() {
  const [activeTab, setActiveTab] = useState<number>(0);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [searchId, setSearchId] = useState("");
  const [currentStage, setCurrentStage] = useState("query_gen");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [qualifiedCompanies, setQualifiedCompanies] = useState<Company[]>([]);
  const [disqualifiedCompanies, setDisqualifiedCompanies] = useState<Company[]>([]);
  const [blockedCompanies, setBlockedCompanies] = useState<Company[]>([]);
  const [sessionCriteria, setSessionCriteria] = useState<any>(null);
  
  const allCompanies = [...qualifiedCompanies, ...disqualifiedCompanies, ...blockedCompanies];

  const addLog = (type: string, message: string) => {
    const timestamp = new Date().toLocaleTimeString([], { hour12: false });
    setLogs((prev) => [...prev, { type, message, timestamp }]);
  };

  const handleDiscoveryStart = (criteria: {
    company_type: string;
    product_or_service: string;
    location: string;
    current_employer?: string | null;
  }) => {
    setSessionCriteria(criteria);
    setActiveTab(1); // Switch to Live Pipeline view
    setLogs([]);
    setQualifiedCompanies([]);
    setDisqualifiedCompanies([]);
    setBlockedCompanies([]);
    setSummary(null);
    setCurrentStage("query_gen");

    let hasAutoSwitched = false;

    let wsUrl = "ws://127.0.0.1:8000/api/ws/discovery";
    if (process.env.NEXT_PUBLIC_API_URL) {
      wsUrl = process.env.NEXT_PUBLIC_API_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws/discovery";
    }
    const apiKey = process.env.NEXT_PUBLIC_API_SECRET_KEY || "";
    const wsUrlWithAuth = apiKey ? `${wsUrl}?api_key=${apiKey}` : wsUrl;
    const ws = new WebSocket(wsUrlWithAuth);

    ws.onopen = () => {
      addLog("system", "Connected to discovery engine...");
      ws.send(JSON.stringify(criteria));
    };

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "ping") return;
      const { type, message, data } = payload;

      addLog(type, message);

      if (type === "query_gen") {
        setCurrentStage("query_gen");
        if (data.search_id) setSearchId(data.search_id);
      } else if (type === "search") {
        setCurrentStage("search");
      } else if (type === "crawl_start" || type === "crawl_progress" || type === "page_extracted") {
        setCurrentStage("crawl");
      } else if (type === "ai_start") {
        setCurrentStage("ai");
      } else if (type === "ai_qualified" || type === "ai_disqualified" || type === "ai_blocked") {
        setCurrentStage("ai");
        
        if (!hasAutoSwitched) {
          setActiveTab(2); // Auto-switch to Results when the first result streams in!
          hasAutoSwitched = true;
        }

        if (data && data.company) {
          if (type === "ai_qualified") {
            setQualifiedCompanies(prev => {
              if (prev.some(c => c.company_name === data.company.company_name)) return prev;
              return [...prev, data.company];
            });
          } else if (type === "ai_blocked" || data.company.is_blocked || data.company.qualification?.is_blocked) {
            setBlockedCompanies(prev => {
              if (prev.some(c => c.company_name === data.company.company_name)) return prev;
              return [...prev, data.company];
            });
          } else {
            setDisqualifiedCompanies(prev => {
              if (prev.some(c => c.company_name === data.company.company_name)) return prev;
              return [...prev, data.company];
            });
          }
        }
      } else if (type === "sheets_start") {
        setCurrentStage("sheets");
      } else if (type === "completed") {
        setCurrentStage("completed");
        
        if (!hasAutoSwitched) {
          setActiveTab(2); // Auto-switch to Results if it finishes (e.g. all blocked/failed)
          hasAutoSwitched = true;
        }

        if (data && data.summary) setSummary(data.summary);
        ws.close();
      } else if (type === "failed" || type === "error") {
        setCurrentStage("failed");
        ws.close();
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      addLog("error", "Error connecting to discovery backend websocket.");
      setCurrentStage("failed");
    };

    ws.onclose = () => {
      addLog("system", "WebSocket connection closed.");
      setCurrentStage((prev) => (prev === "failed" ? "failed" : "completed"));
    };
  };

  // Determine active rail index dynamically based on both real-time stage AND active tab
  const activeRailIdx = activeTab === 0 ? 0 
                      : activeTab === 2 ? 3
                      : (currentStage === "query_gen" || currentStage === "search" ? 1 
                      : currentStage === "completed" || currentStage === "sheets" ? 3 : 2);

  return (
    <div className="app-shell">
      {/* ============ SIDEBAR ============ */}
      <nav className={`sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`} id="sidebar">
        <div className="sb-brand">
          <div className="brand-mark">LG</div>
          <div className="sb-brand-text">
            <h1>Lead Gen App</h1>
            <p>DISCOVERY &amp; QUALIFICATION</p>
          </div>
        </div>

        <div className="sb-scroll">
          <div className="sb-section-label">Workspace</div>
          <div className={`sb-item ${activeTab === 0 ? 'active' : ''}`} onClick={() => setActiveTab(0)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"/></svg>
            <span className="sb-item-label">New Intake</span>
          </div>
          <div 
            className={`sb-item ${activeTab === 1 ? 'active' : ''}`} 
            onClick={() => { if (sessionCriteria) setActiveTab(1); }}
            style={{ opacity: sessionCriteria ? 1 : 0.4, cursor: sessionCriteria ? 'pointer' : 'not-allowed' }}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            <span className="sb-item-label">Live Pipeline</span>
            {activeTab === 1 && currentStage !== "completed" && currentStage !== "failed" && <span className="live-dot" style={{marginLeft:'auto'}}></span>}
          </div>
          <div 
            className={`sb-item ${activeTab === 2 ? 'active' : ''}`} 
            onClick={() => { if (sessionCriteria) setActiveTab(2); }}
            style={{ opacity: sessionCriteria ? 1 : 0.4, cursor: sessionCriteria ? 'pointer' : 'not-allowed' }}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
            <span className="sb-item-label">Results</span>
            {allCompanies.length > 0 && <span className="sb-badge">{allCompanies.length}</span>}
          </div>

          <div className="sb-section-label">Records</div>
          <div className="sb-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18h18"/><path d="M18.7 8l-5.1 5.1-2.8-2.8L7 14"/></svg>
            <span className="sb-item-label">Scan History</span>
            <span className="sb-badge-soon">SOON</span>
          </div>
          <div className="sb-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 4h16v4H4zM4 12h16v8H4z"/></svg>
            <span className="sb-item-label">Saved Profiles</span>
            <span className="sb-badge-soon">SOON</span>
          </div>
          <div className="sb-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
            <span className="sb-item-label">Pipeline (CRM)</span>
            <span className="sb-badge-soon">SOON</span>
          </div>
        </div>

        <div className="sb-footer">
          <div className="sb-avatar">JD</div>
          <div className="sb-footer-text">
            <div className="name">J. Doe</div>
            <div className="tier">PRO WORKSPACE</div>
          </div>
        </div>
      </nav>
      <div className="sb-collapse-btn" onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)} title="Collapse sidebar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
      </div>

      {/* ============ MAIN COLUMN ============ */}
      <div className="main-col">
        <header>
          <div style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: '16px' }}>
            {activeTab === 0 ? "Target Intake Protocol" : activeTab === 1 ? "Live Discovery Pipeline" : "Qualification Results"}
          </div>
          <div className="agent-badge"><span className="agent-dot"></span>Active Agent</div>
        </header>

        {activeTab <= 2 && (
          <div className="scanrail-wrap" style={{ display: 'block' }}>
            <div className="scanrail" id="scanrail">
              {[
                { label: "Auto-Detect", idx: 0 },
                { label: "Search Google", idx: 1 },
                { label: "AI Analysis", idx: 2 },
                { label: "Results", idx: 3 }
              ].map((step, i) => {
                const isClickable = i === 0 || !!sessionCriteria;
                const handleRailClick = () => {
                  if (!isClickable) return;
                  if (i === 0) setActiveTab(0);
                  if (i === 1 || i === 2) setActiveTab(1);
                  if (i === 3) setActiveTab(2);
                };
                return (
                  <React.Fragment key={i}>
                    <div 
                      className={`rail-step ${activeRailIdx > i ? 'done' : activeRailIdx === i ? 'active' : ''}`}
                      onClick={handleRailClick}
                      style={{ cursor: isClickable ? 'pointer' : 'not-allowed' }}
                    >
                      <div className="rail-node"></div>
                      <div className="rail-label">{step.label}</div>
                    </div>
                    {i < 3 && (
                      <div className={`rail-line ${activeRailIdx > i ? 'filled' : ''}`}></div>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>
        )}

        <main>
          {/* ============ VIEW 0: INTAKE ============ */}
          <div className={`view ${activeTab === 0 ? 'active' : ''}`}>
            <ChatInterface onDiscoveryStart={handleDiscoveryStart} />
          </div>

          {/* ============ VIEW 1: LIVE PIPELINE ============ */}
          <div className={`view ${activeTab === 1 ? 'active' : ''}`}>
            <ProgressIndicator 
              logs={logs} 
              currentStage={currentStage} 
              sessionCriteria={sessionCriteria}
              allCompanies={allCompanies} 
              summary={summary}
            />
          </div>

          {/* ============ VIEW 2: RESULTS ============ */}
          <div className={`view ${activeTab === 2 ? 'active' : ''}`}>
            <ResultsTable 
              qualifiedCompanies={qualifiedCompanies} 
              disqualifiedCompanies={disqualifiedCompanies} 
              blockedCompanies={blockedCompanies}
              summary={summary}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
