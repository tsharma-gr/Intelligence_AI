import re
import json
import logging
import sys
import asyncio
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sentry_sdk
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis.asyncio as redis_async
from arq import create_pool
from arq.connections import RedisSettings

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from backend.api.config import settings
from backend.services.llm.factory import LLMFactory
from backend.services.orchestrator import CompanyDiscoveryOrchestrator
from backend.prompts import load_prompt

# Initialize Sentry
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("company_intelligence")

app = FastAPI(
    title="Company Intelligence AI API",
    description="Backend API for AI-powered Company Discovery & Qualification Platform",
    version="1.0.0"
)

# Add Rate Limiter Exception Handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    extracted_data: Optional[Dict[str, Any]] = None
    ready: bool = False

@app.get("/api/health")
def health_check():
    return {"status": "ok", "provider": settings.llm_provider}

@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit("50/minute")
async def chat_endpoint(request: Request, chat_req: ChatRequest):
    try:
        # Load the chat prompt template
        chat_prompt = load_prompt("chat.md")
        
        # Get the latest message and formatting history
        if not chat_req.messages:
            welcome_text = "Welcome to Company Intelligence AI.\nI'll help you discover and qualify companies that match your requirements.\nLet's start by understanding what you're looking for.\n\nWhat type of company are you looking for?\nExamples:\n• Manufacturer\n• Distributor\n• Dealer\n• Service Provider"
            return ChatResponse(content=welcome_text, ready=False)
            
        latest_message = chat_req.messages[-1].content
        history_msgs = chat_req.messages[:-1]
        
        history_str = ""
        for msg in history_msgs:
            role_label = "User" if msg.role == "user" else "Assistant"
            history_str += f"{role_label}: {msg.content}\n"
            
        # Format the prompt
        formatted_prompt = chat_prompt.format(
            history=history_str.strip(),
            message=latest_message
        )
        
        # Instantiate LLM
        llm = LLMFactory.get_service()
        
        # Generate response
        system_instruction = "You are an assistant collecting specific company research criteria (company type, product/service, location) from the user."
        response_text = await llm.generate_response(formatted_prompt, system_instruction)
        
        # Check if the extracted data is present in the response
        extracted_data = None
        ready = False
        
        # Look for the json_extracted block
        pattern = r"```json_extracted\s*([\s\S]*?)\s*```"
        match = re.search(pattern, response_text)
        if match:
            try:
                json_str = match.group(1).strip()
                extracted_data = json.loads(json_str)
                ready = extracted_data.get("ready", False)
                response_text = re.sub(pattern, "", response_text).strip()
            except Exception as e:
                logger.error(f"Failed to parse extracted JSON: {e}")
                
        return ChatResponse(
            role="assistant",
            content=response_text,
            extracted_data=extracted_data,
            ready=ready
        )
        
    except Exception as e:
        logger.exception("Error in chat endpoint")
        raise HTTPException(status_code=500, detail=str(e))

import tempfile
import httpx
import os
from backend.services.document_parser import extract_text_from_file
from backend.services.auto_sector_classifier import classify

@app.post("/api/auto-detect")
async def auto_detect_endpoint(
    employer_url: str = Form(""),
    cv_file: UploadFile = File(None),
    support_file: UploadFile = File(None)
):
    try:
        cv_text = ""
        support_text = ""
        
        # Parse CV
        if cv_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(cv_file.filename)[1]) as tmp:
                tmp.write(await cv_file.read())
                tmp_path = tmp.name
            cv_text = extract_text_from_file(tmp_path)
            os.remove(tmp_path)
            
        # Parse Support Doc
        if support_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(support_file.filename)[1]) as tmp:
                tmp.write(await support_file.read())
                tmp_path = tmp.name
            support_text = extract_text_from_file(tmp_path)
            os.remove(tmp_path)
            
        # Scrape Website
        website_text = ""
        if employer_url:
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    jina_res = await client.get(f"https://r.jina.ai/{employer_url}")
                    if jina_res.status_code == 200:
                        website_text = jina_res.text
                except Exception as e:
                    logger.error(f"Failed to scrape {employer_url}: {e}")
                    
        # Run Rule-based Classifier
        classification = classify(
            employer_homepage_text=website_text,
            linkedin_about_text=support_text + "\n" + cv_text,
            homepage_url=employer_url
        )
        
        # Use LLM to generate Rationale & Location
        llm = LLMFactory.get_service()
        prompt = f"""
        You are an expert sector classifier.
        We have automatically classified the target sector as:
        Sector: {classification['sector']}
        Subsector: {classification['subsector'] if classification['subsector'] else 'PLEASE DETERMINE FROM TEXT'}
        Solution Type: {classification['solution_type']}
        Product Focus: {classification['product_focus'] if classification['product_focus'] else 'PLEASE DETERMINE FROM TEXT'}
        
        Website Text: {website_text[:1500]}
        CV Text: {cv_text[:1500]}
        Support Notes: {support_text[:1500]}
        
        Task:
        1. Write a short 3-line rationale explaining why this classification makes sense based on the texts.
        2. Extract the target 'Location' from the CV and Notes (e.g., 'UK', 'London, UK'). If none is found, default to 'UK'.
        3. If the Subsector or Product Focus are 'PLEASE DETERMINE FROM TEXT', infer the most accurate 1-3 word description for them based on the text. If they are already filled out, just output them exactly as is.
        
        Output JSON only:
        {{
            "rationale": "...",
            "location": "...",
            "subsector": "...",
            "product_focus": "..."
        }}
        """
        response_text = await llm.generate_response(prompt, "Output valid JSON only.")
        
        # Parse LLM response
        rationale = "Based on the provided documents and website, this matches the target profile."
        location = "UK"
        try:
            # simple json extraction
            json_str = response_text[response_text.find("{"):response_text.rfind("}")+1]
            data = json.loads(json_str)
            if "rationale" in data:
                rationale = data["rationale"]
            if "location" in data:
                location = data["location"]
            if "subsector" in data and not classification['subsector']:
                classification['subsector'] = data["subsector"]
            if "product_focus" in data and not classification['product_focus']:
                classification['product_focus'] = data["product_focus"]
        except Exception as e:
            logger.error(f"Failed to parse rationale json: {e}")
            
        return {
            "classification": classification,
            "rationale": rationale,
            "location": location
        }
        
    except Exception as e:
        logger.exception("Error in auto-detect endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/api/ws/discovery")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established for discovery task.")
    
    try:
        # Wait for initial configuration criteria from the frontend client
        data = await websocket.receive_text()
        criteria = json.loads(data)
        
        company_type = criteria.get("company_type")
        product_or_service = criteria.get("product_or_service")
        location = criteria.get("location")
        current_employer = criteria.get("current_employer", "")
        
        if not all([company_type, product_or_service, location]):
            await websocket.send_json({
                "type": "error",
                "message": "Missing search criteria values."
            })
            await websocket.close()
            return
            
        # Event handler that pushes pipeline events to the client websocket
        async def on_event(event_type: str, event_payload: Dict[str, Any]):
            try:
                await websocket.send_json({
                    "type": event_type,
                    "message": event_payload.get("message", ""),
                    "data": event_payload.get("data", {})
                })
            except Exception as ex:
                logger.error(f"Failed to push message over websocket: {ex}")

        # Initialize orchestrator
        orchestrator = CompanyDiscoveryOrchestrator(on_event=on_event)
        
        # Run pipeline
        await orchestrator.run_discovery(
            company_type=company_type,
            product_or_service=product_or_service,
            location=location,
            current_employer=current_employer
        )
        
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.exception("Error in discovery WebSocket channel")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Orchestrator failed: {str(e)}"
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
