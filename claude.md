# Claude Progress Tracker - Indian Railways AI Assistant

## Last Updated
2026-01-08

## Project Overview
An AI-powered Indian Railways inquiry system using LLMs, MCP servers, and LangGraph for real-time railway information.

## Current Project State
- **Status**: Functional
- **Branch**: main (clean, no uncommitted changes)
- **Latest Commit**: `1eef963` - Add 5 new railway tools and update documentation

## Project Structure
```
India_Railway_Tracking_System/
├── RailwayServer.py     # FastMCP tool server with 9 railway API tools
├── app.py               # Streamlit UI + LangGraph agent orchestration
├── .env                 # Environment variables (API keys)
├── requirements.txt     # Python dependencies
├── README.md            # Project documentation
└── claude.md            # This file - progress tracking
```

## Tech Stack
| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| Tool Server | FastMCP |
| Agent Framework | LangChain + LangGraph |
| LLM | OpenAI GPT-4o-mini |
| Frontend | Streamlit |
| Data Source | IRCTC APIs (RapidAPI) |

## Implemented Features (9 Tools)
1. **get_pnr_status** - Check PNR booking status (10-digit PNR)
2. **resolve_station_code** - Convert city/station names to IRCTC codes
3. **get_live_station_trains** - Find trains between stations in next N hours
4. **get_train_schedule** - Complete train route/timetable with all stops
5. **get_fare** - Ticket prices across different classes
6. **get_live_train_status** - Track current location, delay, running status
7. **check_seat_availability** - Class-wise availability with confirmation chances
8. **search_trains** - Search all trains between two stations/cities
9. **plan_journey** - Journey planning with direct trains and connecting options via major junctions

## Major City Station Mappings
| City | Stations |
|------|----------|
| Delhi/New Delhi | NDLS, ANVT, DLI, DEE, DEC, SZM |
| Mumbai | CSMT, BCT, LTT, BDTS |
| Kolkata | HWH, SDAH, KOAA |
| Chennai | MAS, MS, MSB |

## Environment Variables Required
```
OPENAI_API_KEY=your_openai_api_key
RAPIDAPI_KEY=your_rapidapi_key
```

## Run Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

## Session History

### Session: 2026-01-08
- Explored project structure and codebase
- Created claude.md for progress tracking
- **Added `plan_journey` tool** - Journey planning with direct trains and connecting options
  - Finds direct trains between source and destination
  - Searches connecting routes via 15 major junction stations
  - Calculates total journey time including layover
  - Filters connections with valid layover (45 min to 8 hours)
  - Returns recommendations for best route

---

## Pending Tasks
- None currently

## Major Junction Stations (for connections)
NDLS, CNB, MGS, HWH, CSMT, BCT, NGP, BZA, MAS, SBC, SC, ADI, JP, LKO, PNBE

## Future Enhancements (from README)
- Multilingual support (Hindi, regional languages)
- Voice input/output integration
- Booking recommendations based on availability
- ~~Journey planning with connections~~ (DONE)
- Price alerts and notifications
- Mobile-responsive PWA version
- Caching layer for frequently accessed data

## Notes
- API keys stored in `.env` file (not committed to git)
- All tools use IRCTC APIs via RapidAPI
- Station codes are case-insensitive (auto-uppercased)
- Date format for availability: DD-MM-YYYY
