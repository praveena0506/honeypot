import os
import re
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- 1. SETUP MODEL ---
# Using the standard model ID for maximum stability
llm = ChatGroq(
    temperature=0.7,
    model_name="llama-3.1-8b-instant",
    groq_api_key=os.environ.get("GROQ_API_KEY")
)


# --- 2. DEFINE STATE ---
class AgentState(TypedDict):
    messages: List[str]
    latest_user_input: str
    reply: str
    scam_score: int


# --- 3. PERSONA ---
GRANDPA_PROMPT = """
You are 'Ramachandran', a 72-year-old retired clerk living in Chennai.
- You are confused by technology. You do not understand "apps" or "UPI" well.
- You are eager to receive the money/prize but struggle to follow instructions.
- Act naive. Ask strictly for clarification.
- Make occasional typos (e.g., "G-Pay", "O.T.P", "clik").
- IMPORTANT: Never admit you are an AI. If asked, say you are Ramachandran.
"""


# --- 4. HELPER FUNCTIONS ---
def extract_intelligence(text: str):
    """
    Scans text for UPI IDs, Phone Numbers, and Links.
    """
    # 1. UPI Regex (matches example@okaxis, number@paytm)
    upi_pattern = r'[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}'

    # 2. URL Regex
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'

    # 3. Phone Number Regex (Indian format mostly)
    phone_pattern = r'(?:\+91[\-\s]?)?[6-9]\d{9}'

    found_upis = re.findall(upi_pattern, text)
    found_links = re.findall(url_pattern, text)
    found_phones = re.findall(phone_pattern, text)

    return {
        "upiIds": found_upis,
        "phishingLinks": found_links,
        "phoneNumbers": found_phones
    }


# --- 5. NODES ---
def generate_reply(state: AgentState):
    # Prepare the prompt
    messages = [SystemMessage(content=GRANDPA_PROMPT)]

    # Add history
    for m in state['messages']:
        messages.append(HumanMessage(content=m))

    # Add the new input
    messages.append(HumanMessage(content=state['latest_user_input']))

    # Invoke Groq with Error Handling
    try:
        response = llm.invoke(messages)
        content = response.content
    except Exception as e:
        content = "Oh dear, my internet seems slow. Can you say that again?"

    # Improved Scoring Logic
    scam_keywords = ["urgent", "pay", "verify", "block", "expired", "kyc", "winner", "prize", "otp"]
    text_lower = state['latest_user_input'].lower()

    # Base score
    score = 10
    for word in scam_keywords:
        if word in text_lower:
            score += 20

    # Cap at 95
    final_score = min(score, 95)

    return {"reply": content, "scam_score": final_score}


# --- 6. GRAPH ---
workflow = StateGraph(AgentState)
workflow.add_node("grandpa", generate_reply)
workflow.set_entry_point("grandpa")
workflow.add_edge("grandpa", END)
app_graph = workflow.compile()


# --- 7. EXPORT ---
def process_message(user_text: str, history: List[str]):
    """
    Main entry point called by main.py
    """
    # 1. Run Intelligence Extraction IMMEDIATELY on the user's text
    intel = extract_intelligence(user_text)

    # 2. Run the AI Agent
    initial_state = {
        "messages": history,
        "latest_user_input": user_text,
        "reply": "",
        "scam_score": 0
    }

    result = app_graph.invoke(initial_state)

    # 3. Return everything (Reply, Score, Extracted Data)
    # THIS MATCHES THE NEW MAIN.PY EXPECTATIONS
    return result['reply'], result['scam_score'], intel