"use client";

import React, { useState } from "react";
import { ExternalLink, ShieldCheck, ShieldAlert, Award, FileText, ChevronRight, X, Download } from "lucide-react";

export interface Evidence {
  page: string;
  quote: string;
}

export interface Qualification {
  qualified: boolean;
  is_blocked?: boolean;
  reason: string;
  confidence: number;
  evidence: Evidence[];
}

export interface Company {
  company_name: string;
  website: string;
  address?: string;
  phone?: string;
  category?: string;
  qualification: Qualification;
}

interface ResultsTableProps {
  companies: Company[];
}

export default function ResultsTable({ companies }: ResultsTableProps) {
  const [activeTab, setActiveTab] = useState<"qualified" | "disqualified" | "blocked">("qualified");
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);

  const qualifiedList = companies.filter((c) => c.qualification?.qualified === true);
  const blockedList = companies.filter((c) => c.qualification?.is_blocked === true);
  const disqualifiedList = companies.filter((c) => c.qualification?.qualified === false && !c.qualification?.is_blocked);

  const displayList = activeTab === "qualified" ? qualifiedList : activeTab === "blocked" ? blockedList : disqualifiedList;

  const handleExportCSV = () => {
    if (displayList.length === 0) return;

    // Define CSV Headers
    const headers = ["Company Name", "Website", "Status", "Confidence", "Phone", "Address", "Reason"];
    
    // Create CSV Rows
    const rows = displayList.map(c => {
      return [
        `"${c.company_name.replace(/"/g, '""')}"`,
        `"${c.website}"`,
        `"${c.qualification.qualified ? 'Qualified' : 'Disqualified'}"`,
        `"${c.qualification.confidence}%"`,
        `"${c.phone || ''}"`,
        `"${(c.address || '').replace(/"/g, '""')}"`,
        `"${c.qualification.reason.replace(/"/g, '""')}"`
      ].join(",");
    });

    const csvContent = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    
    link.setAttribute("href", url);
    link.setAttribute("download", `company-intelligence-${activeTab}-results.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fade-in relative">
      {/* Tab Selectors & Action Buttons */}
      <div className="flex justify-between border-b border-white/5">
        <div className="flex">

        <button
          onClick={() => {
            setActiveTab("qualified");
            setSelectedCompany(null);
          }}
          className={`px-6 py-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === "qualified"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-zinc-500 hover:text-zinc-300"
          }`}
        >
          <ShieldCheck size={16} />
          <span>Qualified ({qualifiedList.length})</span>
        </button>
        <button
          onClick={() => {
            setActiveTab("disqualified");
            setSelectedCompany(null);
          }}
          className={`px-6 py-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === "disqualified"
              ? "border-zinc-500 text-zinc-400"
              : "border-transparent text-zinc-500 hover:text-zinc-300"
          }`}
        >
          <ShieldAlert size={16} />
          <span>Disqualified ({disqualifiedList.length})</span>
        </button>
        <button
          onClick={() => {
            setActiveTab("blocked");
            setSelectedCompany(null);
          }}
          className={`px-6 py-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === "blocked"
              ? "border-orange-500 text-orange-400"
              : "border-transparent text-zinc-500 hover:text-zinc-300"
          }`}
        >
          <ShieldAlert size={16} />
          <span>Blocked ({blockedList.length})</span>
        </button>
        </div>
        
        {/* Export Button */}
        <div className="flex items-center px-4">
          <button 
            onClick={handleExportCSV}
            disabled={displayList.length === 0}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-white/5 hover:bg-white/10 text-zinc-300 rounded-lg transition-colors border border-white/10 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download size={14} />
            Export CSV
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main List Table */}
        <div className={`lg:col-span-2 glass-panel rounded-2xl overflow-hidden shadow-xl border border-white/5`}>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/5 bg-white/5 text-[11px] text-zinc-500 uppercase tracking-wider">
                  <th className="px-4 py-3 font-semibold">Company Name</th>
                  <th className="px-4 py-3 font-semibold">Website</th>
                  {activeTab === "qualified" && (
                    <th className="px-4 py-3 font-semibold text-center">Confidence</th>
                  )}
                  <th className="px-4 py-3 font-semibold"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-sm text-zinc-300">
                {displayList.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-zinc-500 italic">
                      No companies match this category.
                    </td>
                  </tr>
                ) : (
                  displayList.map((company, idx) => (
                    <tr
                      key={idx}
                      onClick={() => setSelectedCompany(company)}
                      className={`hover:bg-white/[0.02] transition-colors cursor-pointer ${
                        selectedCompany?.company_name === company.company_name ? "bg-white/[0.03]" : ""
                      }`}
                    >
                      <td className="px-4 py-4.5 font-medium text-zinc-200">
                        {company.company_name}
                      </td>
                      <td className="px-4 py-4.5">
                        <a
                          href={company.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-blue-400 hover:underline flex items-center gap-1 text-xs"
                        >
                          <span className="max-w-[120px] truncate block">{company.website.replace("https://", "").replace("www.", "")}</span>
                          <ExternalLink size={10} />
                        </a>
                      </td>
                      {activeTab === "qualified" && (
                        <td className="px-4 py-4.5 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs font-mono font-medium ${
                            company.qualification.confidence >= 90
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : company.qualification.confidence >= 70
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                              : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                          }`}>
                            {company.qualification.confidence}%
                          </span>
                        </td>
                      )}
                      <td className="px-4 py-4.5 text-right">
                        <ChevronRight size={16} className="text-zinc-600 inline" />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Floating Details Drawer Side Panel */}
        <div className="lg:col-span-1">
          {selectedCompany ? (
            <div className="glass-panel rounded-2xl p-5 border border-white/10 bg-zinc-950/40 space-y-5 shadow-2xl relative animate-slide-in">
              <button
                onClick={() => setSelectedCompany(null)}
                className="absolute top-4 right-4 p-1 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-white/5 transition-all"
              >
                <X size={16} />
              </button>

              <div className="space-y-1 pr-12">
                <h3 className="text-lg font-bold text-zinc-100 break-words">{selectedCompany.company_name}</h3>
                <a
                  href={selectedCompany.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-400 hover:underline inline-flex items-center gap-1"
                >
                  <span>Visit website</span>
                  <ExternalLink size={10} />
                </a>
              </div>

              {/* Confidence Meter */}
              {selectedCompany.qualification.qualified && (
                <div className="p-3 bg-white/5 rounded-xl border border-white/5 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Award className="text-amber-400" size={16} />
                    <span className="text-xs text-zinc-400 font-medium">Confidence Score</span>
                  </div>
                  <span className="text-sm font-bold text-zinc-200">{selectedCompany.qualification.confidence}%</span>
                </div>
              )}

              {/* Company Info */}
              {(selectedCompany.address || selectedCompany.phone) && (
                <div className="space-y-2 text-xs text-zinc-400 bg-white/5 p-3 rounded-xl border border-white/5">
                  {selectedCompany.address && (
                    <div>
                      <span className="text-zinc-600 font-mono">ADDRESS:</span> {selectedCompany.address}
                    </div>
                  )}
                  {selectedCompany.phone && (
                    <div>
                      <span className="text-zinc-600 font-mono">PHONE:</span> {selectedCompany.phone}
                    </div>
                  )}
                </div>
              )}

              {/* Why Qualification Reason */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Evaluation Reason</h4>
                <p className="text-xs leading-relaxed text-zinc-300 bg-zinc-900/50 p-3 rounded-xl border border-white/5">
                  {selectedCompany.qualification.reason}
                </p>
              </div>

              {/* Evidence Quotes */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Evidence Quotes</h4>
                <div className="space-y-3">
                  {selectedCompany.qualification.evidence.length === 0 ? (
                    <p className="text-xs text-zinc-600 italic">No exact evidence quotes captured.</p>
                  ) : (
                    selectedCompany.qualification.evidence.map((ev, idx) => (
                      <div key={idx} className="space-y-1.5 p-3 bg-blue-950/10 border border-blue-500/10 rounded-xl">
                        <div className="flex items-center gap-1 text-[10px] text-blue-400 font-mono">
                          <FileText size={10} />
                          <span>Source: {ev.page}</span>
                        </div>
                        <p className="text-[11px] leading-relaxed text-zinc-300 italic">
                          &ldquo;{ev.quote}&rdquo;
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[250px] border border-dashed border-white/5 rounded-2xl flex flex-col items-center justify-center text-center p-6 text-zinc-600">
              <ChevronRight className="rotate-90 lg:rotate-0 mb-1" size={24} />
              <p className="text-xs">Select a company from the list to view qualification reasoning and evidence quotes.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
