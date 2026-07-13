"use client";

import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from 'react-markdown';

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ExtractedData {
  company_type?: string;
  product_or_service?: string;
  location?: string;
}

interface ChatInterfaceProps {
  onDiscoveryStart: (criteria: { company_type: string; product_or_service: string; location: string }) => void;
}

export default function ChatInterface({ onDiscoveryStart }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [extractedData, setExtractedData] = useState<ExtractedData>({});
  const [isReady, setIsReady] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize with welcome message from backend
  useEffect(() => {
    const fetchWelcome = async () => {
      try {
        setIsTyping(true);
        const res = await fetch("http://127.0.0.1:8000/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages: [] }),
        });
        const data = await res.json();
        setMessages([{ role: "assistant", content: data.content }]);
      } catch (err) {
        console.error("Error fetching welcome message:", err);
        setMessages([
          {
            role: "assistant",
            content: "Welcome to Company Intelligence AI.\nI'll help you discover and qualify companies that match your requirements.\nLet's start by understanding what you're looking for.\n\nWhat type of company are you looking for?\nExamples:\n• Manufacturer\n• Distributor\n• Dealer\n• Service Provider",
          },
        ]);
      } finally {
        setIsTyping(false);
      }
    };
    fetchWelcome();
  }, []);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const submitMessage = async (userMessage: string) => {
    if (!userMessage.trim() || isTyping) return;

    setInput("");
    const newMessages = [...messages, { role: "user", content: userMessage } as Message];
    setMessages(newMessages);
    setIsTyping(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: newMessages }),
      });
      if (!res.ok) throw new Error("Chat request failed");
      const data = await res.json();
      
      setMessages((prev) => [...prev, { role: "assistant", content: data.content }]);
      
      if (data.extracted_data) {
        setExtractedData((prev) => ({
          ...prev,
          ...data.extracted_data,
        }));
      }
      
      if (data.ready) {
        setIsReady(true);
      }
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I encountered an issue connecting to the AI brain. Please try again." },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    submitMessage(input);
  };

  const handleTriggerDiscovery = () => {
    if (extractedData.company_type && extractedData.product_or_service && extractedData.location) {
      onDiscoveryStart({
        company_type: extractedData.company_type,
        product_or_service: extractedData.product_or_service,
        location: extractedData.location,
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
            <div className="cia-version">PLATFORM v1.0</div>
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
            
            {/* Show chips if it's the first message */}
            {messages.length === 1 && (
              <div className="cia-chips">
                {["Manufacturer", "Service Provider", "Distributor", "Dealer"].map(chip => (
                  <div key={chip} className="cia-chip" onClick={() => submitMessage(chip)}>
                    {chip}
                  </div>
                ))}
              </div>
            )}

            {isTyping && (
              <div className="cia-msg-row">
                <div className="cia-avatar cia-avatar-bot">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" stroke="#fff" strokeWidth="1.6" strokeLinecap="round"/></svg>
                </div>
                <div className="cia-bubble">
                  <p className="cia-muted" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ animation: 'sweep 2s linear infinite' }}><path d="M12 3L14.5 9.5L21 12L14.5 14.5L12 21L9.5 14.5L3 12L9.5 9.5L12 3Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/></svg>
                    Thinking...
                  </p>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          <div className="cia-input-wrap">
            <form className="cia-input-bar" onSubmit={handleSendMessage}>
              <input 
                type="text" 
                placeholder="Tell the AI what companies to search…" 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isTyping || isReady}
              />
              <button className="cia-send-btn" type="submit" disabled={isTyping || !input.trim() || isReady}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M4 12L20 4L14 20L11 13L4 12Z" fill="#0a0b10"/></svg>
              </button>
            </form>
          </div>
        </div>

        {/* SIDEBAR */}
        <div className="cia-panel" style={{ maxHeight: '80vh', overflowY: 'auto' }}>
          <div className="cia-side-inner">
            <div className="cia-side-head">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 2L4 6v6c0 5 3.5 8.5 8 10 4.5-1.5 8-5 8-10V6l-8-4Z" stroke="#cca35e" strokeWidth="1.4"/></svg>
              <h3>Target Search Profile</h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div className={`cia-req-card ${extractedData.company_type ? 'completed' : ''}`}>
                <div className="cia-req-top">
                  <div className="cia-req-label">
                    <div className="cia-req-icon">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M4 21V5a1 1 0 0 1 1-1h6v17M13 21V9a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v11M8 8h.01M8 12h.01M8 16h.01" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>
                    </div>
                    Company Type
                  </div>
                  {extractedData.company_type ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17l-5-5" stroke="#52d68a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  ) : (
                    <div className="cia-req-status"></div>
                  )}
                </div>
                {extractedData.company_type ? (
                  <div className="cia-req-completed-text">{extractedData.company_type}</div>
                ) : (
                  <div className="cia-req-waiting">Waiting <span className="cia-skel"></span></div>
                )}
              </div>

              <div className={`cia-req-card ${extractedData.product_or_service ? 'completed' : ''}`}>
                <div className="cia-req-top">
                  <div className="cia-req-label">
                    <div className="cia-req-icon">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M21 8l-9-5-9 5 9 5 9-5ZM3 8v8l9 5 9-5V8M12 13v8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>
                    </div>
                    Product / Service
                  </div>
                  {extractedData.product_or_service ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17l-5-5" stroke="#52d68a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  ) : (
                    <div className="cia-req-status"></div>
                  )}
                </div>
                {extractedData.product_or_service ? (
                  <div className="cia-req-completed-text">{extractedData.product_or_service}</div>
                ) : (
                  <div className="cia-req-waiting">Waiting <span className="cia-skel"></span></div>
                )}
              </div>

              <div className={`cia-req-card ${extractedData.location ? 'completed' : ''}`}>
                <div className="cia-req-top">
                  <div className="cia-req-label">
                    <div className="cia-req-icon">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M12 22s7-6.2 7-12A7 7 0 0 0 5 10c0 5.8 7 12 7 12Z" stroke="currentColor" strokeWidth="1.6"/><circle cx="12" cy="10" r="2.3" stroke="currentColor" strokeWidth="1.6"/></svg>
                    </div>
                    Location
                  </div>
                  {extractedData.location ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17l-5-5" stroke="#52d68a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  ) : (
                    <div className="cia-req-status"></div>
                  )}
                </div>
                {extractedData.location ? (
                  <div className="cia-req-completed-text">{extractedData.location}</div>
                ) : (
                  <div className="cia-req-waiting">Waiting <span className="cia-skel"></span></div>
                )}
              </div>
            </div>

            {isReady ? (
              <button className="cia-launch-btn" onClick={handleTriggerDiscovery}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M5 3l14 9-14 9V3z" fill="currentColor"/></svg>
                Launch Discovery Engine
              </button>
            ) : (
              <div className="cia-hint">
                Provide the required criteria in the chat to start discovery. Once all three are set, the agent begins <b>automatic qualification</b>.
              </div>
            )}

            <div>
              <div className="cia-section-title" style={{ marginBottom: '14px' }}>Pipeline Preview</div>
              <div className="cia-pipeline">
                <div className={`cia-step ${!isReady ? 'active' : ''}`}>
                  <div className="cia-step-dot"><svg width="10" height="10" viewBox="0 0 24 24" fill="none"><path d="M5 13l4 4L19 7" stroke="#0a0b10" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/></svg></div>
                  <div className="cia-step-label">Requirements</div>
                </div>
                <div className={`cia-step ${isReady ? 'active' : ''}`}>
                  <div className="cia-step-dot"></div>
                  <div className="cia-step-label">Search Google</div>
                </div>
                <div className="cia-step">
                  <div className="cia-step-dot"></div>
                  <div className="cia-step-label">Crawl Websites</div>
                </div>
                <div className="cia-step">
                  <div className="cia-step-dot"></div>
                  <div className="cia-step-label">AI Analysis</div>
                </div>
                <div className="cia-step">
                  <div className="cia-step-dot"></div>
                  <div className="cia-step-label">Results Dashboard</div>
                </div>
              </div>
            </div>

            {!isReady && (
              <div>
                <div className="cia-section-title" style={{ marginBottom: '12px' }}>Try an Example</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {[
                    "I need Material Handling companies in the UK",
                    "Construction Materials distributors in Scotland",
                    "Platform Lifts installation companies in London"
                  ].map(ex => (
                    <div key={ex} className="cia-example-card" onClick={() => submitMessage(ex)}>
                      <span>{ex}</span>
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
