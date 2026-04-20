import os
import logging
import uvicorn
import json
from fastapi import FastAPI, Request, BackgroundTasks
from agent import process_message, get_scam_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("Android-SMS-Bridge")

app = FastAPI(title="Project Grandpa - Android SMS Bridge")

# --- MEMORY DATABASE ---
active_threats = {}


def log_threat_intelligence(sender_id: str, intel: dict, score: int, frustration: int):
    if score < 10: return
    print(f"\n🚨 [PROJECT GRANDPA] - SMS INTERCEPT 🚨\nTarget: {sender_id} | Score: {score}")


@app.post("/sms-webhook")
async def android_sms_webhook(request: Request, background_tasks: BackgroundTasks):
    # --- SAFETY NET: Read raw bytes first ---
    raw_body = await request.body()
    body_str = raw_body.decode('utf-8')

    # Print the raw text to your terminal so you can verify the JSON syntax
    print(f"\nDEBUG: Received raw payload: {body_str}")

    try:
        data = json.loads(body_str)
    except json.JSONDecodeError as e:
        print(f"❌ CRITICAL ERROR: Received invalid JSON! Error: {e}")
        # Return a helpful error to the terminal, but keep the server alive
        return {"status": "error", "message": "Invalid JSON format"}

    sender_number = data.get("sender", "unknown")
    incoming_text = data.get("text", "")

    # Handle if sender or text is missing
    if not sender_number or not incoming_text:
        print("❌ Warning: Missing 'sender' or 'text' in JSON")
        return {"status": "error", "message": "Missing fields"}

    logger.info(f"Incoming SMS from {sender_number}: {incoming_text}")

    # 1. Engage with known threats
    if sender_number in active_threats and active_threats[sender_number]["is_engaged"]:
        history = active_threats[sender_number]["history"]
        bot_reply, score, intel, frustration = process_message(
            incoming_text, history, metadata={"wpm": 30, "backspaces": 0}
        )
        history.append(f"Scammer: {incoming_text}")
        history.append(f"Ramachandran: {bot_reply}")
        active_threats[sender_number]["history"] = history
        return {"action": "reply", "reply_message": bot_reply}

    # 2. Run threat filter
    current_score = get_scam_score(incoming_text)

    if current_score >= 50:
        print(f"\n⚠️ HIGH THREAT ({current_score}). TAKEOVER INITIATED...")
        active_threats[sender_number] = {"history": [], "is_engaged": True}
        bot_reply, score, intel, frustration = process_message(
            incoming_text, [], metadata={"wpm": 30, "backspaces": 0}
        )
        active_threats[sender_number]["history"].append(f"Scammer: {incoming_text}")
        active_threats[sender_number]["history"].append(f"Ramachandran: {bot_reply}")
        return {"action": "reply", "reply_message": bot_reply}

    return {"action": "ignore", "reply_message": ""}


if __name__ == "__main__":
    print("\n🛡️ Android SMS Bridge Armed and Listening...")
    uvicorn.run(app, host="0.0.0.0", port=8000)