import os
import time
import logging
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Honeypot-Project")

app = FastAPI(title="Project Grandpa - Autonomous Honeypot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from agent import process_message
    AGENT_ACTIVE = True
except ImportError:
    AGENT_ACTIVE = False

def log_threat_intelligence(session_id: str, intel: dict, score: int, frustration: int):
    if score < 10: return
    logger.warning("="*50)
    logger.warning("🚨 THREAT INTEL & PSYCHOLOGICAL PROFILE 🚨")
    logger.warning(f"Scam Score: {score}/100 | Frustration Index: {frustration}/100")
    logger.warning(f"Extracted: {intel}")
    logger.warning("="*50)

@app.post("/analyze")
async def analyze_ep(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except:
        data = {}

    user_text = data.get("text", "Hello")
    metadata = data.get("typing_metadata", {"wpm": 0, "backspaces": 0})
    session_id = data.get("session_id", "class_demo_session")

    bot_reply = "I am confused."
    score, frustration = 0, 0
    intel = {"upiIds": [], "phishingLinks": [], "phoneNumbers": []}

    if AGENT_ACTIVE:
        try:
            bot_reply, score, intel, frustration = process_message(user_text, [], metadata)
        except Exception as e:
            logger.error(f"Agent Error: {e}")

    background_tasks.add_task(log_threat_intelligence, session_id, intel, score, frustration)

    return {
        "status": "success",
        "reply": bot_reply,
        "scamDetected": score > 50,
        "scamScore": score,
        "extractedIntelligence": intel,
        "frustrationIndex": frustration
    }

@app.get("/")
async def root():
    try:
        with open("index.html", "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except FileNotFoundError:
        return {"status": "UI not found."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))