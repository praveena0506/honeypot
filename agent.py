import os
import re
import dspy
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- 1. SETUP DSPy MODEL ---
# DSPy dynamically routes to Groq using the 'groq/' prefix
lm = dspy.LM(
    model='groq/llama-3.1-8b-instant', 
    api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0.7,
    max_retries=0 # Fail-fast for the hackathon tester
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
        # We use standard Predict (Zero-Shot) for high speed
        self.generate_reply = dspy.Predict(GrandpaPersona)

    def forward(self, history: List[str], latest_message: str):
        # Format history into a readable string for the model
        history_str = "\n".join(history) if history else "No previous history."
        
        try:
            # DSPy executes the prompt optimization and generation here
            prediction = self.generate_reply(
                conversation_history=history_str,
                latest_message=latest_message
            )
            return prediction.reply
        except Exception as e:
            # Fast-fail fallback if Groq rate-limits
            print(f"DSPy/Groq Error: {e}")
            return "Oh dear, my internet seems slow. Can you say that again?"

# Instantiate the DSPy Module globally so it stays in memory
agent = HoneypotAgent()

# --- 4. DETERMINISTIC EXTRACTION ---
def extract_intelligence(text: str):
    """Deterministic regex extraction (faster and cheaper than LLM extraction)"""
    upi_pattern = r'[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}'
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    phone_pattern = r'(?:\+91[\-\s]?)?[6-9]\d{9}'

    return {
        "upiIds": re.findall(upi_pattern, text),
        "phishingLinks": re.findall(url_pattern, text),
        "phoneNumbers": re.findall(phone_pattern, text)
    }

# --- 5. MAIN EXPORT ---
def process_message(user_text: str, history: List[str]):
    """
    Main entry point called by main.py
    """
    # 1. Extract Intelligence
    intel = extract_intelligence(user_text)

    # 2. Run DSPy Agent
    bot_reply = agent.forward(history=history, latest_message=user_text)

    # 3. Fast Heuristic Scoring
    scam_keywords = ["urgent", "pay", "verify", "block", "expired", "kyc", "winner", "prize", "otp"]
    text_lower = user_text.lower()
    
    score = 10
    for word in scam_keywords:
        if word in text_lower:
            score += 20

    final_score = min(score, 95)

    # Return exactly what main.py expects
    return bot_reply, final_score, intel
