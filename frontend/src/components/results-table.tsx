"use client";

import React, { useState } from "react";
import * as ExcelJS from "exceljs";
import { saveAs } from "file-saver";

export interface Company {
  company_name: string;
  website: string;
  qualification?: {
    confidence: number;
    reason: string;
    qualified: boolean;
  };
  is_match?: boolean;
  confidence_score?: number;
  reasoning?: string;
  recruitly_status?: string;
  recruitly_id?: string;
  existing_contacts?: any[];
}

interface ResultsTableProps {
  qualifiedCompanies: Company[];
  disqualifiedCompanies: Company[];
  blockedCompanies: Company[];
  summary: any;
}

export default function ResultsTable({ qualifiedCompanies, disqualifiedCompanies, blockedCompanies, summary }: ResultsTableProps) {
  const [activeTab, setActiveTab] = useState<"qualified" | "disqualified" | "blocked">("qualified");
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  
  const tabsRef = React.useRef<(HTMLDivElement | null)[]>([]);
  const [indicatorStyle, setIndicatorStyle] = useState({ left: 4, width: 0 });

  React.useEffect(() => {
    const tabIndex = activeTab === "qualified" ? 0 : activeTab === "disqualified" ? 1 : 2;
    const el = tabsRef.current[tabIndex];
    if (el) {
      setIndicatorStyle({
        left: el.offsetLeft,
        width: el.offsetWidth
      });
    }
  }, [activeTab, qualifiedCompanies.length, disqualifiedCompanies.length, blockedCompanies.length]);

  const displayList = activeTab === "qualified" ? qualifiedCompanies : activeTab === "disqualified" ? disqualifiedCompanies : blockedCompanies;
  const totalScanned = qualifiedCompanies.length + disqualifiedCompanies.length + blockedCompanies.length;
  const blockedCount = blockedCompanies.length;
  const durationStr = summary?.duration || "N/A";

  const getConfBadge = (score: number) => {
    if (score >= 80) return "high";
    if (score >= 50) return "mid";
    return "low";
  };

  const exportToExcel = async () => {
    if (displayList.length === 0) return;
    
    const workbook = new ExcelJS.Workbook();
    
    // Sheet 1: Companies
    const companySheet = workbook.addWorksheet("Companies");
    const companyColumns: any[] = [
      { header: "Company Name", key: "name", width: 30 },
      { header: "Website", key: "website", width: 30 }
    ];

    if (activeTab === "qualified") {
      companyColumns.push({ header: "CRM Status", key: "crm_status", width: 15 });
    }
    
    companyColumns.push({ header: "Reason", key: "reason", width: 60 });
    
    companySheet.columns = companyColumns;
    
    // Sheet 2: Contacts
    const contactSheet = workbook.addWorksheet("Contacts");
    contactSheet.columns = [
      { header: "Company Name", key: "company", width: 30 },
      { header: "Contact Name", key: "name", width: 25 },
      { header: "Job Title", key: "title", width: 30 },
      { header: "LinkedIn", key: "linkedin", width: 35 },
      { header: "Reference ID", key: "ref", width: 15 },
      { header: "CRM URL", key: "crm_url", width: 50 },
      { header: "Last Contacted", key: "last_contacted", width: 20 }
    ];
    
    // Styling headers (black)
    [companySheet, contactSheet].forEach(sheet => {
      sheet.getRow(1).font = { bold: true, color: { argb: "FFFFFFFF" } };
      sheet.getRow(1).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF333333" } };
    });

    displayList.forEach(c => {
      // Add Company Row
      const rowData: any = {
        name: c.company_name || "",
        website: c.website || "",
        reason: c.qualification?.reason || c.reasoning || ""
      };

      if (activeTab === "qualified") {
        rowData.crm_status = c.recruitly_status === "EXISTS" ? (c.recruitly_id || "EXISTS") : "Add Company";
      }

      const compRow = companySheet.addRow(rowData);
      
      // Style Website as link
      if (c.website) {
        compRow.getCell("website").font = { color: { argb: "FF0563C1" }, underline: true };
      }

      // Add Contact Rows
      if (c.existing_contacts && c.existing_contacts.length > 0) {
        c.existing_contacts.forEach((contact: any) => {
          const contRow = contactSheet.addRow({
            company: c.company_name || "",
            name: contact.name || "",
            title: contact.job_title || "",
            linkedin: contact.linkedin || "",
            ref: contact.reference_id || "",
            crm_url: contact.crm_url || "",
            last_contacted: contact.last_contacted ? (contact.last_contacted.toUpperCase() === "NEVER" ? "NEVER" : contact.last_contacted) : "NEVER"
          });
          
          // Style links
          if (contact.linkedin) {
            contRow.getCell("linkedin").font = { color: { argb: "FF0563C1" }, underline: true };
          }
          if (contact.crm_url) {
            contRow.getCell("crm_url").font = { color: { argb: "FF0563C1" }, underline: true };
          }
        });
      }
    });

    const buffer = await workbook.xlsx.writeBuffer();
    saveAs(new Blob([buffer]), `${activeTab}_companies_export.xlsx`);
  };

  return (
    <>
      {summary && (
        <div style={{
          background: 'rgba(62,214,160,0.1)', border: '1px solid var(--success)', 
          color: 'var(--success)', padding: '12px 20px', borderRadius: '12px', 
          marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px',
          fontWeight: 500, fontSize: '14px', animation: 'slideIn 0.3s ease'
        }}>
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>
          Search Completed Successfully — Processed {summary.total_processed} companies in {durationStr}.
        </div>
      )}
      <div className="stat-row">
        <div className="stat-card">
          <div className="stat-top"><span>Total Scanned</span><div className="stat-icon gd"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg></div></div>
          <div className="num">{totalScanned}</div>
          <div className="stat-spark"><svg viewBox="0 0 100 26" preserveAspectRatio="none"><polyline points="0,20 15,17 30,18 45,12 60,13 75,7 90,8 100,4" fill="none" stroke="var(--accent-gold)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg></div>
        </div>
        <div className="stat-card">
          <div className="stat-top"><span>Qualified</span><div className="stat-icon g"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 6L9 17l-5-5"/></svg></div></div>
          <div className="num" style={{ color: 'var(--success)' }}>{qualifiedCompanies.length}</div>
          <div className="stat-spark"><svg viewBox="0 0 100 26" preserveAspectRatio="none"><polyline points="0,22 20,20 40,15 55,16 70,9 85,10 100,3" fill="none" stroke="var(--success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg></div>
        </div>
        <div className="stat-card">
          <div className="stat-top"><span>Disqualified</span><div className="stat-icon r"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg></div></div>
          <div className="num" style={{ color: 'var(--danger)' }}>{disqualifiedCompanies.length}</div>
          <div className="stat-spark"><svg viewBox="0 0 100 26" preserveAspectRatio="none"><polyline points="0,6 20,10 40,9 55,15 70,14 85,19 100,21" fill="none" stroke="var(--danger)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg></div>
        </div>
        <div className="stat-card">
          <div className="stat-top"><span>Blocked / Bot</span><div className="stat-icon a"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg></div></div>
          <div className="num" style={{ color: 'var(--warning)' }}>{blockedCount}</div>
          <div className="stat-spark"><svg viewBox="0 0 100 26" preserveAspectRatio="none"><polyline points="0,13 100,13" fill="none" stroke="var(--warning)" strokeWidth="2" strokeLinecap="round" strokeDasharray="1 6"/></svg></div>
        </div>
        <div className="stat-card">
          <div className="stat-top"><span>Duration</span><div className="stat-icon v"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg></div></div>
          <div className="num">{durationStr}</div>
          <div className="stat-spark"><svg viewBox="0 0 100 26" preserveAspectRatio="none"><polyline points="0,10 20,14 40,8 55,18 70,11 85,15 100,9" fill="none" stroke="var(--accent-violet)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg></div>
        </div>
      </div>

      <div className="tabs-row">
        <div className="tabs" style={{ position: 'relative' }}>
          <div className="tab-indicator" style={{ 
            position: 'absolute', 
            top: 4, 
            bottom: 4, 
            left: indicatorStyle.left, 
            width: indicatorStyle.width, 
            background: 'var(--accent-gold-soft)', 
            borderRadius: '7px', 
            transition: 'all 0.3s cubic-bezier(0.25, 1, 0.5, 1)',
            zIndex: 0
          }} />
          <div 
            ref={el => { tabsRef.current[0] = el; }}
            className={`tab ${activeTab === "qualified" ? 'active' : ''}`}
            onClick={() => setActiveTab("qualified")}
            style={{ position: 'relative', zIndex: 1, background: 'transparent' }}
          >
            Qualified <span className="n">({qualifiedCompanies.length})</span>
          </div>
          <div 
            ref={el => { tabsRef.current[1] = el; }}
            className={`tab ${activeTab === "disqualified" ? 'active' : ''}`}
            onClick={() => setActiveTab("disqualified")}
            style={{ position: 'relative', zIndex: 1, background: 'transparent' }}
          >
            Disqualified <span className="n">({disqualifiedCompanies.length})</span>
          </div>
          <div 
            ref={el => { tabsRef.current[2] = el; }}
            className={`tab ${activeTab === "blocked" ? 'active' : ''}`}
            onClick={() => setActiveTab("blocked")}
            style={{ position: 'relative', zIndex: 1, background: 'transparent' }}
          >
            Blocked <span className="n">({blockedCount})</span>
          </div>
        </div>
        <button className="export-btn" onClick={exportToExcel}>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 15V3M7 10l5 5 5-5M20 21H4"/></svg>
          Export Excel
        </button>
      </div>

      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Website</th>
            <th>Confidence</th>
            {activeTab === "qualified" && <th>CRM Status</th>}
            <th></th>
          </tr>
        </thead>
        <tbody>
          {displayList.length === 0 ? (
            <tr>
              <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: '30px' }}>
                No companies in this list yet.
              </td>
            </tr>
          ) : (
            displayList.map((c, i) => (
              <tr key={i} onClick={() => setSelectedCompany(c)} className={selectedCompany === c ? 'selected-row' : ''}>
                <td className="company-name">{c.company_name}</td>
                <td>
                  <a className="website-link" href={c.website || "#"} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
                    {c.website ? c.website.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '') : 'No website'} ↗
                  </a>
                </td>
                <td>
                  <span className={`conf-badge ${getConfBadge(c.qualification?.confidence ?? c.confidence_score ?? 0)}`}>
                    {c.qualification?.confidence ?? c.confidence_score ?? 0}%
                  </span>
                </td>
                {activeTab === "qualified" && (
                  <td className="crm-cell">
                    {c.recruitly_status === "EXISTS" ? (
                      <button className="crm-btn existing">{c.recruitly_id || "In CRM"}</button>
                    ) : (
                      <button className="crm-btn new" onClick={(e) => { e.stopPropagation(); alert("CRM Sync coming soon!") }}>Add Company</button>
                    )}
                  </td>
                )}
                <td className="row-expand">›</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {selectedCompany && (
        <>
          <div className="sidebar-backdrop" onClick={() => setSelectedCompany(null)}></div>
          <div className="details-sidebar">
            <div className="ds-header">
              <h3>{selectedCompany.company_name}</h3>
              <button className="ds-close" onClick={() => setSelectedCompany(null)}>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
              </button>
            </div>
            
            <div className="ds-content">
              <a className="ds-website" href={selectedCompany.website} target="_blank" rel="noopener noreferrer">
                Visit official website <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/></svg>
              </a>

              <div className="ds-card ds-score-card">
                <div className="ds-score-left">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="var(--accent-gold)" strokeWidth="2"><circle cx="12" cy="8" r="7"/><path d="M8.21 13.89L7 23l5-3 5 3-1.21-9.12"/></svg>
                  <span>Confidence Score</span>
                </div>
                <div className="ds-score-val">
                  {selectedCompany.qualification?.confidence ?? selectedCompany.confidence_score ?? 0}%
                </div>
              </div>

              <div className="ds-section-label">EVALUATION REASON</div>
              <div className="ds-card ds-reason-card">
                {selectedCompany.qualification?.reason || selectedCompany.reasoning || (activeTab === "blocked" ? "Website blocked our scraper via anti-bot protection." : "No reasoning provided.")}
                {selectedCompany.recruitly_status === "EXISTS" && selectedCompany.recruitly_id && (
                  <span className="ds-inline-id"> [Recruitly ID: {selectedCompany.recruitly_id}]</span>
                )}
              </div>

              <div className="ds-card ds-crm-status">
                <div className="ds-crm-info">
                  <h4>CRM Integration</h4>
                  <p>{selectedCompany.recruitly_status === "EXISTS" ? "Status in Recruitly database" : "Not found in CRM"}</p>
                </div>
                {selectedCompany.recruitly_status === "EXISTS" ? (
                  <div className="ds-crm-badge green">{selectedCompany.recruitly_id}</div>
                ) : (
                  <div className="ds-crm-badge purple" onClick={() => alert("CRM Sync coming soon!")}>Add Company</div>
                )}
              </div>

              {selectedCompany.recruitly_status === "EXISTS" && (
                <>
                  <div className="ds-section-label">
                    EXISTING CONTACTS IN CRM ({selectedCompany.existing_contacts?.length || 0})
                  </div>
                  <div className="ds-contacts-list">
                    {selectedCompany.existing_contacts && selectedCompany.existing_contacts.length > 0 ? (
                      selectedCompany.existing_contacts.map((contact, idx) => (
                        <div key={idx} className="ds-contact-card">
                          <div className="dsc-info">
                            <h5>
                              {contact.name} 
                              {contact.reference_id && <span style={{ color: 'var(--text-tertiary)', fontSize: '11px', fontWeight: 500, marginLeft: '8px', fontFamily: 'var(--mono)' }}>({contact.reference_id})</span>}
                            </h5>
                            <p>{contact.job_title || "No title provided"}</p>
                            <p style={{ marginTop: '6px', fontSize: '11px', color: 'var(--text-tertiary)', fontFamily: 'var(--mono)', letterSpacing: '0.5px' }}>
                              LAST CONTACTED: {contact.last_contacted ? (contact.last_contacted.toUpperCase() === "NEVER" ? "NEVER" : contact.last_contacted) : "NEVER"}
                            </p>
                          </div>
                          <div className="dsc-tags">
                            {contact.linkedin ? (
                              <a href={contact.linkedin} target="_blank" rel="noopener noreferrer" className="dsc-tag linkedin" title="View LinkedIn Profile">IN</a>
                            ) : (
                              <span className="dsc-tag linkedin" style={{opacity: 0.5}} title="No LinkedIn provided">IN</span>
                            )}
                            {contact.crm_url ? (
                              <a href={contact.crm_url} target="_blank" rel="noopener noreferrer" className="dsc-tag crm" title="Open in CRM">CRM</a>
                            ) : (
                              <span className="dsc-tag crm" style={{opacity: 0.5}} title="No CRM link">CRM</span>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="ds-contact-card empty">No contacts found for this company in Recruitly.</div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}
