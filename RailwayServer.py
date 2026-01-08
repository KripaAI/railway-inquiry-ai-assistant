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

# Validate API key on startup
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    logging.warning("RAPIDAPI_KEY not found in environment variables!")

# Helper to get headers
def get_headers():
    if not RAPIDAPI_KEY:
        raise ValueError("RAPIDAPI_KEY is not configured. Please set it in .env file.")
    return {
        "x-rapidapi-key": RAPIDAPI_KEY,
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

        # Handle multiple possible field names for journey date
        journey_date = (
            data.get("dateOfJourney") or
            data.get("doj") or
            data.get("journeyDate") or
            data.get("date") or
            "N/A"
        )

        return {
            "pnr": pnr,
            "train_info": {
                "name": data.get("trainName", "Unknown"),
                "number": data.get("trainNumber", "Unknown"),
            },
            "journey_details": {
                "date_of_journey": journey_date,
                "departure_time": data.get("departureTime", "N/A"),
                "arrival_time": data.get("arrivalTime", "N/A"),
                "from_station": data.get("from") or data.get("fromStation", "N/A"),
                "to_station": data.get("to") or data.get("toStation", "N/A"),
                "duration": data.get("duration", "N/A"),
                "class": data.get("class") or data.get("journeyClass", "N/A"),
                "chart_status": data.get("chartStatus") or data.get("chartPrepared", "N/A")
            },
            "passengers": [
                {
                    "number": idx + 1,
                    "booking_status": p.get("bookingStatus", "N/A"),
                    "current_status": p.get("currentStatus", "N/A")
                }
                for idx, p in enumerate(data.get("passengers", []))
            ]
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


def minutes_to_time(minutes: int) -> str:
    """Convert minutes from midnight to HH:MM format."""
    if minutes is None:
        return "N/A"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

@mcp.tool()
def get_train_schedule(train_number: str) -> dict:
    """
    Get complete schedule/route of a train with all station stops and timings.
    Use this to find all stations a train passes through.
    """
    logging.info(f"Fetching schedule for train: {train_number}")

    # Clean input
    train_number = train_number.strip()

    if not train_number.isdigit() or len(train_number) not in [4, 5]:
        return {"error": "Train number must be 4-5 digits"}

    url = "https://irctc-api2.p.rapidapi.com/trainSchedule"

    try:
        r = requests.get(url, headers=get_headers(),
                        params={"trainNumber": train_number}, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", [])

        if not data:
            return {"error": f"No schedule found for train {train_number}"}

        # Format the schedule - data is an array of stations
        stops = []
        major_stops = []

        for station in data:
            std_min = station.get("std_min")
            is_stop = station.get("stop", False)

            stop_info = {
                "station_name": station.get("station_name", "N/A"),
                "station_code": station.get("station_code", "N/A"),
                "state": station.get("state_name", "N/A"),
                "departure_time": minutes_to_time(std_min),
                "day": station.get("day", 1),
                "platform": station.get("platform_number", "N/A"),
                "is_stop": is_stop
            }
            stops.append(stop_info)

            # Collect major stops (where train actually stops)
            if is_stop:
                major_stops.append(stop_info)

        return {
            "train_number": train_number,
            "total_stations": len(stops),
            "total_stops": len(major_stops),
            "major_stops": major_stops,
            "full_route": stops
        }
    except Exception as e:
        logging.error(f"Train Schedule API Error: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_fare(train_number: str, source: str, destination: str, date: str = None) -> dict:
    """
    Get ticket fare/price for a train between two stations.
    Uses trainAvailability API which includes fare information.

    Parameters:
    - train_number: 4-5 digit train number (e.g., '12565')
    - source: Source station CODE (e.g., 'HJP')
    - destination: Destination station CODE (e.g., 'NDLS')
    - date: Optional date in DD-MM-YYYY format (defaults to tomorrow)
    """
    logging.info(f"Fetching fare: Train {train_number}, {source} -> {destination}")

    train_number = train_number.strip()
    source = source.strip().upper()
    destination = destination.strip().upper()

    if not train_number or not source or not destination:
        return {"error": "Train number, source, and destination are required"}

    # Use trainAvailability API which includes fare data
    url = "https://irctc-api2.p.rapidapi.com/trainAvailability"

    # Default to a near future date if not provided
    if not date:
        from datetime import datetime, timedelta
        tomorrow = datetime.now() + timedelta(days=1)
        date = tomorrow.strftime("%d-%m-%Y")

    try:
        r = requests.get(url, headers=get_headers(), params={
            "source": source,
            "destination": destination,
            "date": date
        }, timeout=20)
        r.raise_for_status()
        data = r.json().get("data", [])

        if not data:
            return {"error": f"No trains found from {source} to {destination}"}

        # Find the specific train
        train_data = None
        for train in data:
            if train.get("trainNumber") == train_number:
                train_data = train
                break

        if not train_data:
            return {"error": f"Train {train_number} not found on route {source} to {destination}"}

        # Extract fare information
        fares = []
        for cls in train_data.get("classAvailability", []):
            fares.append({
                "class": cls.get("class", "N/A"),
                "fare": f"₹{cls.get('fare', 'N/A')}",
                "availability": cls.get("displayStatus", "N/A")
            })

        return {
            "train_number": train_number,
            "train_name": train_data.get("trainName", "Unknown"),
            "source": train_data.get("from", {}).get("name", source),
            "destination": train_data.get("to", {}).get("name", destination),
            "distance_km": train_data.get("distanceKm", "N/A"),
            "duration": train_data.get("duration", "N/A"),
            "fares_by_class": fares
        }
    except Exception as e:
        logging.error(f"Fare API Error: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_live_train_status(train_number: str, date: str = None) -> dict:
    """
    Get live running status of a train - current location, delay, etc.
    Date format: YYYY-MM-DD (optional, defaults to today).
    """
    logging.info(f"Fetching live status: Train {train_number}, Date: {date}")

    train_number = train_number.strip()

    if not train_number.isdigit() or len(train_number) not in [4, 5]:
        return {"error": "Train number must be 4-5 digits"}

    url = "https://irctc-api2.p.rapidapi.com/liveTrainStatus"

    params = {"trainNumber": train_number}
    if date:
        params["date"] = date

    try:
        r = requests.get(url, headers=get_headers(), params=params, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", {})

        if not data:
            return {"error": f"No live status found for train {train_number}. Train may not be running today."}

        # Current position details
        current = data.get("currentStation", {})

        return {
            "train_number": data.get("trainNumber", train_number),
            "train_name": data.get("trainName", "Unknown"),
            "running_status": data.get("status", "Unknown"),
            "delay_minutes": data.get("delay", 0),
            "current_station": {
                "name": current.get("stationName", "N/A"),
                "code": current.get("stationCode", "N/A"),
                "arrived": current.get("actualArrival", "N/A"),
                "departed": current.get("actualDeparture", "N/A")
            },
            "last_updated": data.get("lastUpdated", "N/A"),
            "source": data.get("source", "N/A"),
            "destination": data.get("destination", "N/A")
        }
    except Exception as e:
        logging.error(f"Live Train Status API Error: {e}")
        return {"error": str(e)}


@mcp.tool()
def check_seat_availability(source: str, destination: str, date: str, train_number: str = None) -> dict:
    """
    Check seat/train availability between two stations on a specific date.
    Returns all trains with their class-wise availability, fares, and confirmation chances.

    Parameters:
    - source: Source station CODE (e.g., 'NDLS')
    - destination: Destination station CODE (e.g., 'HJP')
    - date: Journey date in DD-MM-YYYY format (e.g., '13-01-2026')
    - train_number: Optional - filter results for a specific train
    """
    logging.info(f"Checking availability: {source}->{destination}, {date}, Train: {train_number}")

    source = source.strip().upper()
    destination = destination.strip().upper()

    if not source or not destination or not date:
        return {"error": "Source, destination, and date are required"}

    url = "https://irctc-api2.p.rapidapi.com/trainAvailability"

    try:
        r = requests.get(url, headers=get_headers(), params={
            "source": source,
            "destination": destination,
            "date": date
        }, timeout=20)
        r.raise_for_status()
        data = r.json().get("data", [])

        if not data:
            return {"error": f"No trains found from {source} to {destination} on {date}"}

        # Format train availability
        trains = []
        for train in data:
            # If train_number specified, filter for that train only
            if train_number and train.get("trainNumber") != train_number:
                continue

            class_availability = []
            for cls in train.get("classAvailability", []):
                class_availability.append({
                    "class": cls.get("class", "N/A"),
                    "status": cls.get("displayStatus", "N/A"),
                    "availability": cls.get("availability", "N/A"),
                    "fare": f"₹{cls.get('fare', 'N/A')}",
                    "confirmation_chance": cls.get("prediction", "N/A")
                })

            trains.append({
                "train_number": train.get("trainNumber", "N/A"),
                "train_name": train.get("trainName", "N/A"),
                "from": train.get("from", {}).get("name", source),
                "to": train.get("to", {}).get("name", destination),
                "departure": train.get("departure", "N/A"),
                "arrival": train.get("arrival", "N/A"),
                "duration": train.get("duration", "N/A"),
                "running_days": train.get("runningDays", "N/A"),
                "classes_available": train.get("allClasses", []),
                "class_availability": class_availability
            })

        if not trains:
            return {"error": f"Train {train_number} not found on this route for {date}"}

        return {
            "source": source,
            "destination": destination,
            "date": date,
            "trains_found": len(trains),
            "trains": trains
        }
    except Exception as e:
        logging.error(f"Seat Availability API Error: {e}")
        return {"error": str(e)}


# Delhi area stations mapping
DELHI_STATIONS = ["NDLS", "ANVT", "DLI", "DEE", "DEC", "SZM"]
MUMBAI_STATIONS = ["CSMT", "BCT", "LTT", "BDTS"]
KOLKATA_STATIONS = ["HWH", "SDAH", "KOAA"]
CHENNAI_STATIONS = ["MAS", "MS", "MSB"]

CITY_STATION_MAP = {
    "DELHI": DELHI_STATIONS,
    "NEW DELHI": DELHI_STATIONS,
    "MUMBAI": MUMBAI_STATIONS,
    "KOLKATA": KOLKATA_STATIONS,
    "CHENNAI": CHENNAI_STATIONS
}

@mcp.tool()
def search_trains(source: str, destination: str, date: str = None) -> dict:
    """
    Search for all trains between two stations/cities.
    For major cities (Delhi, Mumbai, Kolkata, Chennai), searches ALL stations in that city.

    Parameters:
    - source: Station CODE (NDLS) or city name (Delhi)
    - destination: Station CODE (HJP) or city name (Mumbai)
    - date: DD-MM-YYYY format (optional, defaults to tomorrow)
    """
    logging.info(f"Searching trains: {source} -> {destination}")

    source = source.strip().upper()
    destination = destination.strip().upper()

    if not source or not destination:
        return {"error": "Source and destination are required"}

    # Expand city names to multiple stations
    source_stations = CITY_STATION_MAP.get(source, [source])
    dest_stations = CITY_STATION_MAP.get(destination, [destination])

    # Use trainAvailability API
    url = "https://irctc-api2.p.rapidapi.com/trainAvailability"

    # Default to tomorrow if no date provided
    if not date:
        from datetime import datetime, timedelta
        tomorrow = datetime.now() + timedelta(days=1)
        date = tomorrow.strftime("%d-%m-%Y")

    all_trains = []
    searched_routes = []

    # Search all combinations of source and destination stations
    for src in source_stations:
        for dest in dest_stations:
            try:
                r = requests.get(url, headers=get_headers(), params={
                    "source": src,
                    "destination": dest,
                    "date": date
                }, timeout=20)

                if r.status_code == 200:
                    data = r.json().get("data", [])
                    searched_routes.append(f"{src} → {dest}")

                    for t in data:
                        # Avoid duplicates
                        train_num = t.get("trainNumber")
                        if not any(tr["train_number"] == train_num for tr in all_trains):
                            all_trains.append({
                                "train_number": train_num,
                                "train_name": t.get("trainName", "N/A"),
                                "source_station": f"{t.get('from', {}).get('name', 'N/A')} ({t.get('from', {}).get('code', src)})",
                                "destination_station": f"{t.get('to', {}).get('name', 'N/A')} ({t.get('to', {}).get('code', dest)})",
                                "departure": t.get("departure", "N/A"),
                                "arrival": t.get("arrival", "N/A"),
                                "duration": t.get("duration", "N/A"),
                                "run_days": t.get("runningDays", "N/A"),
                                "classes": t.get("allClasses", [])
                            })
            except Exception as e:
                logging.error(f"Error searching {src} to {dest}: {e}")
                continue

    if not all_trains:
        return {"error": f"No trains found from {source} to {destination}"}

    # Sort by departure time
    all_trains.sort(key=lambda x: x["departure"])

    return {
        "search_query": f"{source} to {destination}",
        "routes_searched": searched_routes,
        "date": date,
        "train_count": len(all_trains),
        "trains": all_trains
    }


if __name__ == "__main__":
    mcp.run()