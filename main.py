import os
import time
import logging
import json
import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# --- 1. SETUP LOGGING ---
load_dotenv()
# Set level to DEBUG to capture everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Honeypot")

app = FastAPI(title="HCL Honeypot API - Debug Mode")

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
    logger.info("✅ Agent module loaded successfully.")
except ImportError:
    AGENT_ACTIVE = False
    logger.warning("⚠️ Agent module NOT found. Running in Dummy Mode.")


# --- 2. CALLBACK TASK ---
def send_callback_task(session_id: str, total_msgs: int, intel: dict, score: int, notes: str):
    logger.info(f"📤 Preparing Callback for Session: {session_id} | Score: {score}")

    if score < 10:
        logger.info("Callback skipped (Score too low).")
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
            "suspiciousKeywords": ["urgent", "pay"]
        },
        "agentNotes": f"Score: {score}. Reply: {notes[:50]}"
    }

    try:
        logger.debug(f"Callback Payload: {json.dumps(payload)}")
        res = requests.post(CALLBACK_URL, json=payload, timeout=5)
        logger.info(f"✅ Callback Response: {res.status_code} | Body: {res.text}")
    except Exception as e:
        logger.error(f"❌ Callback Failed: {str(e)}")


# --- 3. UNIVERSAL HANDLER WITH DEEP LOGGING ---
async def universal_handler(request: Request, background_tasks: BackgroundTasks, x_api_key: str):
    start_time = time.time()

    # LOG 1: HEADERS
    headers = dict(request.headers)
    logger.info(f"🔍 INCOMING REQUEST | Headers: {json.dumps(headers)}")
    logger.info(f"🔑 Received API Key: '{x_api_key}' | Expected: '{API_KEY}'")

    if x_api_key != API_KEY:
        logger.warning(f"⛔ Key Mismatch! Proceeding anyway for debug...")

    # LOG 2: RAW BODY
    try:
        raw_body = await request.body()
        logger.info(f"📦 Raw Body (Bytes): {raw_body.decode('utf-8')}")
        data = await request.json()
    except Exception as e:
        logger.error(f"❌ Failed to parse JSON: {e}")
        data = {}

    # LOG 3: EXTRACTION
    session_id = data.get("sessionId", data.get("session_id", "default_session"))

    user_text = "Hello"
    if "message" in data:
        if isinstance(data["message"], dict):
            user_text = data["message"].get("text", "Hello")
        elif isinstance(data["message"], str):
            user_text = data["message"]
    elif "text" in data:
        user_text = data["text"]

    logger.info(f"📝 Extracted SessionID: {session_id}")
    logger.info(f"📝 Extracted User Text: '{user_text}'")

    # LOG 4: HISTORY
    history = []
    if "conversationHistory" in data and isinstance(data["conversationHistory"], list):
        for item in data["conversationHistory"]:
            if isinstance(item, dict):
                history.append(item.get("text", ""))
    logger.info(f"📚 History Length: {len(history)}")

    # LOG 5: AGENT EXECUTION
    bot_reply = "I am a bit confused, why do I need to pay?"
    score = 0
    intel = {"upiIds": [], "phishingLinks": [], "phoneNumbers": []}

    if AGENT_ACTIVE:
        try:
            logger.info("🧠 Calling Agent...")
            bot_reply, score, intel = process_message(user_text, history)
            logger.info(f"🧠 Agent Success | Score: {score} | Intel: {intel}")
        except Exception as e:
            logger.error(f"❌ Agent Crash: {str(e)}")
            bot_reply = "Internet slow. Please repeat?"
    else:
        logger.info("🧠 Agent Inactive (Dummy Mode)")

    # Queue Callback
    background_tasks.add_task(send_callback_task, session_id, len(history) + 1, intel, score, bot_reply)

    # LOG 6: FINAL RESPONSE
    response_data = {
        "status": "success",
        "honeypot": "active",
        "request_logged": True,
        "timestamp": time.time(),
        "reply": bot_reply,
        "scamDetected": score > 50,
        "session_id": session_id,
        "extractedIndicators": {
            "upi_ids": intel.get("upiIds", []),
            "upiIds": intel.get("upiIds", []),
            "urls": intel.get("phishingLinks", []),
            "phishingLinks": intel.get("phishingLinks", []),
            "phone_numbers": intel.get("phoneNumbers", []),
            "phoneNumbers": intel.get("phoneNumbers", []),
            "bank_accounts": []
        },
        "metadata": {
            "processed_instantly": True,
            "processing_time": time.time() - start_time
        }
    }

    logger.info(f"🚀 Sending Response: {json.dumps(response_data)}")
    return response_data


# --- 4. ENDPOINTS ---
@app.post("/analyze")
async def analyze_ep(req: Request, bt: BackgroundTasks, x_api_key: Optional[str] = Header(None)):
    logger.info("➡️ Hit /analyze endpoint")
    return await universal_handler(req, bt, x_api_key)


@app.post("/api/honeypot")
async def honeypot_ep(req: Request, bt: BackgroundTasks, x_api_key: Optional[str] = Header(None)):
    logger.info("➡️ Hit /api/honeypot endpoint")
    return await universal_handler(req, bt, x_api_key)


@app.get("/")
async def root():
    return {"status": "operational", "mode": "debug"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)