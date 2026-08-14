"use client";

import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from 'react-markdown';

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ExtractedData {
  company_type?: string;
  product_or_service?: string;
  location?: string;
  current_employer?: string | null;
}

interface ChatInterfaceProps {
  onDiscoveryStart: (criteria: { company_type: string; product_or_service: string; location: string; current_employer?: string | null }) => void;
}

const FileUploadZone = ({ label, required, file, setFile, id }: any) => {
  const [isDragging, setIsDragging] = useState(false);
  
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };
  
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  };
  
  return (
    <div style={{ marginBottom: '16px' }}>
      <label style={{ display: 'block', fontSize: '13px', color: '#8b8d98', marginBottom: '8px', fontWeight: 500 }}>
        {label} {required && <span style={{ color: '#ef4444' }}>*</span>}
      </label>
      <div 
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => document.getElementById(id)?.click()}
        style={{
          border: `2px dashed ${isDragging ? '#52d68a' : '#232533'}`,
          borderRadius: '12px',
          padding: '24px 16px',
          textAlign: 'center',
          backgroundColor: isDragging ? 'rgba(82, 214, 138, 0.05)' : '#13141c',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px'
        }}
      >
        <input 
          id={id}
          type="file" 
          accept=".pdf,.docx,.doc" 
          onChange={e => setFile(e.target.files?.[0] || null)} 
          style={{ display: 'none' }} 
          required={required && !file}
        />
        {file ? (
          <>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" stroke="#52d68a" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="#52d68a" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
            <div style={{ fontSize: '13px', color: '#fff', fontWeight: 500, wordBreak: 'break-all' }}>{file.name}</div>
            <div style={{ fontSize: '11px', color: '#52d68a' }}>Click or drag to replace</div>
          </>
        ) : (
          <>
            <div style={{ background: '#1c1e29', padding: '10px', borderRadius: '50%' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke="#8b8d98" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </div>
            <div style={{ fontSize: '13px', color: '#8b8d98' }}>
              <span style={{ color: '#fff', fontWeight: 500 }}>Click to upload</span> or drag and drop
            </div>
            <div style={{ fontSize: '11px', color: '#565869' }}>PDF or DOCX (max. 10MB)</div>
          </>
        )}
      </div>
    </div>
  );
};

export default function ChatInterface({ onDiscoveryStart }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Welcome to Company Intelligence AI.\nPlease upload the Candidate CV, Supporting Documents, and provide the Current Employer URL to begin Auto-Detect classification.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  
  // File Upload State
  const [employerUrl, setEmployerUrl] = useState("");
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [supportFile, setSupportFile] = useState<File | null>(null);
  
  const [extractedData, setExtractedData] = useState<ExtractedData>({});
  const [isReady, setIsReady] = useState(false);
  const [hasUploaded, setHasUploaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cvFile && !employerUrl) return;

    setIsTyping(true);
    setHasUploaded(true);
    
    // Add user message indicating upload
    setMessages(prev => [...prev, { role: "user", content: "Uploaded documents for analysis." }]);

    try {
      const formData = new FormData();
      formData.append("employer_url", employerUrl);
      if (cvFile) formData.append("cv_file", cvFile);
      if (supportFile) formData.append("support_file", supportFile);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000/api" : "https://company-intelligence-backend.onrender.com/api");
      
      const res = await fetch(`${apiUrl}/auto-detect`, {
        method: "POST",
        body: formData,
      });
      
      if (!res.ok) throw new Error("Auto-detect failed");
      const data = await res.json();
      
      const c = data.classification;
      const rationale = data.rationale;
      const loc = data.location;
      
      setExtractedData({
        company_type: c.sector,
        product_or_service: c.product_focus || c.subsector,
        location: loc,
        current_employer: employerUrl
      });
      
      const aiReply = `I have analyzed the documents and website. Here is my proposed classification:\n\n- **Sector**: ${c.sector || 'None'}\n- **Subsector**: ${c.subsector || 'None'}\n- **Solution Type**: ${c.solution_type || 'None'}\n- **Location**: ${loc || 'UK'}\n\n**Rationale**: ${rationale}\n\nDoes this look correct? Please type **Yes** to confirm, or provide your edits below.`;
      
      setMessages(prev => [...prev, { role: "assistant", content: aiReply }]);
      
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I encountered an error during analysis. Please try again." }]);
      setHasUploaded(false);
    } finally {
      setIsTyping(false);
    }
  };

  const submitChatMessage = async (userMessage: string) => {
    if (!userMessage.trim() || isTyping) return;
    setInput("");
    const newMessages = [...messages, { role: "user", content: userMessage } as Message];
    setMessages(newMessages);
    
    // Simple logic: if user says yes, we are ready. Otherwise, pass to chat.
    if (userMessage.toLowerCase().trim() === "yes" || userMessage.toLowerCase().trim() === "confirm") {
      setIsReady(true);
      setMessages(prev => [...prev, { role: "assistant", content: "Great! Classification confirmed. Click 'Launch Discovery Engine' to begin." }]);
      return;
    }
    
    setIsTyping(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000/api" : "https://company-intelligence-backend.onrender.com/api");
      const res = await fetch(`${apiUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: newMessages }),
      });
      const data = await res.json();
      
      setMessages(prev => [...prev, { role: "assistant", content: data.content }]);
      
      if (data.extracted_data) {
        setExtractedData(prev => ({ ...prev, ...data.extracted_data }));
      }
      if (data.ready) {
        setIsReady(true);
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: "assistant", content: "Error connecting to AI. Please try again." }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleTriggerDiscovery = () => {
    if (extractedData.company_type && extractedData.product_or_service && extractedData.location) {
      onDiscoveryStart({
        company_type: extractedData.company_type,
        product_or_service: extractedData.product_or_service,
        location: extractedData.location,
        current_employer: extractedData.current_employer
      });
    }
  };

  return (
    <div style={{ padding: '28px' }}>
      <div className="cia-grid">
        {/* CHAT PANEL */}
        <div className="cia-panel" style={{ display: 'flex', flexDirection: 'column', maxHeight: '80vh' }}>
          <div className="cia-chat-head">
            <div className="cia-chat-head-left">
              <span className="cia-live-dot"></span> Company Intelligence AI
            </div>
            <div className="cia-version">PLATFORM v2.0 (Auto-Detect)</div>
          </div>

          <div className="cia-thread" style={{ flex: 1, overflowY: 'auto' }}>
            {messages.map((msg, idx) => (
              <div key={idx} className={`cia-msg-row ${msg.role === "user" ? "user-msg" : ""}`}>
                <div className={`cia-avatar ${msg.role === "assistant" ? "cia-avatar-bot" : "cia-avatar-user"}`}>
                  {msg.role === "assistant" ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" stroke="#fff" strokeWidth="1.6" strokeLinecap="round"/></svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" stroke="#edeef3" strokeWidth="1.6" strokeLinecap="round"/></svg>
                  )}
                </div>
                <div className="cia-bubble" style={{ whiteSpace: "normal" }}>
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              </div>
            ))}
            
            {isTyping && (
              <div className="cia-msg-row">
                <div className="cia-avatar cia-avatar-bot">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" stroke="#fff" strokeWidth="1.6" strokeLinecap="round"/></svg>
                </div>
                <div className="cia-bubble">
                  <p className="cia-muted" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ animation: 'sweep 2s linear infinite' }}><path d="M12 3L14.5 9.5L21 12L14.5 14.5L12 21L9.5 14.5L3 12L9.5 9.5L12 3Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/></svg>
                    Analyzing documents...
                  </p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="cia-input-wrap">
            <form className="cia-input-bar" onSubmit={(e) => { e.preventDefault(); submitChatMessage(input); }}>
              <input 
                type="text" 
                placeholder="Confirm with 'Yes' or provide edits…" 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isTyping || !hasUploaded}
              />
              <button className="cia-send-btn" type="submit" disabled={isTyping || !input.trim() || !hasUploaded}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M4 12L20 4L14 20L11 13L4 12Z" fill="#0a0b10"/></svg>
              </button>
            </form>
          </div>
        </div>

        {/* SIDEBAR: FILE UPLOADS & STATUS */}
        <div className="cia-panel" style={{ maxHeight: '80vh', overflowY: 'auto' }}>
          <div className="cia-side-inner">
            
            <div className="cia-section-title" style={{ marginBottom: '14px', fontSize: '18px', color: '#fff' }}>Phase 0: Auto-Detect</div>
            
            {!hasUploaded ? (
              <form onSubmit={handleFileUpload} style={{ display: 'flex', flexDirection: 'column', background: '#0a0b10', padding: '16px', borderRadius: '12px', border: '1px solid #232533' }}>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '13px', color: '#8b8d98', marginBottom: '8px', fontWeight: 500 }}>Current Employer (Name or URL) <span style={{ color: '#ef4444' }}>*</span></label>
                  <input type="text" value={employerUrl} onChange={e => setEmployerUrl(e.target.value)} placeholder="e.g. Shipnet or https://shipnet.no" style={{ width: '100%', padding: '12px', background: '#13141c', border: '1px solid #232533', borderRadius: '8px', color: '#fff', outline: 'none', transition: 'border-color 0.2s' }} required />
                </div>
                
                <FileUploadZone label="Candidate CV (PDF/Docx)" required={true} file={cvFile} setFile={setCvFile} id="cv-upload" />
                <FileUploadZone label="Supporting Doc (FIR/EC Notes)" required={false} file={supportFile} setFile={setSupportFile} id="support-upload" />
                
                <button type="submit" style={{ background: '#52d68a', color: '#0a0b10', padding: '12px', borderRadius: '8px', fontWeight: 'bold', border: 'none', cursor: 'pointer', marginTop: '8px', transition: 'opacity 0.2s' }} disabled={isTyping} onMouseOver={(e) => e.currentTarget.style.opacity = '0.9'} onMouseOut={(e) => e.currentTarget.style.opacity = '1'}>
                  {isTyping ? 'Analyzing...' : 'Submit for Analysis'}
                </button>
              </form>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div className="cia-req-card completed">
                  <div className="cia-req-top">
                    <div className="cia-req-label">Sector / Subsector</div>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17l-5-5" stroke="#52d68a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </div>
                  <div className="cia-req-completed-text">{extractedData.company_type || 'None'}</div>
                </div>
                
                <div className="cia-req-card completed">
                  <div className="cia-req-top">
                    <div className="cia-req-label">Product Focus</div>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17l-5-5" stroke="#52d68a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </div>
                  <div className="cia-req-completed-text">{extractedData.product_or_service || 'None'}</div>
                </div>
              </div>
            )}

            {isReady ? (
              <button className="cia-launch-btn" onClick={handleTriggerDiscovery} style={{ marginTop: '24px' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M5 3l14 9-14 9V3z" fill="currentColor"/></svg>
                Launch Discovery Engine
              </button>
            ) : (
              <div className="cia-hint" style={{ marginTop: '24px' }}>
                Upload the documents to begin Auto-Detect. Confirm the classification in the chat once complete.
              </div>
            )}

            <div style={{ marginTop: '24px' }}>
              <div className="cia-section-title" style={{ marginBottom: '14px' }}>Pipeline Preview</div>
              <div className="cia-pipeline">
                <div className={`cia-step ${!isReady ? 'active' : ''}`}>
                  <div className="cia-step-dot"></div>
                  <div className="cia-step-label">Auto-Detect</div>
                </div>
                <div className={`cia-step ${isReady ? 'active' : ''}`}>
                  <div className="cia-step-dot"></div>
                  <div className="cia-step-label">Search Google</div>
                </div>
                <div className="cia-step">
                  <div className="cia-step-dot"></div>
                  <div className="cia-step-label">AI Analysis</div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
