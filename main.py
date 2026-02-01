import os
import time
import logging
import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# --- 1. IMPORT THE BRAIN ---
# Ensure agent.py is in the same folder!
try:
    from agent import process_message
except ImportError:
    # Fallback if agent.py is missing (prevents crash during deploy)
    print("WARNING: agent.py not found. Using dummy bot.")


    def process_message(text, history):
        return "I am confused, please explain.", 50, {"upiIds": [], "phoneNumbers": [], "phishingLinks": []}

load_dotenv()

# --- 2. SETUP LOGGING & APP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Honeypot")

app = FastAPI(title="HCL Honeypot API - Final")

# CORS (Crucial for web widgets)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.environ.get("HONEYPOT_API_KEY", "hackathon_secret_123")
CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"


# --- 3. DATA MODELS (Flexible) ---
# We use flexible dicts mostly, but define these for documentation
class MessageItem(BaseModel):
    sender: str
    text: str
    timestamp: Optional[str] = None


class HoneypotResponse(BaseModel):
    status: str
    reply: str
    # extractedIntelligence is OPTIONAL in immediate response for some testers,
    # but mandatory in the Callback. We include it here just for debugging/safety.
    extractedIntelligence: Optional[Dict] = None


# --- 4. BACKGROUND TASK (The "Callback" Logic) ---
def send_final_result_task(session_id: str, total_msgs: int, intel: dict, score: int, notes: str):
    """
    Sends the extracted intelligence to the Hackathon Evaluation Endpoint.
    """
    # Only report if there is a threat or significant interaction
    # (You can remove 'score > 30' if you want to report everything)
    if score < 10 and not intel['upiIds'] and not intel['phoneNumbers']:
        logger.info(f"Skipping callback for harmless session {session_id}")
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
            "suspiciousKeywords": []
        },
        "agentNotes": f"Scam Score: {score}. Bot Replied: {notes[:50]}..."
    }

    try:
        logger.info(f"🚀 Sending Callback for {session_id}...")
        res = requests.post(CALLBACK_URL, json=payload, timeout=5)
        logger.info(f"Callback Status: {res.status_code} | Response: {res.text}")
    except Exception as e:
        logger.error(f"❌ Callback Failed: {e}")


# --- 5. THE UNIVERSAL LOGIC HANDLER ---
async def handle_honeypot_logic(request: Request, background_tasks: BackgroundTasks, x_api_key: str):
    """
    Shared logic for both /analyze and /api/honeypot endpoints
    """
    # A. Security Check
    if x_api_key != API_KEY:
        logger.warning(f"⛔ Unauthorized access with key: {x_api_key}")
        # We return a 401 error, but you can comment this out if the tester is buggy
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # B. Parse Data (Universal Parser)
    try:
        data = await request.json()
    except:
        data = {}

    # Extract Data safely
    session_id = data.get("sessionId", data.get("session_id", "unknown_session"))

    # Find the user's message text (Handles deep nesting or flat structure)
    user_text = ""
    history = []

    if "message" in data and isinstance(data["message"], dict):
        user_text = data["message"].get("text", "")
    elif "text" in data:
        user_text = data["text"]
    elif "message" in data and isinstance(data["message"], str):
        user_text = data["message"]

    if not user_text:
        user_text = "Hello"  # Default fallback

    # Handle History
    if "conversationHistory" in data:
        history = [m.get("text", "") for m in data["conversationHistory"] if isinstance(m, dict)]

    # C. Call the AI Agent
    bot_reply, score, intel = process_message(user_text, history)

    # D. Queue the Callback (Background)
    # Calc total messages
    total_msgs = len(history) + 1
    background_tasks.add_task(
        send_final_result_task,
        session_id,
        total_msgs,
        intel,
        score,
        bot_reply
    )

    # E. Return Immediate Response
    return {
        "status": "success",
        "reply": bot_reply,
        # We add these extras just in case the tester wants to see them immediately
        "scamDetected": score > 50,
        "extractedIntelligence": intel
    }


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {"status": "operational", "project": "HCL Honeypot"}


@app.get("/health")
@app.post("/health")
async def health_check():
    return {"status": "healthy"}


# --- OFFICIAL ENDPOINT (Per Doc) ---
@app.post("/analyze")
async def analyze_endpoint(
        request: Request,
        background_tasks: BackgroundTasks,
        x_api_key: Optional[str] = Header(None)
):
    return await handle_honeypot_logic(request, background_tasks, x_api_key)


# --- BACKUP ENDPOINT (Your Custom Link) ---
@app.post("/api/honeypot")
async def custom_endpoint(
        request: Request,
        background_tasks: BackgroundTasks,
        x_api_key: Optional[str] = Header(None)
):
    return await handle_honeypot_logic(request, background_tasks, x_api_key)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)