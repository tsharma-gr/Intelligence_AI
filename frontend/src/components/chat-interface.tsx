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

const FileDropzone = ({ label, required, file, setFile, id, hint }: any) => {
  const [isDragging, setIsDragging] = useState(false);
  
  return (
    <div className="field">
      <label>{label} {required && <span className="req">*</span>}</label>
      <div 
        className="dropzone"
        style={{ borderColor: isDragging ? 'var(--accent-gold)' : undefined, background: isDragging ? 'var(--accent-gold-soft)' : undefined }}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            setFile(e.dataTransfer.files[0]);
          }
        }}
        onClick={() => document.getElementById(id)?.click()}
      >
        <input 
          id={id} type="file" accept=".pdf,.docx,.doc" 
          onChange={e => setFile(e.target.files?.[0] || null)} 
          style={{ display: 'none' }} required={required && !file}
        />
        <div className="dz-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/></svg>
        </div>
        <div className="dz-text">
          {file ? (
            <><b>{file.name}</b><span>{(file.size/1024).toFixed(0)} KB — uploaded</span></>
          ) : (
            <><b>Click to upload</b><span>{hint}</span></>
          )}
        </div>
      </div>
    </div>
  );
};

export default function ChatInterface({ onDiscoveryStart }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Welcome — upload the candidate's **CV**, any supporting notes, and their **current employer** to begin. I'll auto-detect their industry and build a matching company profile.",
    },
    {
      role: "assistant",
      content: "Once I detect the category, I'll show you the profile summary here for confirmation before running the search — you'll always get a chance to correct it."
    }
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

  const handleFileUpload = async () => {
    if (!cvFile && !employerUrl) return;

    setIsTyping(true);
    setHasUploaded(true);
    
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
    
    if (userMessage.toLowerCase().trim() === "yes" || userMessage.toLowerCase().trim() === "confirm" || userMessage.toLowerCase().trim() === "y") {
      setIsReady(true);
      setMessages(prev => [...prev, { role: "assistant", content: "Great! Classification confirmed. Click 'Submit for Analysis' to begin." }]);
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
      if (data.ready) setIsReady(true);
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

  const canUpload = (cvFile || employerUrl) && !hasUploaded && !isTyping;
  const isFormComplete = isReady && extractedData.company_type;

  return (
    <div className="grid">
      {/* CHAT PANEL */}
      <div className="panel">
        <div className="panel-head">
          <div className="panel-title"><span className="live-dot"></span>Company Intelligence AI</div>
          <div className="pill">v2.0 · AUTO-DETECT</div>
        </div>
        <div className="chat-body">
          {messages.map((msg, idx) => (
            <div key={idx} className={`msg ${msg.role === "user" ? "user-msg" : ""}`}>
              <div className={`avatar ${msg.role === "user" ? "user-avatar" : ""}`}>
                {msg.role === "assistant" ? (
                  <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"/></svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{color:'var(--text-secondary)'}}><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"/></svg>
                )}
              </div>
              <div className="bubble">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="msg">
              <div className="avatar"><svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"/></svg></div>
              <div className="bubble"><span className="cursor" style={{marginLeft:0}}></span></div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        {hasUploaded && !isReady && !isTyping && (
          <div className="quick-chips">
            <div className="chip" onClick={() => submitChatMessage("Yes, this classification is correct.")}>✅ Confirm classification</div>
            <div className="chip" onClick={() => submitChatMessage("No, edit category")}>✏️ Edit category</div>
          </div>
        )}
        
        <div className="chat-input" style={{ opacity: (!hasUploaded) ? 0.5 : 1, pointerEvents: (!hasUploaded) ? 'none' : 'auto' }}>
          <input 
            type="text" 
            placeholder={!hasUploaded ? "Upload documents first..." : "Confirm with 'Yes' or describe an edit…"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitChatMessage(input)}
          />
          <button className="send-btn" onClick={() => submitChatMessage(input)}>
            <svg viewBox="0 0 24 24" fill="#0A0B0E" width="15" height="15"><path d="M3 12l18-9-6 18-3-7-9-2z"/></svg>
          </button>
        </div>
      </div>

      {/* FORM PANEL */}
      <div className="panel">
        <div className="panel-head">
          <div className="panel-title">Source Documents</div>
        </div>
        <div className="form-body">
          <div className="field">
            <label>Current Employer <span className="req">*</span></label>
            <div className="input-wrap">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 010 20 15 15 0 010-20"/></svg>
              <input 
                type="text" 
                value={employerUrl} 
                onChange={(e) => setEmployerUrl(e.target.value)} 
                placeholder="e.g. Shipnet or https://shipnet.com" 
                disabled={hasUploaded}
              />
            </div>
          </div>
          
          <FileDropzone 
            label="Candidate CV" 
            required={true} 
            file={cvFile} 
            setFile={setCvFile} 
            id="cv-upload" 
            hint="PDF or DOCX, max 10MB"
          />
          
          <FileDropzone 
            label="Supporting Doc (FIR / EC Notes)" 
            required={false} 
            file={supportFile} 
            setFile={setSupportFile} 
            id="support-upload" 
            hint="Optional notes"
          />

          {!hasUploaded ? (
            <button 
              className={`submit-btn ${canUpload ? 'enabled' : ''}`}
              onClick={handleFileUpload}
              disabled={!canUpload}
            >
              Upload & Auto-Detect
            </button>
          ) : (
            <>
              <button 
                className={`submit-btn ${isFormComplete ? 'enabled' : ''}`} 
                onClick={handleTriggerDiscovery}
                disabled={!isFormComplete}
              >
                Submit for Analysis
              </button>
              {isFormComplete ? (
                <div className="submit-hint">Required fields complete — ready to run</div>
              ) : (
                <div className="submit-hint">Please confirm classification in chat to proceed</div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
