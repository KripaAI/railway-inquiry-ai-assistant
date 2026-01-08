import os
import sys
import asyncio
import streamlit as st
import nest_asyncio
from dotenv import load_dotenv

# ===============================
# ENV & ASYNC FIX
# ===============================
load_dotenv()
nest_asyncio.apply()

# ===============================
# LANGCHAIN / LANGGRAPH
# ===============================
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, SystemMessage

# ===============================
# STREAMLIT UI
# ===============================
st.set_page_config(page_title="🚄 Railway AI", page_icon="🚄")
st.title("🚄 Indian Railways AI Assistant")

with st.sidebar:
    st.header("Control Panel")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("""
    **Capabilities**
    1. PNR Status
    2. Station Code Search
    3. Live Trains
    4. Train Schedule/Route
    5. Fare Enquiry
    6. Live Train Status
    7. Seat Availability
    8. Train Search
    """)

# ===============================
# CHAT HISTORY
# ===============================
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ===============================
# MCP SERVER FILE
# ===============================
SERVER_PATH = os.path.abspath("RailwayServer.py")

# ===============================
# SYSTEM PROMPT
# ===============================
SYSTEM_PROMPT = """
You are an expert Indian Railways assistant with access to real-time IRCTC data.

Available Tools:
1. get_pnr_status: Check PNR booking status (10-digit PNR number)
2. resolve_station_code: Convert city names to station codes (use before train searches)
3. get_live_station_trains: Find trains running between stations in next few hours
4. get_train_schedule: Get complete route/timetable of a train
5. get_fare: Get ticket prices for different classes
6. get_live_train_status: Track current location and delay of a running train
7. check_seat_availability: Check seat availability (date format: DD-MM-YYYY)
8. search_trains: Find all trains between two stations

Rules:
1. If user provides city names (Delhi, Mumbai), use resolve_station_code to get codes.
2. If user already provides station CODES (NDLS, HJP, CNB), use them directly - DO NOT call resolve_station_code.
3. NEVER guess station codes or train data - always use tools.
4. For seat availability, date format is DD-MM-YYYY.
5. Format responses clearly with bullet points and tables when appropriate.
6. If a tool returns an error, explain it clearly to the user.
"""

# ===============================
# AGENT FUNCTION (FIXED)
# ===============================
async def run_agent(user_input: str):

    # 1. Initialize Client (Standard Instantiation)
    client = MultiServerMCPClient({
        "railway": {
            "command": sys.executable,
            "args": [SERVER_PATH],
            "transport": "stdio",
            "env": {**os.environ, "PYTHONUNBUFFERED": "1"}
        }
    })

    # 2. Get tools directly (This handles the connection internally in v0.1.0)
    # The error message suggests: "client = MultiServerMCPClient(...) tools = await client.get_tools()"
    tools = await client.get_tools()

    # 3. Build the Agent
    llm = ChatOpenAI(
        model="gpt-4o-mini", 
        temperature=0
    ).bind_tools(tools)

    def agent(state: MessagesState):
        return {
            "messages": [
                llm.invoke(
                    [SystemMessage(content=SYSTEM_PROMPT)] 
                    + state["messages"]
                )
            ]
        }

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    app = graph.compile()

    final_response = None

    # 4. Run the Agent with UI Streaming
    with st.status("🧠 AI is processing...", expanded=True) as status:
        async for event in app.astream(
            {"messages": [HumanMessage(content=user_input)]}
        ):

            if "agent" in event:
                msg = event["agent"]["messages"][0]
                if msg.tool_calls:
                    for tool in msg.tool_calls:
                        status.write(f"🛠️ Calling tool: `{tool['name']}`")
                        status.write(f"Arguments: {tool['args']}")

            if "tools" in event:
                for msg in event["tools"]["messages"]:
                    status.write(f"✅ Tool `{msg.name}` executed")

            if "agent" in event and not event["agent"]["messages"][0].tool_calls:
                final_response = event["agent"]["messages"][0].content

        status.update(
            label="✅ Processing Complete", 
            state="complete", 
            expanded=False
        )

    # 5. Cleanup manually if needed (though get_tools usually handles transient connections)
    # For long-running apps, Python garbage collection typically cleans up the subprocess,
    # but strictly speaking, we rely on the client destructor here.
    return final_response


# ===============================
# CHAT INPUT
# ===============================
if query := st.chat_input(" "):
    st.session_state.messages.append(
        {"role": "user", "content": query}
    )

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        try:
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(run_agent(query))

            if response:
                st.markdown(response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )
            else:
                st.error("No response generated.")
                
        except Exception as e:
            st.error(f"❌ Error: {e}")