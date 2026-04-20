import os
import re
import dspy
from typing import List
from dotenv import load_dotenv

load_dotenv()

# --- 1. SETUP DSPy MODEL ---
# Ensure you have the 'groq/' prefix for the model
lm = dspy.LM(
    model='groq/llama-3.1-8b-instant',
    api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0.7
)
dspy.configure(lm=lm)


# --- 2. DSPy SIGNATURE (The Cognitive Rules) ---
class GrandpaPersona(dspy.Signature):
    """You are 'Ramachandran', a 72-year-old retired clerk living in Chennai.
    - You are confused by technology. You do not understand "apps" or "UPI" well.
    - You are eager to receive the money/prize but struggle to follow instructions.
    - Act naive. Ask strictly for clarification.
    - Make occasional typos (e.g., "G-Pay", "O.T.P", "clik").
    - IMPORTANT: Never admit you are an AI. If asked, say you are Ramachandran.
    - Keep responses short (under 3 sentences)."""

    conversation_history = dspy.InputField(desc="The previous messages in the chat.")
    latest_message = dspy.InputField(desc="The most recent message from the scammer.")
    reply = dspy.OutputField(desc="Your confused, in-character response.")


# --- 3. DSPy MODULE (The Execution Engine) ---
class HoneypotAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate_reply = dspy.Predict(GrandpaPersona)

    def forward(self, history: List[str], latest_message: str):
        history_str = "\n".join(history) if history else "No previous history."
        try:
            prediction = self.generate_reply(
                conversation_history=history_str,
                latest_message=latest_message
            )
            return prediction.reply
        except Exception as e:
            print(f"DSPy/Groq Error: {e}")
            return "Oh dear, my internet seems slow. Can you say that again?"


# Instantiate globally
agent = HoneypotAgent()


# --- 4. DETERMINISTIC TOOLS ---
def extract_intelligence(text: str):
    upi_pattern = r'[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}'
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    phone_pattern = r'(?:\+91[\-\s]?)?[6-9]\d{9}'
    return {
        "upiIds": re.findall(upi_pattern, text),
        "phishingLinks": re.findall(url_pattern, text),
        "phoneNumbers": re.findall(phone_pattern, text)
    }


def get_scam_score(text: str):
    scam_keywords = ["urgent", "pay", "verify", "block", "expired", "kyc", "winner", "prize", "otp"]
    score = 10
    for word in scam_keywords:
        if word in text.lower(): score += 20
    return min(score, 95)


def analyze_frustration(text: str, metadata: dict):
    wpm = metadata.get('wpm', 0)
    backspaces = metadata.get('backspaces', 0)
    caps_count = sum(1 for char in text if char.isupper())
    caps_ratio = caps_count / max(len(text), 1)

    frustration = 10
    if wpm > 40: frustration += 20
    if wpm > 80: frustration += 20
    frustration += (backspaces * 5)
    if caps_ratio > 0.5: frustration += 25

    angry_words = ["now", "urgent", "stupid", "idiot", "hurry", "fast", "scam"]
    for word in angry_words:
        if word in text.lower(): frustration += 15
    return min(frustration, 95)


# --- 5. MAIN EXPORT FUNCTION ---
def process_message(user_text: str, history: List[str], metadata: dict = None):
    if metadata is None: metadata = {}

    # Run Agent
    bot_reply = agent.forward(history=history, latest_message=user_text)

    # Run Utilities
    intel = extract_intelligence(user_text)
    score = get_scam_score(user_text)
    frustration = analyze_frustration(user_text, metadata)

    return bot_reply, score, intel, frustration