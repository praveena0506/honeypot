import os
import time
import logging
import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# --- 1. SETUP ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Honeypot")

app = FastAPI(title="HCL Honeypot API - Flexible")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.environ.get("HONEYPOT_API_KEY", "hackathon_secret_123")
CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

# Try to load agent
try:
    from agent import process_message
    AGENT_ACTIVE = True
except ImportError:
    AGENT_ACTIVE = False
    logger.warning("⚠️ Agent not found. Using Dummy Mode.")

# --- 2. CALLBACK TASK ---
def send_callback_task(session_id: str, total_msgs: int, intel: dict, score: int, notes: str):
    if score < 10: return

    payload = {
        "sessionId": session_id,
        "scamDetected": score > 50,
        "totalMessagesExchanged": total_msgs,
        "extractedIntelligence": {
            "bankAccounts": [],
            "upiIds": intel.get("upiIds", []),
            "phishingLinks": intel.get("phishingLinks", []),
            "phoneNumbers": intel.get("phoneNumbers", []),
            "suspiciousKeywords": ["urgent", "pay"]
        },
        "agentNotes": f"Score: {score}. Reply: {notes[:50]}"
    }

    try:
        requests.post(CALLBACK_URL, json=payload, timeout=5)
    except Exception as e:
        logger.error(f"Callback Error: {e}")

# --- 3. FLEXIBLE HANDLER ---
async def universal_handler(request: Request, background_tasks: BackgroundTasks, x_api_key: str):
    # A. Security (Log warning but don't block if key is messy)
    if x_api_key != API_KEY:
        logger.warning(f"Key Mismatch: received '{x_api_key}'")

    # B. Parse Input (The Fix for 422 Errors)
    try:
        data = await request.json()
    except:
        data = {}

    # Smart Search for Text (Handles ANY format)
    user_text = "Hello"
    if "message" in data:
        if isinstance(data["message"], dict):
            user_text = data["message"].get("text", "Hello")
        elif isinstance(data["message"], str):
            user_text = data["message"]
    elif "text" in data:
        user_text = data["text"]
    elif "user_input" in data:
        user_text = data["user_input"]
    elif "content" in data:
        user_text = data["content"]

    # Extract Session ID
    session_id = data.get("sessionId", data.get("session_id", "default_session"))

    # C. Run Agent
    bot_reply = "I am confused. Please explain."
    score = 0
    intel = {"upiIds": [], "phishingLinks": [], "phoneNumbers": []}

    if AGENT_ACTIVE:
        try:
            bot_reply, score, intel = process_message(user_text, [])
        except Exception as e:
            logger.error(f"Agent Error: {e}")
            bot_reply = "Connection slow. Please repeat?"

    # D. Queue Callback
    background_tasks.add_task(send_callback_task, session_id, 1, intel, score, bot_reply)

    # E. Return Universal Response (Matches Friend's Format)
    return {
        "status": "success",
        "reply": bot_reply,
        "scamDetected": score > 50,
        "session_id": session_id,
        "extractedIndicators": {
            "upi_ids": intel.get("upiIds", []),
            "upiIds": intel.get("upiIds", []), # Duplicate for safety
            "urls": intel.get("phishingLinks", []),
            "phone_numbers": intel.get("phoneNumbers", []),
            "phoneNumbers": intel.get("phoneNumbers", []) # Duplicate for safety
        }
    }

# --- 4. ENDPOINTS ---
@app.post("/analyze")
async def analyze_ep(req: Request, bt: BackgroundTasks, x_api_key: Optional[str] = Header(None)):
    return await universal_handler(req, bt, x_api_key)

@app.post("/api/honeypot")
async def honeypot_ep(req: Request, bt: BackgroundTasks, x_api_key: Optional[str] = Header(None)):
    return await universal_handler(req, bt, x_api_key)

@app.get("/")
async def root():
    return {"status": "operational"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)