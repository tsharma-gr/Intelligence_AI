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
  summary?: any;
}

export default function ProgressIndicator({ logs, currentStage, sessionCriteria, allCompanies, summary }: ProgressIndicatorProps) {
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
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (currentStage === "completed" || currentStage === "failed") {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }
    
    if (currentStage !== "query_gen" && !timerRef.current) {
      timerRef.current = setInterval(() => {
        setElapsed(prev => prev + 1);
      }, 1000);
    }
    
    return () => {
      // Don't cleanup the interval on re-render unless component unmounts
      // We manage the cleanup manually when stage reaches completed/failed
    };
  }, [currentStage]);

  // Cleanup on unmount only
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

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
          <div className="n">{summary?.duration ? summary.duration : formatElapsed(elapsed)}</div>
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
            <style dangerouslySetInnerHTML={{__html: `
              .radar-wrap{ display:flex; align-items:center; justify-content:center; padding:20px 0 6px; }
              .radar{ position:relative; width:150px; height:150px; }
              .radar-ring{ position:absolute; border:1px solid var(--border, #21242D); border-radius:50%; }
              .radar-ring.r1{ inset:0; }
              .radar-ring.r2{ inset:20px; }
              .radar-ring.r3{ inset:40px; }
              .radar-ring.r4{ inset:60px; border-color: rgba(203,163,95,0.3); }
              .radar-sweep{ position:absolute; inset:0; border-radius:50%; overflow:hidden; animation: sweep 3.2s linear infinite; }
              .radar-sweep::before{ content:''; position:absolute; inset:0; background: conic-gradient(from 0deg, rgba(203,163,95,0.55), transparent 28%); }
              @keyframes sweep{ to{ transform: rotate(360deg); } }
              .radar-blip{ position:absolute; width:6px; height:6px; border-radius:50%; background:var(--accent-gold, #CBA35F); box-shadow:0 0 8px rgba(203,163,95,0.8); animation: blip-pulse 2s ease-in-out infinite; }
              @keyframes blip-pulse{ 0%,100%{ opacity:.5; transform:scale(0.8);} 50%{ opacity:1; transform:scale(1.2);} }
              .radar-center{ position:absolute; left:50%; top:50%; width:4px; height:4px; background:var(--accent-gold, #CBA35F); border-radius:50%; transform:translate(-50%,-50%); }
            `}} />
            <div className="radar-wrap">
              <div className="radar">
                <div className="radar-ring r1"></div>
                <div className="radar-ring r2"></div>
                <div className="radar-ring r3"></div>
                <div className="radar-ring r4"></div>
                <div className="radar-sweep"></div>
                <div className="radar-center"></div>
                <div className="radar-blip" style={{ top: '28%', left: '62%', animationDelay: '.2s' }}></div>
                <div className="radar-blip" style={{ top: '65%', left: '34%', animationDelay: '.9s' }}></div>
                <div className="radar-blip" style={{ top: '48%', left: '78%', animationDelay: '1.5s' }}></div>
              </div>
            </div>
            <div className="bubble" style={{ background: 'var(--bg-inset)', color: '#FFFFFF' }}>
              <b style={{ color: '#F0685C' }}>Category:</b> {sessionCriteria?.company_type || 'Unknown'}<br />
              <b style={{ color: '#F0685C' }}>Product/Service:</b> {sessionCriteria?.product_or_service || 'Unknown'}<br />
              <b style={{ color: '#F0685C' }}>Region:</b> {sessionCriteria?.location || 'Unknown'}<br />
              <b style={{ color: '#F0685C' }}>Signal source:</b> CV + Employer Domain
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
