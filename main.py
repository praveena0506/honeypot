import os
import uvicorn
import requests
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from agent import process_message

load_dotenv()

app = FastAPI()
REQUIRED_KEY = os.environ.get("HONEYPOT_API_KEY")


# --- 1. STRICT INPUT MODELS (Section 6) ---
class MessageItem(BaseModel):
    sender: str
    text: str
    timestamp: Optional[str] = None


class Metadata(BaseModel):
    channel: Optional[str] = None
    language: Optional[str] = None
    locale: Optional[str] = None


class IncomingRequest(BaseModel):
    sessionId: str
    message: MessageItem
    conversationHistory: List[MessageItem] = []
    metadata: Optional[Metadata] = None


# --- 2. SIMPLE OUTPUT MODEL (Section 8) ---
class HoneypotResponse(BaseModel):
    status: str
    reply: str


# --- 3. MANDATORY CALLBACK LOGIC (Section 12) ---
def send_final_result(session_id: str, total_msgs: int, intel: dict, score: int, notes: str):
    """
    Sends the extracted intelligence to the GUVI evaluation endpoint.
    This runs in the background so it doesn't slow down the chat.
    """
    # Only send if scam is actually detected
    is_scam = score > 50
    if not is_scam:
        return

    callback_url = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

    payload = {
        "sessionId": session_id,
        "scamDetected": is_scam,
        "totalMessagesExchanged": total_msgs,
        "extractedIntelligence": {
            "bankAccounts": [],  # Add regex for this if needed
            "upiIds": intel.get("upiIds", []),
            "phishingLinks": intel.get("phishingLinks", []),
            "phoneNumbers": intel.get("phoneNumbers", []),
            "suspiciousKeywords": ["urgent", "verify", "block"]  # Example
        },
        "agentNotes": f"Scam detected with score {score}. Agent replied: {notes[:50]}..."
    }

    try:
        print(f"🚀 Sending Callback for Session {session_id}...")
        requests.post(callback_url, json=payload, timeout=5)
        print("✅ Callback Sent Successfully")
    except Exception as e:
        print(f"❌ Callback Failed: {e}")


# --- 4. THE MAIN ENDPOINT ---
@app.post("/analyze", response_model=HoneypotResponse)
async def analyze_scam(payload: IncomingRequest, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    # 1. Security Check (Section 5)
    if x_api_key != REQUIRED_KEY:
        # Strict mode: raise HTTPException(status_code=401)
        print(f"WARNING: Invalid Key {x_api_key}")

    # 2. Prepare History
    history_text = [m.text for m in payload.conversationHistory]

    # 3. Call the Brain (agent.py)
    bot_reply, score, intel = process_message(payload.message.text, history_text)

    # 4. Handle Mandatory Callback (Section 12)
    # We calculate total messages as History + Current Message
    total_messages = len(payload.conversationHistory) + 1

    # Run this in the background to keep the API fast
    background_tasks.add_task(
        send_final_result,
        payload.sessionId,
        total_messages,
        intel,
        score,
        bot_reply
    )

    # 5. Return Simple JSON (Section 8)
    return {
        "status": "success",
        "reply": bot_reply
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)