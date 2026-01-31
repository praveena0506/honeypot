import os
import uvicorn
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from agent import process_message

load_dotenv()

app = FastAPI()
REQUIRED_KEY = os.environ.get("HONEYPOT_API_KEY")


# --- DATA MODELS ---
class Message(BaseModel):
    sender: str
    text: str
    timestamp: Optional[str] = None


class IncomingRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: List[Message] = []


class ExtractedIntelligence(BaseModel):
    upiIds: List[str] = []
    phishingLinks: List[str] = []
    phoneNumbers: List[str] = []  # Added this to match agent.py


class HoneypotResponse(BaseModel):
    status: str
    scamDetected: bool
    extractedIntelligence: ExtractedIntelligence
    agentNotes: str


@app.get("/health")
async def health_check():
    return {"status": "alive"}


@app.post("/analyze", response_model=HoneypotResponse)
async def analyze_scam(payload: IncomingRequest, x_api_key: str = Header(None)):
    # 1. Security Check
    if x_api_key != REQUIRED_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # 2. Get history
    history_text = [m.text for m in payload.conversationHistory]

    # 3. Ask Agent (Calling the brain)
    # This now returns THREE values: Reply, Score, and the Intel Dictionary
    bot_reply, score, intel = process_message(payload.message.text, history_text)

    # 4. Return JSON
    return {
        "status": "success",
        "scamDetected": score > 50,
        "extractedIntelligence": intel,  # Pass the dictionary directly
        "agentNotes": bot_reply
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)