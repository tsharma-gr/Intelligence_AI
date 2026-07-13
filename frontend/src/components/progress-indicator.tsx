"use client";

import React, { useEffect, useRef } from "react";
import { Loader2, CheckCircle2, Circle, AlertCircle } from "lucide-react";

export interface LogEntry {
  type: string;
  message: string;
  timestamp: string;
}

interface ProgressIndicatorProps {
  logs: LogEntry[];
  currentStage: string; // 'query_gen', 'search', 'crawl', 'ai', 'sheets', 'completed', 'failed'
}

export default function ProgressIndicator({ logs, currentStage }: ProgressIndicatorProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const stages = [
    { id: "query_gen", label: "Generating Queries" },
    { id: "search", label: "Searching Google" },
    { id: "crawl", label: "Crawling & Indexing Websites" },
    { id: "ai", label: "AI Company Qualification" },
    { id: "sheets", label: "Google Sheets Exporting" }
  ];

  const getStageStatus = (stageId: string) => {
    const stageOrder = ["query_gen", "search", "crawl", "ai", "sheets", "completed"];
    const currentIndex = stageOrder.indexOf(currentStage);
    const targetIndex = stageOrder.indexOf(stageId);

    if (currentStage === "failed") {
      return "failed";
    }
    if (currentStage === "completed" || currentIndex > targetIndex) {
      return "completed";
    }
    if (currentIndex === targetIndex) {
      return "active";
    }
    return "pending";
  };

  return (
    <div className="w-full max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6 animate-fade-in" style={{ marginTop: '20px' }}>
      {/* Stages Checklist */}
      <div className="cia-panel md:col-span-1 p-6 space-y-4">
        <h3 className="cia-section-title border-b border-white/5 pb-3 mb-2" style={{ letterSpacing: '0.1em' }}>Discovery Process</h3>
        <div className="space-y-5 mt-2">
          {stages.map((stage) => {
            const status = getStageStatus(stage.id);
            return (
              <div key={stage.id} className="flex items-center gap-3 text-sm font-body">
                {status === "completed" && (
                  <CheckCircle2 style={{ color: 'var(--success)' }} className="shrink-0" size={18} />
                )}
                {status === "active" && (
                  <Loader2 style={{ color: 'var(--gold-bright)' }} className="animate-spin shrink-0" size={18} />
                )}
                {status === "pending" && (
                  <Circle className="text-zinc-700 shrink-0" size={18} />
                )}
                {status === "failed" && (
                  <AlertCircle className="text-rose-500 shrink-0" size={18} />
                )}
                <span
                  style={{
                    color: status === "active" ? 'var(--text-primary)' : status === "completed" ? 'var(--text-secondary)' : 'var(--text-tertiary)',
                    fontWeight: status === "active" ? 600 : 500
                  }}
                >
                  {stage.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Live Console Output */}
      <div className="cia-panel md:col-span-2 p-6 flex flex-col h-[340px]">
        <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-4">
          <h3 className="cia-section-title" style={{ letterSpacing: '0.1em', margin: 0 }}>Live Execution Logs</h3>
          <div className="cia-agent-pill" style={{ padding: '4px 10px', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', gap: '6px' }}>
            <span className="cia-dot-live" style={{ width: '5px', height: '5px' }}></span>
            Active Stream
          </div>
        </div>
        
        {/* Output list */}
        <div className="flex-1 overflow-y-auto font-mono text-[11.5px] space-y-2.5 pr-2" style={{ color: 'var(--text-secondary)' }}>
          {logs.length === 0 ? (
            <div style={{ color: 'var(--text-tertiary)' }} className="italic h-full flex items-center justify-center font-body">
              Waiting for discovery server connection...
            </div>
          ) : (
            logs.map((log, idx) => (
              <div key={idx} className="flex gap-3 leading-relaxed">
                <span style={{ color: 'var(--text-tertiary)' }} className="shrink-0 select-none">[{log.timestamp}]</span>
                <span
                  style={{
                    color: log.type.includes("qualified") && !log.type.includes("disqualified")
                      ? 'var(--success)'
                      : log.type.includes("disqualified")
                      ? 'var(--text-tertiary)'
                      : log.type === "error" || log.type === "failed"
                      ? '#ef4444'
                      : 'var(--text-primary)',
                    fontWeight: log.type.includes("qualified") || log.type === "error" ? 600 : 400
                  }}
                >
                  {log.message}
                </span>
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}
