"use client";

import React, { useState } from "react";

export interface Company {
  company_name: string;
  website_url: string;
  is_match: boolean;
  confidence_score: number;
  reasoning: string;
}

interface ResultsTableProps {
  qualifiedCompanies: Company[];
  disqualifiedCompanies: Company[];
  summary: any;
}

export default function ResultsTable({ qualifiedCompanies, disqualifiedCompanies, summary }: ResultsTableProps) {
  const [activeTab, setActiveTab] = useState<"qualified" | "disqualified">("qualified");
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const displayList = activeTab === "qualified" ? qualifiedCompanies : disqualifiedCompanies;
  const totalScanned = qualifiedCompanies.length + disqualifiedCompanies.length;
  const blockedCount = summary?.blocked_count || 0;
  const durationStr = summary?.duration_seconds ? `${summary.duration_seconds.toFixed(1)}s` : "N/A";

  const getConfBadge = (score: number) => {
    if (score >= 80) return "high";
    if (score >= 50) return "mid";
    return "low";
  };

  return (
    <>
      <div className="stat-row">
        <div className="stat-card">
          <div className="stat-top"><span>Total Scanned</span><div className="stat-icon gd"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg></div></div>
          <div className="num">{totalScanned}</div>
        </div>
        <div className="stat-card">
          <div className="stat-top"><span>Qualified</span><div className="stat-icon g"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 6L9 17l-5-5"/></svg></div></div>
          <div className="num" style={{ color: 'var(--success)' }}>{qualifiedCompanies.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-top"><span>Disqualified</span><div className="stat-icon r"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg></div></div>
          <div className="num" style={{ color: 'var(--danger)' }}>{disqualifiedCompanies.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-top"><span>Blocked / Bot</span><div className="stat-icon a"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg></div></div>
          <div className="num" style={{ color: 'var(--warning)' }}>{blockedCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-top"><span>Duration</span><div className="stat-icon v"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg></div></div>
          <div className="num">{durationStr}</div>
        </div>
      </div>

      <div className="tabs-row">
        <div className="tabs">
          <div 
            className={`tab ${activeTab === "qualified" ? 'active' : ''}`}
            onClick={() => setActiveTab("qualified")}
          >
            Qualified <span className="n">({qualifiedCompanies.length})</span>
          </div>
          <div 
            className={`tab ${activeTab === "disqualified" ? 'active' : ''}`}
            onClick={() => setActiveTab("disqualified")}
          >
            Disqualified <span className="n">({disqualifiedCompanies.length})</span>
          </div>
          <div className="tab" style={{ opacity: 0.5, cursor: 'not-allowed' }} title="Coming Soon">
            Blocked <span className="n">({blockedCount})</span>
          </div>
        </div>
        <button className="export-btn" onClick={() => alert("CSV Export coming soon!")}>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 15V3M7 10l5 5 5-5M20 21H4"/></svg>
          Export CSV
        </button>
      </div>

      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Website</th>
            <th>Confidence</th>
            <th>CRM Status</th>
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
              <React.Fragment key={i}>
                <tr onClick={() => setExpandedRow(expandedRow === i ? null : i)}>
                  <td className="company-name">{c.company_name}</td>
                  <td>
                    <a className="website-link" href={c.website_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
                      {c.website_url.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')} ↗
                    </a>
                  </td>
                  <td>
                    <span className={`conf-badge ${getConfBadge(c.confidence_score)}`}>{c.confidence_score}%</span>
                  </td>
                  <td className="crm-cell">
                    <button className="crm-btn" onClick={(e) => { e.stopPropagation(); alert("CRM Sync coming soon!") }}>Add Company</button>
                  </td>
                  <td className="row-expand">{expandedRow === i ? 'v' : '›'}</td>
                </tr>
                {expandedRow === i && (
                  <tr className="reason-row">
                    <td colSpan={5}>
                      <span className="reason-label">WHY {c.is_match ? 'QUALIFIED' : 'DISQUALIFIED'}</span>
                      {c.reasoning}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))
          )}
        </tbody>
      </table>
    </>
  );
}
