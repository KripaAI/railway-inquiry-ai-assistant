🚄 Indian Railways Inquiry AI Assistant

An AI-powered Indian Railways inquiry system that allows users to ask natural language questions and receive accurate, real-time railway information such as PNR status, station codes, and live train details.

This project demonstrates a tool-driven, agentic AI architecture using LLMs, MCP servers, and LangGraph, designed to avoid hallucinations and ensure reliable outputs.

✨ Features

🔍 PNR Status Inquiry

🏙️ Station Name → Station Code Resolution

🚆 Live Trains Between Two Stations

💬 Natural Language Chat Interface

🛠️ Strict Tool-Based AI (No Guessing)

📊 Real-Time Data via IRCTC APIs

🧠 System Architecture
User (Streamlit Chat UI)
        │
        ▼
LLM Agent (GPT-4o + LangGraph)
        │
        │ decides which tool to call
        ▼
FastMCP Tool Server
(PNR • Station Codes • Live Trains)
        │
        ▼
IRCTC APIs (RapidAPI)

🏗️ Project Structure
.
├── RailwayServer.py        # FastMCP tool server (Railway APIs)
├── app.py                  # Streamlit UI + LangGraph agent
├── .env                    # Environment variables (API keys)
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation

🔧 Tech Stack

Python

FastMCP – Tool server for railway operations

LangChain & LangGraph – Agent orchestration

OpenAI GPT-4o-mini – LLM

Streamlit – Chat-based UI

RapidAPI (IRCTC APIs) – Real-time railway data

⚙️ Setup Instructions
1️⃣ Clone the Repository
git clone https://github.com/your-username/indian-railways-inquiry-ai.git
cd indian-railways-inquiry-ai

2️⃣ Create & Activate Virtual Environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Configure Environment Variables

Create a .env file:

OPENAI_API_KEY=your_openai_key
RAPIDAPI_KEY=your_rapidapi_key

▶️ Running the Application
streamlit run app.py


Then open the browser at:

http://localhost:8501

💬 Example Queries

“What is the PNR status of 2749628734?”

“Station code for New Delhi”

“Trains running from NDLS to CNB in the next 4 hours”

🛡️ Design Principles

✅ Tool-first AI – LLM never guesses data

✅ Deterministic behavior using LangGraph

✅ Separation of concerns via MCP server

✅ Production-style agent architecture

🚀 Future Enhancements

Seat availability & fare inquiry

Multilingual support

Caching & rate-limit optimization

User journey history

Mobile-friendly UI

📌 Why This Project Matters

This project showcases how LLMs can be used as reliable orchestrators, not just text generators.

It is a practical example of Agentic AI + MCP + real-world APIs working together in a safe and scalable way.

📜 License

MIT License

🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to fork the repo and submit a PR.