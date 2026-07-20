import re
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.api.config import settings
from backend.services.llm.factory import LLMFactory
from backend.services.orchestrator import CompanyDiscoveryOrchestrator
from backend.prompts import load_prompt

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
async def chat_endpoint(request: ChatRequest):
    try:
        # Load the chat prompt template
        chat_prompt = load_prompt("chat.md")
        
        # Get the latest message and formatting history
        if not request.messages:
            welcome_text = "Welcome to Company Intelligence AI.\nI'll help you discover and qualify companies that match your requirements.\nLet's start by understanding what you're looking for.\n\nWhat type of company are you looking for?\nExamples:\n• Manufacturer\n• Distributor\n• Dealer\n• Service Provider"
            return ChatResponse(content=welcome_text, ready=False)
            
        latest_message = request.messages[-1].content
        history_msgs = request.messages[:-1]
        
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
            location=location
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
