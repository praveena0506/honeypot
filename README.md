Project Grandpa: Autonomous AI Honeypot 🍯👴

Project Grandpa is an autonomous agentic system designed to intercept financial scammers, waste their time, and harvest actionable threat intelligence. It bridges mobile communication (SMS/Telegram) with cloud-native AI to turn the tables on attackers

.Note: Replace the image above with your own system architecture diagram (e.g., from Excalidraw or a whiteboard sketch). It significantly increases project credibility.🚀 Key FeaturesAutonomous Interception: Bridges Android SMS and Telegram to an AI-driven backend, enabling real-time detection without manual intervention.

Adaptive Persona (DSPy): Uses DSPy to modulate the agent’s "frustration levels." As scammers get aggressive, the agent becomes progressively more confused, keeping them engaged in a loop.Intelligent Extraction: Automated pipeline to scrape UPI IDs, phishing links, and threat metadata from scammer chat logs.Agentic Workflow

(LangGraph): Orchestrates complex, stateful conversations that maintain context and persona consistency throughout the attack.🛠 Tech StackComponentTechnologyBackendPython, FastAPIAgentic FrameworkLangGraph, DSPyLLM InferenceGroq (Llama-3.1-8B-Instant)Mobile BridgeMacroDroid (SMS/Notification Forwarding)CommunicationTelegram (Telethon), SMS Webhooks🏗 Architecture OverviewThe system operates on a "Listener-Brain-Harvester" flow:Listener: MacroDroid captures incoming SMS/Notifications on the device and triggers a webhook.Brain: FastAPI receives the payload, and LangGraph orchestrates the stateful LLM response.Harvester: The system performs regex-based intelligence extraction on scammer messages before logging.

⚙️ Getting StartedPrerequisitesPython 3.10+Groq API Key (Sign up at Groq Console)Telegram API ID/Hash (If using the Telegram module)InstallationClone the repository:Bashgit clone https://github.com/praveena0506/honeypot.git
cd honeypot
Setup Virtual Environment:Bashpython -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
Install Dependencies:Bashpip install -r requirements.txt
Environment Configuration:Create a .env file in the root directory:Code snippetGROQ_API_KEY=your_groq_api_key_here
TELEGRAM_API_ID=your_id
TELEGRAM_API_HASH=your_hash
🛡 Security NoticeThis project is for educational and security research purposes only. Do not deploy this in a way that interacts with real, unsuspecting victims. Always use a dedicated/burner environment when testing.📜 LicenseDistributed under the MIT License. See LICENSE for more information.
