"use client";

import React, { useEffect, useRef, useState } from "react";

export interface LogEntry {
  type: string;
  message: string;
  timestamp: string;
}

interface ProgressIndicatorProps {
  logs: LogEntry[];
  currentStage: string;
  sessionCriteria: any;
  allCompanies: any[];
}

export default function ProgressIndicator({ logs, currentStage, sessionCriteria, allCompanies }: ProgressIndicatorProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const [elapsed, setElapsed] = useState(0);
  const [timerInterval, setTimerInterval] = useState<NodeJS.Timeout | null>(null);

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  // Elapsed timer
  useEffect(() => {
    if (currentStage !== "query_gen" && currentStage !== "completed" && currentStage !== "failed") {
      if (!timerInterval) {
        const int = setInterval(() => setElapsed(prev => prev + 1), 1000);
        setTimerInterval(int);
      }
    } else if (currentStage === "completed" || currentStage === "failed") {
      if (timerInterval) {
        clearInterval(timerInterval);
        setTimerInterval(null);
      }
    }
    return () => {
      if (timerInterval) clearInterval(timerInterval);
    };
  }, [currentStage, timerInterval]);

  const formatElapsed = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    if (mins > 0) return `${mins}m ${s}s`;
    return `${s}s`;
  };

  const activeWebsitesCount = allCompanies.length || 0; 
  // Very rough estimate of progress
  const progressPercent = currentStage === "query_gen" ? 10 
                        : currentStage === "search" ? 30 
                        : currentStage === "crawl" ? 60 
                        : currentStage === "ai" ? 85 
                        : currentStage === "completed" ? 100 : 0;

  return (
    <>
      <div className="scan-stats">
        <div className="scan-stat">
          <div className="l">Websites Processed</div>
          <div className="n">{activeWebsitesCount}</div>
        </div>
        <div className="scan-stat gold">
          <div className="l">Current Stage</div>
          <div className="n" style={{ fontSize: '18px', display: 'flex', alignItems: 'center', marginTop: '10px' }}>
            {currentStage.replace('_', ' ').toUpperCase()}
          </div>
        </div>
        <div className="scan-stat violet">
          <div className="l">Status</div>
          <div className="n" style={{ fontSize: '18px', display: 'flex', alignItems: 'center', marginTop: '10px' }}>
            {currentStage === "completed" ? "FINISHED" : "RUNNING..."}
          </div>
        </div>
        <div className="scan-stat">
          <div className="l">Elapsed</div>
          <div className="n">{formatElapsed(elapsed)}</div>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1.6fr 1fr' }}>
        <div>
          <div className="panel-head" style={{ border: '1px solid var(--border)', borderBottom: 'none', borderRadius: '12px 12px 0 0', background: 'var(--bg-card)' }}>
            <div className="panel-title"><span className="live-dot"></span>Crawl Log</div>
            <div className="pill">PHASE: {currentStage.toUpperCase()}</div>
          </div>
          <div className="terminal" ref={terminalRef}>
            {logs.map((log, idx) => {
              let cls = 'info';
              if (log.type === 'error' || log.type === 'failed') cls = 'warn';
              else if (log.type.includes('qualified') || log.type.includes('completed') || log.type === 'ok') cls = 'ok';
              else if (log.type === 'system') cls = 'info';
              
              return (
                <div key={idx} className="term-line" style={{ animationDelay: '0s', opacity: 1 }}>
                  <span className="t">[{log.timestamp}]</span>
                  <span className={cls}>{log.message}</span>
                </div>
              );
            })}
            {currentStage !== "completed" && currentStage !== "failed" && (
              <div className="term-line" style={{ animationDelay: '0s', opacity: 1 }}>
                <span className="t">{'>'}</span>
                <span className="info">awaiting next log<span className="cursor"></span></span>
              </div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head"><div className="panel-title">Profile Being Matched</div></div>
          <div className="form-body" style={{ gap: '14px' }}>
            <div className="bubble" style={{ background: 'var(--bg-inset)' }}>
              <b>Category:</b> {sessionCriteria?.company_type || 'Unknown'}<br />
              <b>Product/Service:</b> {sessionCriteria?.product_or_service || 'Unknown'}<br />
              <b>Region:</b> {sessionCriteria?.location || 'Unknown'}<br />
              <b>Signal source:</b> CV + Employer Domain
            </div>
            <div className="progress-card" style={{ padding: 0, border: 'none', background: 'none', margin: 0 }}>
              <div className="progress-top"><span>Overall progress</span><b>{progressPercent}%</b></div>
              <div className="bar"><div className="bar-fill" style={{ width: `${progressPercent}%` }}></div></div>
            </div>
            <div className="submit-hint" style={{ textAlign: 'left', color: 'var(--text-secondary)' }}>
              This view stays live so you always know what's being checked and why — no silent 60-second wait.
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
