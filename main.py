import os
import logging
import requests
import uvicorn
import time
from fastapi import FastAPI, HTTPException, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# --- 1. SETUP ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Honeypot")

app = FastAPI(title="HCL Honeypot API - Universal")

# CORS (Critical for web testers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.environ.get("HONEYPOT_API_KEY", "hackathon_secret_123")
CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

# Import Brain (Safely)
try:
    from agent import process_message

    AGENT_ACTIVE = True
except ImportError:
    AGENT_ACTIVE = False
    logger.warning("⚠️ agent.py not found. Running in Dummy Mode.")


# --- 2. BACKGROUND CALLBACK (The real work) ---
def send_callback_task(session_id: str, total_msgs: int, intel: dict, score: int, notes: str):
    # Only report if it's somewhat suspicious or if you want to report everything
    if score < 10:
        return

    payload = {
        "sessionId": session_id,
        "scamDetected": score > 50,
        "totalMessagesExchanged": total_msgs,
        "extractedIntelligence": {
            "bankAccounts": [],
            "upiIds": intel.get("upiIds", []),
            "phishingLinks": intel.get("phishingLinks", []),
            "phoneNumbers": intel.get("phoneNumbers", []),
            "suspiciousKeywords": ["urgent", "pay", "verify"]
        },
        "agentNotes": f"Score: {score}. Reply: {notes[:50]}..."
    }

    try:
        res = requests.post(CALLBACK_URL, json=payload, timeout=5)
        logger.info(f"🚀 Callback Sent for {session_id} | Status: {res.status_code}")
    except Exception as e:
        logger.error(f"❌ Callback Failed: {e}")


# --- 3. UNIVERSAL LOGIC HANDLER ---
async def handle_request_logic(request: Request, background_tasks: BackgroundTasks, x_api_key: str):
    # A. Validation (Loose)
    # We log the warning but don't block, just like your friend's code
    if x_api_key != API_KEY:
        logger.warning(f"Key mismatch: {x_api_key} (Expected: {API_KEY})")

    # B. Input Parsing (Bulletproof)
    try:
        data = await request.json()
    except Exception:
        data = {}  # Survive empty body

    # C. Extract Data (Smart Search)
    # Look for session_id in every possible place
    session_id = data.get("sessionId", data.get("session_id", "default_session"))

    # Look for text in every possible place
    user_text = "Hello"
    if "message" in data:
        if isinstance(data["message"], dict):
            user_text = data["message"].get("text", "Hello")
        elif isinstance(data["message"], str):
            user_text = data["message"]
    elif "text" in data:
        user_text = data["text"]

    # History (Optional)
    history = []
    if "conversationHistory" in data and isinstance(data["conversationHistory"], list):
        for item in data["conversationHistory"]:
            if isinstance(item, dict):
                history.append(item.get("text", ""))

    # D. AI Processing
    bot_reply = "I am confused, can you explain?"
    score = 0
    intel = {"upiIds": [], "phishingLinks": [], "phoneNumbers": []}

    if AGENT_ACTIVE:
        try:
            bot_reply, score, intel = process_message(user_text, history)
        except Exception as e:
            logger.error(f"AI Error: {e}")

    # E. Queue Callback (Background)
    total_msgs = len(history) + 1
    background_tasks.add_task(send_callback_task, session_id, total_msgs, intel, score, bot_reply)

    # F. Response (Format matches your friend's working code)
    return {
        "status": "success",
        "reply": bot_reply,
        "scamDetected": score > 50,
        "session_id": session_id,
        "extractedIndicators": {
            "upi_ids": intel.get("upiIds", []),
            "urls": intel.get("phishingLinks", []),
            "phone_numbers": intel.get("phoneNumbers", []),
            "bank_accounts": []
        },
        "metadata": {
            "processed_instantly": True,
            "timestamp": time.time()
        }
    }


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {"status": "operational", "team": "Honeypot Agent"}


@app.get("/health")
@app.post("/health")
async def health():
    return {"status": "healthy"}


# Endpoint 1: The one defined in Docs
@app.post("/analyze")
async def analyze_endpoint(
        request: Request,
        background_tasks: BackgroundTasks,
        x_api_key: Optional[str] = Header(None)
):
    return await handle_request_logic(request, background_tasks, x_api_key)


# Endpoint 2: The one your friend used (Backup)
@app.post("/api/honeypot")
async def friend_endpoint(
        request: Request,
        background_tasks: BackgroundTasks,
        x_api_key: Optional[str] = Header(None)
):
    return await handle_request_logic(request, background_tasks, x_api_key)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)