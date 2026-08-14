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
  recruitly_status?: "EXISTS" | "FRESH";
  recruitly_id?: string;
  bypass_used?: string;
  existing_contacts?: any[];
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

  const handleExportExcel = async () => {
    if (displayList.length === 0) return;

    // Dynamically import exceljs and file-saver
    const ExcelJS = (await import('exceljs')).default;
    const { saveAs } = (await import('file-saver')).default || await import('file-saver');

    const workbook = new ExcelJS.Workbook();
    
    // --- SHEET 1: COMPANIES ---
    const companiesSheet = workbook.addWorksheet('Companies');
    companiesSheet.columns = [
      { header: 'Company Name', key: 'company_name', width: 25 },
      { header: 'Website', key: 'website', width: 30 },
      { header: 'CRM Status', key: 'crm_status', width: 15 },
      { header: 'Reason', key: 'reason', width: 60 }
    ];

    // Style Companies header
    companiesSheet.getRow(1).font = { bold: true, color: { argb: 'FFFFFFFF' } };
    companiesSheet.getRow(1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF333333' } };

    displayList.forEach((c, index) => {
      const row = companiesSheet.addRow({
        company_name: c.company_name,
        website: c.website,
        crm_status: activeTab === "qualified" ? (c.recruitly_id || "Add Company") : "N/A",
        reason: c.qualification.reason
      });
      // Alternating row colors
      if (index % 2 === 1) {
        row.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF2F2F2' } };
      }
    });

    // --- SHEET 2: CONTACTS ---
    const contactsSheet = workbook.addWorksheet('Contacts');
    contactsSheet.columns = [
      { header: 'Company Name', key: 'company_name', width: 25 },
      { header: 'Contact Name', key: 'contact_name', width: 25 },
      { header: 'Job Title', key: 'job_title', width: 35 },
      { header: 'LinkedIn', key: 'linkedin', width: 40 },
      { header: 'Reference ID', key: 'reference_id', width: 15 },
      { header: 'CRM URL', key: 'crm_url', width: 40 }
    ];

    // Style Contacts header
    contactsSheet.getRow(1).font = { bold: true, color: { argb: 'FFFFFFFF' } };
    contactsSheet.getRow(1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF333333' } };

    // Group contacts by company with alternating colors (white and grey)
    const colors = ['FFFFFFFF', 'FFF2F2F2']; 
    let colorIndex = 0;

    displayList.forEach(c => {
      if (c.existing_contacts && c.existing_contacts.length > 0) {
        const rowColor = colors[colorIndex % 2];
        
        c.existing_contacts.forEach(contact => {
          const row = contactsSheet.addRow({
            company_name: c.company_name,
            contact_name: contact.name || "",
            job_title: contact.job_title || "",
            linkedin: contact.linkedin || "",
            reference_id: contact.reference_id || "",
            crm_url: contact.crm_url || ""
          });
          
          row.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: rowColor } };
        });
        colorIndex++;
      }
    });

    // Generate Excel file
    const buffer = await workbook.xlsx.writeBuffer();
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    saveAs(blob, `company_results_${activeTab}.xlsx`);
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
            onClick={handleExportExcel}
            disabled={displayList.length === 0}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-white/5 hover:bg-white/10 text-zinc-300 rounded-lg transition-colors border border-white/10 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download size={14} />
            Export Excel
          </button>
        </div>
      </div>

      <div className="relative w-full">
        {/* Main List Table */}
        <div className="glass-panel rounded-2xl overflow-hidden shadow-2xl border border-white/5 bg-zinc-950/40 backdrop-blur-md transition-all duration-300">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/5 bg-white/5 text-[11px] text-zinc-500 uppercase tracking-wider">
                  <th className="px-4 py-3 font-semibold">Company Name</th>
                  <th className="px-4 py-3 font-semibold">Website</th>
                  {activeTab === "qualified" && (
                    <th className="px-4 py-3 font-semibold text-center">Confidence</th>
                  )}
                  {activeTab === "qualified" && (
                    <th className="px-4 py-3 font-semibold text-center">CRM Status</th>
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
                      className={`group transition-all duration-200 cursor-pointer ${
                        selectedCompany?.company_name === company.company_name 
                          ? "bg-blue-900/10 border-l-2 border-blue-500 shadow-inner" 
                          : "hover:bg-white/[0.03] border-l-2 border-transparent"
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
                      {activeTab === "qualified" && (
                        <td className="px-4 py-4.5 text-center">
                          {company.recruitly_status === "EXISTS" ? (
                            <span className="px-2.5 py-1 rounded bg-green-500/10 text-green-400 text-xs font-mono font-bold border border-green-500/20">
                              {company.recruitly_id}
                            </span>
                          ) : company.recruitly_status === "FRESH" ? (
                            <button className="px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-semibold shadow-sm transition-colors"
                              onClick={(e) => {
                                e.stopPropagation();
                                console.log("Add Company clicked - Phase 2.1 UI only!");
                              }}>
                              Add Company
                            </button>
                          ) : (
                            <span className="text-zinc-500 text-xs flex items-center justify-center h-full animate-pulse">...</span>
                          )}
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
      </div>

      {/* Slide-Out Details Drawer (Overlay) */}
      <div 
        className={`fixed inset-0 z-[100] transition-opacity duration-300 ${selectedCompany ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
      >
        <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setSelectedCompany(null)} />
        
        <div className={`absolute top-0 right-0 h-full w-full max-w-md bg-zinc-950/95 border-l border-white/10 shadow-2xl transform transition-transform duration-300 ease-out overflow-y-auto ${selectedCompany ? 'translate-x-0' : 'translate-x-full'}`}>
          {selectedCompany && (
            <div className="p-8 space-y-8 relative h-full">
              {/* Close Button */}
              <button
                onClick={() => setSelectedCompany(null)}
                className="absolute top-6 right-6 p-2 rounded-full text-zinc-400 hover:text-white hover:bg-white/10 transition-all focus:outline-none focus:ring-2 focus:ring-white/20"
              >
                <X size={20} />
              </button>

              <div className="space-y-2 pr-12 border-b border-white/5 pb-6">
                <h3 className="text-2xl font-bold text-white tracking-tight">{selectedCompany.company_name}</h3>
                <a
                  href={selectedCompany.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-400 hover:text-blue-300 hover:underline inline-flex items-center gap-1.5 transition-colors"
                >
                  <span className="font-medium">Visit official website</span>
                  <ExternalLink size={12} />
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
              {/* CRM Status Box */}
              {activeTab === "qualified" && selectedCompany.recruitly_status && (
                <div className="mt-8 p-4 bg-gradient-to-r from-blue-900/20 to-purple-900/20 border border-blue-500/20 rounded-xl flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-white">CRM Integration</h4>
                    <p className="text-xs text-blue-200/60 mt-1">Status in Recruitly database</p>
                  </div>
                  <div>
                    {selectedCompany.recruitly_status === "EXISTS" ? (
                       <span className="px-3 py-1.5 rounded bg-emerald-500/20 text-emerald-400 text-sm font-mono font-bold border border-emerald-500/30 shadow-inner">
                        {selectedCompany.recruitly_id}
                      </span>
                    ) : (
                      <button className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold shadow-md shadow-blue-900/20 transition-all hover:scale-105 active:scale-95"
                        onClick={(e) => {
                          e.stopPropagation();
                          console.log("Add Company clicked - UI ONLY Phase 2.2");
                        }}>
                        Add to Recruitly
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Existing Contacts */}
              {selectedCompany.existing_contacts && selectedCompany.existing_contacts.length > 0 && (
                <div className="space-y-3 mt-6">
                  <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Existing Contacts in CRM ({selectedCompany.existing_contacts.length})</h4>
                  <div className="max-h-64 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                    {selectedCompany.existing_contacts.map((contact, i) => (
                      <div key={i} className="p-3 bg-white/5 rounded-lg border border-white/5 hover:border-white/10 transition-colors">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="font-semibold text-zinc-200 text-sm">{contact.name}</div>
                            <div className="text-xs text-zinc-400 mt-0.5">{contact.job_title}</div>
                            {contact.last_contacted && (
                              <div className="text-[10px] text-zinc-500 mt-1 flex items-center gap-1">
                                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                                Last Contacted: {contact.last_contacted}
                              </div>
                            )}
                          </div>
                          <div className="flex gap-2">
                            {contact.linkedin && (
                              <a href={contact.linkedin} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 transition-colors" title="LinkedIn Profile">
                                <span className="text-[10px] uppercase font-bold border border-blue-400/30 px-1.5 py-0.5 rounded bg-blue-400/10">IN</span>
                              </a>
                            )}
                            {contact.crm_url && (
                              <a href={contact.crm_url} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:text-emerald-300 transition-colors" title="Open in CRM">
                                <span className="text-[10px] uppercase font-bold border border-emerald-400/30 px-1.5 py-0.5 rounded bg-emerald-400/10">CRM</span>
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>
          )}
        </div>
      </div>
    </div>
  );
}
