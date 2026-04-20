import os
import re
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()

# --- 1. SETUP MODEL ---
llm = ChatGroq(
    temperature=0.7,
    model_name="llama-3.1-8b-instant",
    groq_api_key=os.environ.get("GROQ_API_KEY"),
    max_retries=0
)

# --- 2. DEFINE STATE ---
class AgentState(TypedDict):
    messages: List[str]
    latest_user_input: str
    reply: str
    scam_score: int

# --- 3. PERSONA PROMPT ---
GRANDPA_PROMPT = """
You are 'Ramachandran', a 72-year-old retired clerk living in Chennai.
- You are confused by technology. You do not understand "apps" or "UPI" well.
- You are eager to receive the money/prize but struggle to follow instructions.
- Act naive. Ask strictly for clarification.
- Make occasional typos (e.g., "G-Pay", "O.T.P", "clik").
- IMPORTANT: Never admit you are an AI. If asked, say you are Ramachandran.
"""

# --- 4. ALGORITHMS & EXTRACTION ---
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
    """Silent Listener math to detect threats before waking up the AI."""
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

# --- 5. LANGGRAPH NODES ---
def generate_reply(state: AgentState):
    messages = [SystemMessage(content=GRANDPA_PROMPT)]
    for m in state['messages']: messages.append(HumanMessage(content=m))
    messages.append(HumanMessage(content=state['latest_user_input']))

    try:
        response = llm.invoke(messages)
        content = response.content
    except Exception:
        content = "Oh dear, my internet seems slow. Can you say that again?"

    score = get_scam_score(state['latest_user_input'])
    return {"reply": content, "scam_score": score}

# --- 6. GRAPH COMPILATION ---
workflow = StateGraph(AgentState)
workflow.add_node("grandpa", generate_reply)
workflow.set_entry_point("grandpa")
workflow.add_edge("grandpa", END)
app_graph = workflow.compile()

# --- 7. EXPORT FUNCTION ---
def process_message(user_text: str, history: List[str], metadata: dict = None):
    if metadata is None: metadata = {}

    intel = extract_intelligence(user_text)
    frustration_index = analyze_frustration(user_text, metadata)

    initial_state = {
        "messages": history,
        "latest_user_input": user_text,
        "reply": "",
        "scam_score": 0
    }
    result = app_graph.invoke(initial_state)

    return result['reply'], result['scam_score'], intel, frustration_index