# RailwayServer.py
import os
import sys
import requests
import logging
from fastmcp import FastMCP
from dotenv import load_dotenv

# Redirect logs to stderr to keep the app connection clean
logging.basicConfig(level=logging.INFO, stream=sys.stderr, force=True)

load_dotenv()

mcp = FastMCP("IRCTC-Assistant")

# Helper to get headers
def get_headers():
    return {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": "irctc-api2.p.rapidapi.com"
    }

@mcp.tool()
def get_pnr_status(pnr: str) -> dict:
    """Fetch detailed PNR status including train time, number, stations, and passenger status."""
    logging.info(f"Fetching PNR: {pnr}")
    
    if not pnr.isdigit() or len(pnr) != 10:
        return {"error": "PNR must be exactly 10 digits"}

    url = "https://irctc-api2.p.rapidapi.com/pnrStatus"
    
    try:
        r = requests.get(url, headers=get_headers(), params={"pnr": pnr}, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", {})
        
        if not data:
            return {"error": "No data found. PNR might be invalid."}

        return {
            "pnr": pnr,
            "train_info": {
                "name": data.get("trainName", "Unknown"),
                "number": data.get("trainNumber", "Unknown"),
            },
            "journey_details": {
                "date_of_journey": data.get("doj", "N/A"),
                "departure_time": data.get("departureTime", "N/A"),
                "arrival_time": data.get("arrivalTime", "N/A"),
                "from_station": data.get("from", "N/A"),
                "to_station": data.get("to", "N/A"),
                "duration": data.get("duration", "N/A")
            },
            "status": [p.get("currentStatus") for p in data.get("passengers", [])]
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def resolve_station_code(station_name: str) -> dict:
    """
    Find the station code for a city name (e.g., 'Delhi' -> 'NDLS').
    Always use this BEFORE searching for trains if you don't know the code.
    """
    logging.info(f"Resolving station: {station_name}")
    
    if not station_name or not station_name.strip():
        return {"error": "Station name is required"}

    url = "https://irctc-api2.p.rapidapi.com/stationSearch"
    
    try:
        r = requests.get(url, headers=get_headers(), params={"code": station_name}, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        
        if not data:
            return {"error": f"No station found for '{station_name}'"}

        return {
            "match_found": True,
            "stations": [
                {
                    "name": s.get("station_name"),
                    "code": s.get("station_code"),
                    "location": f"{s.get('city_name', '')}, {s.get('state_name', '')}"
                }
                for s in data[:5]
            ]
        }
    except Exception as e:
        return {"error": f"Station search failed: {str(e)}"}

@mcp.tool()
def get_live_station_trains(source: str, destination: str, hours: int = 4) -> dict:
    """
    Fetch trains running between two stations in the next N hours.
    Requires Station CODES (e.g., 'NDLS', 'CNB').
    """
    logging.info(f"Searching live trains: {source} -> {destination} (next {hours}h)")

    if not source or not destination:
        return {"error": "Source and Destination codes are required"}

    # --- UPDATED URL AND LOGIC TO MATCH YOUR WORKING SCRIPT ---
    url = "https://irctc-api2.p.rapidapi.com/liveStation"
    
    params = {
        "source": source.upper(),
        "destination": destination.upper(),
        "hours": hours
    }
    
    try:
        r = requests.get(url, headers=get_headers(), params=params, timeout=10)
        r.raise_for_status()
        
        json_resp = r.json()
        data = json_resp.get("data", {})
        raw_trains = data.get("trains", [])

        if not raw_trains:
            return {"error": f"No trains found running from {source} to {destination} in the next {hours} hours."}

        # Format the output based on your verified output structure
        formatted_trains = []
        for t in raw_trains:
            formatted_trains.append({
                "train_number": t.get("trainNumber"),
                "train_name": t.get("trainName"),
                "scheduled_departure": t.get("scheduledDeparture"),
                "expected_departure": t.get("expectedDeparture"),
                "delay": t.get("delay", "On Time"),
                "platform": t.get("platform", "TBD")
            })
            
        return {
            "source": data.get("source"),
            "destination": data.get("destination"),
            "train_count": data.get("trainCount"),
            "trains": formatted_trains
        }

    except Exception as e:
        logging.error(f"Live Station API Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()