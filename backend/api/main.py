import re
import json
import logging
import sys
import asyncio
import uuid
from typing import List, Dict, Any, Optional
import os
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, UploadFile, File, Form, Depends, Security
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
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
from backend.services.search.factory import SearchFactory
from backend.services.orchestrator import CompanyDiscoveryOrchestrator
from backend.services.auto_sector_classifier import classify
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
logger = logging.getLogger("lead_gen_app")

app = FastAPI(
    title="Lead Gen App API",
    description="Backend services for the Lead Gen App platform",
    version="2.0.0"
)

# Add Rate Limiter Exception Handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enable CORS for Next.js frontend
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

async def get_api_key(
    api_key_header: str = Security(api_key_header),
    api_key_query: str = Security(api_key_query),
):
    expected_key = os.getenv("API_SECRET_KEY")
    if not expected_key:
        # If no key is set in backend, allow request (useful for local dev testing)
        return None
    if api_key_header == expected_key or api_key_query == expected_key:
        return expected_key
    raise HTTPException(status_code=403, detail="Could not validate API KEY")

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
async def chat_endpoint(request: Request, chat_req: ChatRequest, api_key: str = Depends(get_api_key)):
    try:
        # Load the chat prompt template
        chat_prompt = load_prompt("chat.md")
        
        # Get the latest message and formatting history
        if not chat_req.messages:
            welcome_text = "Welcome to Lead Gen App.\nI'll help you discover and qualify companies that match your requirements.\nLet's start by understanding what you're looking for.\n\nWhat type of company are you looking for?\nExamples:\n• Manufacturer\n• Distributor\n• Dealer\n• Service Provider"
            return ChatResponse(content=welcome_text, extracted_data={}, ready=False)
            
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
    request: Request,
    employer_url: str = Form(""),
    cv_file: UploadFile = File(None),
    support_file: UploadFile = File(None),
    api_key: str = Depends(get_api_key)
):
    try:
        # Define async worker functions for parallel execution
        async def parse_cv():
            if not cv_file: return ""
            cv_bytes = await cv_file.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(cv_file.filename)[1]) as tmp:
                tmp.write(cv_bytes)
                tmp_path = tmp.name
            try:
                return await asyncio.to_thread(extract_text_from_file, tmp_path)
            finally:
                os.remove(tmp_path)
                
        async def parse_support():
            if not support_file: return ""
            sup_bytes = await support_file.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(support_file.filename)[1]) as tmp:
                tmp.write(sup_bytes)
                tmp_path = tmp.name
            try:
                return await asyncio.to_thread(extract_text_from_file, tmp_path)
            finally:
                os.remove(tmp_path)
                
        async def scrape_site():
            if not employer_url: return ""
            employer_url_clean = employer_url.strip()
            target_url = None
            
            if " " not in employer_url_clean and "." in employer_url_clean:
                target_url = employer_url_clean if employer_url_clean.startswith("http") else f"https://{employer_url_clean}"
            else:
                logger.info(f"'{employer_url_clean}' looks like a company name. Searching for official website...")
                try:
                    search_service = SearchFactory.get_service()
                    results = await search_service.search(f"{employer_url_clean} official website company", num_results=1)
                    if results and len(results) > 0:
                        target_url = results[0].website
                        logger.info(f"Resolved '{employer_url_clean}' to URL: {target_url}")
                    else:
                        logger.warning(f"Could not find a website for '{employer_url_clean}'")
                except Exception as e:
                    logger.error(f"Search resolution failed: {e}")
                    
            if target_url:
                for attempt in range(3):
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            jina_res = await client.get(f"https://r.jina.ai/{target_url}")
                            if jina_res.status_code == 200:
                                return jina_res.text
                            elif jina_res.status_code == 429:
                                await asyncio.sleep(2)
                                continue
                            else:
                                logger.warning(f"Jina scrape failed with status {jina_res.status_code}")
                                return ""
                    except Exception as e:
                        if attempt == 2:
                            logger.error(f"Failed to scrape {target_url}: {e}")
                        else:
                            await asyncio.sleep(2)
            return ""

        # Execute all three tasks concurrently!
        cv_text, support_text, website_text = await asyncio.gather(
            parse_cv(), 
            parse_support(), 
            scrape_site()
        )
                    
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
        
        Website Text: {website_text}
        CV Text: {cv_text}
        Support Notes: {support_text}
        
        Task:
        1. Write a short 3-line rationale explaining why this classification makes sense based on the texts.
        2. Extract the target 'Location' from the CV and Notes. Format it specifically as "City, Country" or "Region, Country" (e.g., 'Portishead, UK', 'London, UK'). Be as specific as possible based on the candidate's area. If none is found, default to 'UK'.
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
async def websocket_endpoint(websocket: WebSocket, api_key: str = None):
    expected_key = os.getenv("API_SECRET_KEY")
    if expected_key and api_key != expected_key:
        await websocket.close(code=1008)
        return
        
    await websocket.accept()
    logger.info("WebSocket connection established for discovery task.")
    
    # Send ping every 15 seconds to prevent load balancer timeouts
    async def keep_alive():
        try:
            while True:
                await asyncio.sleep(15)
                await websocket.send_text(json.dumps({"type": "ping", "message": "keep-alive"}))
        except Exception:
            pass

    ping_task = asyncio.create_task(keep_alive())
    
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
        # We start the orchestrator asynchronously, but since we are awaiting it,
        # it blocks this handler until it finishes.
        orchestrator = CompanyDiscoveryOrchestrator(on_event=on_event)
        await orchestrator.run_discovery(
            company_type=company_type,
            product_or_service=product_or_service,
            location=location,
            current_employer=current_employer
        )
        
    except WebSocketDisconnect:
        logger.info("Client disconnected.")
    except Exception as e:
        logger.error(f"Error during discovery: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"An internal error occurred: {str(e)}"
            }))
        except Exception:
            pass
    finally:
        ping_task.cancel()
        try:
            await websocket.close()
        except Exception:
            pass
