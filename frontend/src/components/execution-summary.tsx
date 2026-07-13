"use client";

import React from "react";
import { CheckCircle2, XCircle, Search, Clock, Award } from "lucide-react";

interface SummaryData {
  started_at: string;
  finished_at: string;
  total_processed: number;
  qualified_count: number;
  disqualified_count: number;
  duration: string;
  errors?: string;
}

interface ExecutionSummaryProps {
  summary: SummaryData;
  searchId: string;
}

export default function ExecutionSummary({ summary, searchId }: ExecutionSummaryProps) {
  const cards = [
    {
      label: "Total Websites Scanned",
      value: summary.total_processed,
      icon: <Search className="text-blue-400" size={20} />,
      bg: "bg-blue-500/5 border-blue-500/10"
    },
    {
      label: "Qualified Companies",
      value: summary.qualified_count,
      icon: <CheckCircle2 className="text-emerald-400" size={20} />,
      bg: "bg-emerald-500/5 border-emerald-500/10"
    },
    {
      label: "Disqualified Companies",
      value: summary.disqualified_count,
      icon: <XCircle className="text-zinc-500" size={20} />,
      bg: "bg-zinc-800/10 border-white/5"
    },
    {
      label: "Execution Duration",
      value: summary.duration,
      icon: <Clock className="text-purple-400" size={20} />,
      bg: "bg-purple-500/5 border-purple-500/10"
    }
  ];

  return (
    <div className="w-full max-w-4xl mx-auto space-y-4 animate-fade-in">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 glass-panel rounded-xl border border-white/5 bg-black/10">
        <div>
          <h3 className="text-sm font-semibold text-zinc-300">Execution Report</h3>
          <p className="text-[10px] text-zinc-500 font-mono mt-0.5">Search ID: {searchId}</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-zinc-400 font-mono">
          <span>Started: {summary.started_at ? new Date(summary.started_at).toLocaleTimeString() : "N/A"}</span>
          <span className="text-zinc-700">|</span>
          <span>Finished: {summary.finished_at ? new Date(summary.finished_at).toLocaleTimeString() : "N/A"}</span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map((card, index) => (
          <div key={index} className={`p-5 rounded-2xl border flex flex-col justify-between ${card.bg} shadow-md`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-zinc-400 font-medium">{card.label}</span>
              {card.icon}
            </div>
            <div className="text-2xl font-bold text-zinc-100 tracking-tight">{card.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
