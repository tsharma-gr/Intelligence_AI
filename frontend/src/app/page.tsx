"use client";

import React, { useState, useEffect } from "react";
import { Sparkles, Cpu, RefreshCw, Layers } from "lucide-react";
import ChatInterface from "@/components/chat-interface";
import ProgressIndicator, { LogEntry } from "@/components/progress-indicator";
import ExecutionSummary from "@/components/execution-summary";
import ResultsTable, { Company } from "@/components/results-table";
import { collection, query, where, onSnapshot, doc } from "firebase/firestore";
import { db } from "@/lib/firebase";

type ViewState = "chat" | "discovery" | "results";

export default function Home() {
  const [viewState, setViewState] = useState<ViewState>("chat");
  const [searchId, setSearchId] = useState("");
  const [currentStage, setCurrentStage] = useState("query_gen");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [qualifiedCompanies, setQualifiedCompanies] = useState<Company[]>([]);
  const [disqualifiedCompanies, setDisqualifiedCompanies] = useState<Company[]>([]);
  const [sessionCriteria, setSessionCriteria] = useState<any>(null);
  const headerRef = React.useRef<HTMLDivElement>(null);
  
  const allCompanies = [...qualifiedCompanies, ...disqualifiedCompanies];

  // Firebase Real-time Listeners
  useEffect(() => {
    if (!searchId) return;

    // 1. Qualified Companies
    const qQualified = query(collection(db, "qualified_companies"), where("search_id", "==", searchId));
    const unsubQualified = onSnapshot(qQualified, (snapshot) => {
      const docs = snapshot.docs.map(d => d.data() as Company);
      setQualifiedCompanies(docs);
    });

    // 2. Disqualified Companies
    const qDisqualified = query(collection(db, "disqualified_companies"), where("search_id", "==", searchId));
    const unsubDisqualified = onSnapshot(qDisqualified, (snapshot) => {
      const docs = snapshot.docs.map(d => d.data() as Company);
      setDisqualifiedCompanies(docs);
    });

    // 3. Execution Summary (Final metrics)
    const qSummary = query(collection(db, "search_history"), where("search_id", "==", searchId));
    const unsubSummary = onSnapshot(qSummary, (snapshot) => {
      if (!snapshot.empty) {
        const data = snapshot.docs[0].data();
        if (data.summary) {
          setSummary(data.summary);
        }
      }
    });

    return () => {
      unsubQualified();
      unsubDisqualified();
      unsubSummary();
    };
  }, [searchId]);

  useEffect(() => {
    let ticking = false;
    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const scrollY = window.scrollY;
          if (headerRef.current) {
            const opacity = Math.max(1 - scrollY / 250, 0);
            const scale = Math.max(1 - scrollY / 800, 0.95);
            const blur = Math.min(scrollY / 15, 10);
            
            headerRef.current.style.opacity = opacity.toString();
            headerRef.current.style.transform = `scale(${scale})`;
            headerRef.current.style.filter = `blur(${blur}px)`;
            headerRef.current.style.pointerEvents = scrollY > 50 ? 'none' : 'auto';
          }
          ticking = false;
        });
        ticking = true;
      }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const addLog = (type: string, message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { type, message, timestamp }]);
  };

  const handleDiscoveryStart = (criteria: {
    company_type: string;
    product_or_service: string;
    location: string;
    current_employer?: string | null;
  }) => {
    setSessionCriteria(criteria);
    setViewState("discovery");
    setLogs([]);
    setCurrentStage("query_gen");

    // Establish WebSocket Connection
    // Establish WebSocket Connection using exact production URL to prevent env var path bugs, or localhost in development
    let wsUrl = process.env.NODE_ENV === "development" ? "ws://127.0.0.1:8000/api/ws/discovery" : "wss://company-intelligence-backend.onrender.com/api/ws/discovery";
    if (process.env.NEXT_PUBLIC_API_URL) {
      wsUrl = process.env.NEXT_PUBLIC_API_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws/discovery";
    }
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      addLog("system", "Connected to discovery engine...");
      // Send criteria payload
      ws.send(JSON.stringify(criteria));
    };

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      const { type, message, data } = payload;

      // Add message to live logs
      addLog(type, message);

      // Map progress updates to stages
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
        // State is now managed automatically via Firebase onSnapshot listeners!
      } else if (type === "sheets_start") {
        setCurrentStage("sheets");
      } else if (type === "completed") {
        setCurrentStage("completed");
        // Summary and final data is now fetched via Firebase onSnapshot listeners
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
      // Ensure the UI stops spinning when the backend disconnects naturally
      setCurrentStage((prev) => (prev === "failed" ? "failed" : "completed"));
    };
  };

  const handleReset = () => {
    setViewState("chat");
    setSessionCriteria(null);
    setLogs([]);
    setSummary(null);
    setQualifiedCompanies([]);
    setDisqualifiedCompanies([]);
    setSearchId("");
  };

  return (
    <main className="cia-root flex flex-col relative pb-16" style={{ padding: 0 }}>
      {/* Header */}
      <div className="cia-header" style={{ padding: '16px 32px', borderBottom: '1px solid var(--border)', background: 'rgba(10, 11, 16, 0.8)', backdropFilter: 'blur(12px)', position: 'sticky', top: 0, zIndex: 50 }}>
        <div className="cia-brand">
          <div className="cia-mark">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L20 6.5V17.5L12 22L4 17.5V6.5L12 2Z" stroke="#cca35e" strokeWidth="1.4"/>
              <circle cx="12" cy="12" r="3" stroke="#e8c37f" strokeWidth="1.4"/>
            </svg>
          </div>
          <div className="cia-brand-text">
            <div className="cia-title">Company Intelligence AI</div>
            <div className="cia-eyebrow">Discovery &amp; Qualification</div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {viewState !== "chat" && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/5 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5 transition-all cursor-pointer"
            >
              <RefreshCw size={12} />
              <span style={{ fontFamily: 'var(--font-body)' }}>Start New Search</span>
            </button>
          )}
          <div className="hidden sm:flex cia-agent-pill">
            <span className="cia-dot-live"></span>
            Active Agent
          </div>
        </div>
      </div>

      {/* Content Container */}
      <section className="flex-1 flex flex-col p-4 md:p-8 max-w-5xl w-full mx-auto space-y-8 justify-center">
        
        {/* VIEW 1: Requirements Collection Dialogue */}
        {viewState === "chat" && (
          <div className="w-full flex flex-col gap-6 items-center">
            <div 
              ref={headerRef}
              className="text-center max-w-lg mb-2"
            >
              <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-zinc-100 mb-2 font-display">
                Company Discovery Engine
              </h2>
              <p className="text-xs md:text-sm text-zinc-400 leading-relaxed font-body">
                Describe the company profile in the chat. The AI will interview you, generate queries, crawl websites, and perform automatic qualifications.
              </p>
            </div>
            <ChatInterface onDiscoveryStart={handleDiscoveryStart} />
          </div>
        )}

        {/* VIEW 2: Real-time Discovery Tracker */}
        {viewState === "discovery" && (
          <div className="space-y-6 w-full py-4">
            <div className="text-center max-w-md mx-auto space-y-3 mb-8">
              <h2 className="text-2xl font-bold font-display" style={{ color: 'var(--text-primary)' }}>Running AI Discovery Pipeline</h2>
              <p className="text-sm font-body leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                Searching Google for target criteria, crawling matches, extracting content, and auditing with DeepSeek.
              </p>
            </div>
            
            {/* Target criteria tag board */}
            {sessionCriteria && (
              <div className="flex flex-wrap justify-center gap-3 max-w-2xl mx-auto mb-6">
                <span className="cia-version" style={{ fontSize: '11px' }}>
                  <b style={{ color: 'var(--gold-bright)', marginRight: '6px' }}>TYPE:</b> {sessionCriteria.company_type}
                </span>
                <span className="cia-version" style={{ fontSize: '11px' }}>
                  <b style={{ color: 'var(--gold-bright)', marginRight: '6px' }}>PRODUCT:</b> {sessionCriteria.product_or_service}
                </span>
                <span className="cia-version" style={{ fontSize: '11px' }}>
                  <b style={{ color: 'var(--gold-bright)', marginRight: '6px' }}>LOCATION:</b> {sessionCriteria.location}
                </span>
              </div>
            )}

            <ProgressIndicator logs={logs} currentStage={currentStage} />
            
            {/* Live Results Section */}
            {(allCompanies.length > 0 || summary) && (
              <div className="mt-12 space-y-8 w-full animate-fade-in border-t border-white/10 pt-12">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-4">
                  <div>
                    <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
                      <Layers className="text-blue-400" size={20} />
                      <span>Discovery Results {summary ? 'Summary' : '(Live Stream)'}</span>
                    </h2>
                    <p className="text-xs text-zinc-500 mt-1">
                      {summary ? 'Export complete. All logs and tables successfully stored in Google Sheets.' : 'Real-time AI qualification in progress...'}
                    </p>
                  </div>
                </div>

                {/* KPI Cards */}
                {summary && (
                  <ExecutionSummary summary={summary} searchId={searchId} />
                )}

                {/* Split Tables tabbed list */}
                {allCompanies.length > 0 && (
                  <ResultsTable companies={allCompanies} />
                )}
              </div>
            )}
          </div>
        )}

      </section>
    </main>
  );
}
