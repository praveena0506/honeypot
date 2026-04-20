import os
import logging
from telethon import TelegramClient, events
from dotenv import load_dotenv

# Import our AI brain
from agent import process_message, get_scam_score

# --- 1. SETUP ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("Telegram-Honeypot")

API_ID = os.environ.get("TELEGRAM_API_ID")
API_HASH = os.environ.get("TELEGRAM_API_HASH")

if not API_ID or not API_HASH:
    logger.error("🚨 Missing Telegram API credentials in .env file!")
    exit(1)

# Initialize Telegram Client
client = TelegramClient('grandpa_session', API_ID, API_HASH)

# --- 2. THREAT DATABASE ---
active_threats = {}


def log_threat_intelligence(sender_id: str, intel: dict, score: int, frustration: int):
    if score < 10: return
    print("\n" + "=" * 60)
    print("🚨 [PROJECT GRANDPA] - INVISIBLE INTERCEPT TRIGGERED 🚨")
    print(f"🎯 Target Account ID : {sender_id}")
    print(f"📊 Threat Score      : [{score}/100] CRITICAL")
    print(f"🧠 Frustration Index : [{frustration}/100]")
    print(f"🔍 Extracted Intel   : {intel}")
    print("=" * 60 + "\n")


# --- 3. THE SILENT LISTENER ---
@client.on(events.NewMessage(incoming=True))
async def invisible_interceptor(event):
    # Ignore group chats
    if not event.is_private:
        return

    sender = await event.get_sender()
    sender_id = str(sender.id)
    incoming_text = event.raw_text

    # 1. Is this a known scammer we are already fighting?
    if sender_id in active_threats and active_threats[sender_id]["is_engaged"]:
        history = active_threats[sender_id]["history"]

        bot_reply, score, intel, frustration = process_message(
            incoming_text, history, metadata={"wpm": 35, "backspaces": 0}
        )

        history.append(f"Scammer: {incoming_text}")
        history.append(f"Ramachandran: {bot_reply}")
        active_threats[sender_id]["history"] = history

        log_threat_intelligence(sender_id, intel, score, frustration)

        # Grandpa replies autonomously!
        await event.reply(bot_reply)
        return

    # 2. Monitor mode: Run the math filter silently
    current_score = get_scam_score(incoming_text)

    if current_score >= 50:
        print(f"\n⚠️ HIGH THREAT DETECTED ({current_score}). AUTONOMOUS TAKEOVER INITIATED FOR {sender_id}...")

        active_threats[sender_id] = {"history": [], "is_engaged": True}

        bot_reply, score, intel, frustration = process_message(
            incoming_text, [], metadata={"wpm": 35, "backspaces": 0}
        )

        active_threats[sender_id]["history"].append(f"Scammer: {incoming_text}")
        active_threats[sender_id]["history"].append(f"Ramachandran: {bot_reply}")

        log_threat_intelligence(sender_id, intel, score, frustration)

        # Fire back at the scammer
        await event.reply(bot_reply)
    else:
        # Not a threat, stay completely invisible.
        pass


# --- 4. LAUNCH ---
if __name__ == '__main__':
    print("\n🛡️ Telegram Invisible Interceptor Armed and Listening...")
    client.start()
    client.run_until_disconnected()