# RailwayServer.py
import os
import sys
import requests
import logging
from datetime import datetime, timedelta
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


def normalize_date(date_str: str) -> str:
    """
    Normalize various date formats to DD-MM-YYYY.
    Handles: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, and assumes current year if missing.
    Returns None if date is invalid.
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Already in DD-MM-YYYY format
    if len(date_str) == 10 and date_str[2] == '-' and date_str[5] == '-':
        try:
            datetime.strptime(date_str, "%d-%m-%Y")
            return date_str
        except ValueError:
            pass

    # DD/MM/YYYY format
    if '/' in date_str:
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                if len(parts[2]) == 4:  # DD/MM/YYYY
                    parsed = datetime.strptime(date_str, "%d/%m/%Y")
                    return parsed.strftime("%d-%m-%Y")
                elif len(parts[0]) == 4:  # YYYY/MM/DD
                    parsed = datetime.strptime(date_str, "%Y/%m/%d")
                    return parsed.strftime("%d-%m-%Y")
        except ValueError:
            pass

    # YYYY-MM-DD format (ISO)
    if len(date_str) == 10 and date_str[4] == '-':
        try:
            parsed = datetime.strptime(date_str, "%Y-%m-%d")
            return parsed.strftime("%d-%m-%Y")
        except ValueError:
            pass

    return None


def get_default_date(days_ahead: int = 1) -> str:
    """Get a default date (tomorrow by default) in DD-MM-YYYY format."""
    target = datetime.now() + timedelta(days=days_ahead)
    return target.strftime("%d-%m-%Y")

@mcp.tool()
def get_pnr_status(pnr: str) -> dict:
    """Fetch detailed PNR status including train time, number, stations, and passenger status."""
    logging.info(f"Fetching PNR: {pnr}")

    if not pnr:
        return {"error": "PNR number is required"}

    pnr = pnr.strip()

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
    if minutes is None or minutes < 0:
        return "N/A"
    # Handle times that might span multiple days
    hours = (minutes // 60) % 24
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

@mcp.tool()
def get_train_schedule(train_number: str) -> dict:
    """
    Get complete schedule/route of a train with all station stops and timings.
    Use this to find all stations a train passes through.
    """
    logging.info(f"Fetching schedule for train: {train_number}")

    if not train_number:
        return {"error": "Train number is required"}

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

    if not train_number or not source or not destination:
        return {"error": "Train number, source, and destination are required"}

    train_number = train_number.strip()
    source = source.strip().upper()
    destination = destination.strip().upper()

    # Use trainAvailability API which includes fare data
    url = "https://irctc-api2.p.rapidapi.com/trainAvailability"

    # Default to a near future date if not provided, or normalize provided date
    if not date:
        date = get_default_date()
    else:
        normalized = normalize_date(date)
        if normalized:
            date = normalized

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
    Date format: DD-MM-YYYY (optional, defaults to today).
    """
    logging.info(f"Fetching live status: Train {train_number}, Date: {date}")

    if not train_number:
        return {"error": "Train number is required"}

    train_number = train_number.strip()

    if not train_number.isdigit() or len(train_number) not in [4, 5]:
        return {"error": "Train number must be 4-5 digits"}

    url = "https://irctc-api2.p.rapidapi.com/liveTrainStatus"

    params = {"trainNumber": train_number}
    if date:
        # First normalize to DD-MM-YYYY, then convert to YYYY-MM-DD for this API
        normalized = normalize_date(date)
        if normalized:
            # Convert DD-MM-YYYY to YYYY-MM-DD for the API
            parts = normalized.split("-")
            date = f"{parts[2]}-{parts[1]}-{parts[0]}"
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

    # Normalize date format
    normalized = normalize_date(date)
    if normalized:
        date = normalized

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
    # Major metros
    "DELHI": DELHI_STATIONS,
    "NEW DELHI": DELHI_STATIONS,
    "MUMBAI": MUMBAI_STATIONS,
    "KOLKATA": KOLKATA_STATIONS,
    "CHENNAI": CHENNAI_STATIONS,
    # Bihar
    "HAJIPUR": ["HJP"],
    "PATNA": ["PNBE", "PPTA", "RJPB"],
    "MUZAFFARPUR": ["MFP"],
    "GAYA": ["GAYA"],
    "DARBHANGA": ["DBG"],
    # UP
    "LUCKNOW": ["LKO", "LJN"],
    "VARANASI": ["BSB", "BCY"],
    "KANPUR": ["CNB"],
    "ALLAHABAD": ["PRYJ", "ALD"],
    "PRAYAGRAJ": ["PRYJ", "ALD"],
    "AGRA": ["AGC", "AF"],
    "GORAKHPUR": ["GKP"],
    # Rajasthan
    "JAIPUR": ["JP"],
    "JODHPUR": ["JU"],
    "UDAIPUR": ["UDZ"],
    "AJMER": ["AII"],
    # Gujarat
    "AHMEDABAD": ["ADI"],
    "SURAT": ["ST"],
    "VADODARA": ["BRC"],
    # MP
    "BHOPAL": ["BPL"],
    "INDORE": ["INDB"],
    "JABALPUR": ["JBP"],
    # South
    "BANGALORE": ["SBC", "BNCE"],
    "BENGALURU": ["SBC", "BNCE"],
    "HYDERABAD": ["SC", "HYB"],
    "SECUNDERABAD": ["SC"],
    "COIMBATORE": ["CBE"],
    "TRIVANDRUM": ["TVC"],
    "KOCHI": ["ERS"],
    # East
    "BHUBANESWAR": ["BBS"],
    "RANCHI": ["RNC"],
    "GUWAHATI": ["GHY"],
    # Punjab/Haryana
    "AMRITSAR": ["ASR"],
    "CHANDIGARH": ["CDG"],
    "LUDHIANA": ["LDH"],
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

    # Default to tomorrow if no date provided, or normalize provided date
    if not date:
        date = get_default_date()
    else:
        normalized = normalize_date(date)
        if normalized:
            date = normalized

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


# Major junction stations for connections
MAJOR_JUNCTIONS = [
    "NDLS",  # New Delhi
    "CNB",   # Kanpur Central
    "MGS",   # Mughal Sarai (Pt. Deen Dayal Upadhyaya Jn)
    "HWH",   # Howrah
    "CSMT",  # Mumbai CST
    "BCT",   # Mumbai Central
    "NGP",   # Nagpur
    "BZA",   # Vijayawada
    "MAS",   # Chennai Central
    "SBC",   # Bangalore
    "SC",    # Secunderabad
    "ADI",   # Ahmedabad
    "JP",    # Jaipur
    "LKO",   # Lucknow
    "PNBE",  # Patna
]


def parse_time_to_minutes(time_str: str) -> int:
    """Convert HH:MM time string to minutes from midnight."""
    if not time_str or time_str == "N/A":
        return -1
    try:
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return -1


def parse_duration_to_minutes(duration_str: str) -> int:
    """Convert duration string like '5h 30m' or '5:30' to minutes."""
    if not duration_str or duration_str == "N/A":
        return -1
    try:
        # Handle "5h 30m" format
        if "h" in duration_str:
            hours = 0
            mins = 0
            parts = duration_str.lower().replace("m", "").split("h")
            hours = int(parts[0].strip())
            if len(parts) > 1 and parts[1].strip():
                mins = int(parts[1].strip())
            return hours * 60 + mins
        # Handle "HH:MM" format
        elif ":" in duration_str:
            parts = duration_str.split(":")
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return int(duration_str)
    except:
        return -1


def minutes_to_duration(mins: int) -> str:
    """Convert minutes to 'Xh Ym' format."""
    if mins < 0:
        return "N/A"
    hours = mins // 60
    minutes = mins % 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def resolve_station_code_internal(station_name: str) -> list:
    """
    Internal helper to resolve station code from city/station name.
    Returns list of station codes.
    """
    station_name = station_name.strip().upper()

    # Check if it's already a known city
    if station_name in CITY_STATION_MAP:
        return CITY_STATION_MAP[station_name]

    # Check if it looks like a station code (2-5 uppercase letters)
    if len(station_name) <= 5 and station_name.isalpha():
        return [station_name]

    # Otherwise, try to resolve via API
    try:
        url = "https://irctc-api2.p.rapidapi.com/stationSearch"
        r = requests.get(url, headers=get_headers(), params={"code": station_name}, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                # Return the first matching station code
                return [data[0].get("station_code", station_name)]
    except Exception as e:
        logging.error(f"Station resolution failed for {station_name}: {e}")

    return [station_name]


@mcp.tool()
def plan_journey(source: str, destination: str, date: str = None, max_connections: int = 1) -> dict:
    """
    Plan a journey between two stations, finding direct trains and connecting options.
    Useful when no direct train exists or to find alternative routes.

    Parameters:
    - source: Source station CODE or city name (e.g., 'NDLS', 'Delhi', 'Hajipur')
    - destination: Destination station CODE or city name (e.g., 'HWH', 'Kolkata', 'Hajipur')
    - date: Journey date in DD-MM-YYYY format (optional, defaults to tomorrow)
    - max_connections: Maximum number of connections (default: 1, max: 2)

    Returns direct trains and connecting options via major junctions with:
    - Total journey time
    - Layover duration at connecting station
    - Train details for each leg
    """
    logging.info(f"Planning journey: {source} -> {destination}, Date: {date}")

    source = source.strip().upper()
    destination = destination.strip().upper()

    if not source or not destination:
        return {"error": "Source and destination are required"}

    # Resolve station codes (handles city names like "Hajipur" -> "HJP")
    source_stations = resolve_station_code_internal(source)
    dest_stations = resolve_station_code_internal(destination)

    logging.info(f"Resolved stations: {source} -> {source_stations}, {destination} -> {dest_stations}")

    # Default to tomorrow if no date, or normalize provided date
    if not date:
        date = get_default_date()
    else:
        normalized = normalize_date(date)
        if normalized:
            date = normalized

    url = "https://irctc-api2.p.rapidapi.com/trainAvailability"

    # Step 1: Find direct trains
    direct_trains = []
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
                    for t in data:
                        train_num = t.get("trainNumber")
                        if not any(tr["train_number"] == train_num for tr in direct_trains):
                            duration_mins = parse_duration_to_minutes(t.get("duration", "N/A"))
                            direct_trains.append({
                                "train_number": train_num,
                                "train_name": t.get("trainName", "N/A"),
                                "from_station": t.get("from", {}).get("name", src),
                                "from_code": t.get("from", {}).get("code", src),
                                "to_station": t.get("to", {}).get("name", dest),
                                "to_code": t.get("to", {}).get("code", dest),
                                "departure": t.get("departure", "N/A"),
                                "arrival": t.get("arrival", "N/A"),
                                "duration": t.get("duration", "N/A"),
                                "duration_mins": duration_mins,
                                "classes": t.get("allClasses", []),
                                "run_days": t.get("runningDays", "N/A")
                            })
            except Exception as e:
                logging.error(f"Error searching direct {src} to {dest}: {e}")
                continue

    # Sort direct trains by duration
    direct_trains.sort(key=lambda x: x.get("duration_mins", 9999))

    # Step 2: Find connecting routes via major junctions
    connecting_routes = []

    if max_connections >= 1:
        # Determine which junctions to try (exclude source/dest stations)
        junctions_to_try = [j for j in MAJOR_JUNCTIONS
                           if j not in source_stations and j not in dest_stations]

        for junction in junctions_to_try[:8]:  # Limit to 8 junctions to avoid too many API calls
            leg1_trains = []
            leg2_trains = []

            # Find trains from source to junction
            for src in source_stations:
                try:
                    r = requests.get(url, headers=get_headers(), params={
                        "source": src,
                        "destination": junction,
                        "date": date
                    }, timeout=15)

                    if r.status_code == 200:
                        data = r.json().get("data", [])
                        for t in data:
                            leg1_trains.append({
                                "train_number": t.get("trainNumber"),
                                "train_name": t.get("trainName", "N/A"),
                                "from_code": t.get("from", {}).get("code", src),
                                "to_code": junction,
                                "departure": t.get("departure", "N/A"),
                                "arrival": t.get("arrival", "N/A"),
                                "duration": t.get("duration", "N/A"),
                                "duration_mins": parse_duration_to_minutes(t.get("duration", "N/A"))
                            })
                except:
                    continue

            if not leg1_trains:
                continue

            # Find trains from junction to destination
            for dest in dest_stations:
                try:
                    r = requests.get(url, headers=get_headers(), params={
                        "source": junction,
                        "destination": dest,
                        "date": date
                    }, timeout=15)

                    if r.status_code == 200:
                        data = r.json().get("data", [])
                        for t in data:
                            leg2_trains.append({
                                "train_number": t.get("trainNumber"),
                                "train_name": t.get("trainName", "N/A"),
                                "from_code": junction,
                                "to_code": t.get("to", {}).get("code", dest),
                                "departure": t.get("departure", "N/A"),
                                "arrival": t.get("arrival", "N/A"),
                                "duration": t.get("duration", "N/A"),
                                "duration_mins": parse_duration_to_minutes(t.get("duration", "N/A"))
                            })
                except:
                    continue

            if not leg2_trains:
                continue

            # Match leg1 and leg2 trains with valid layover times
            for l1 in leg1_trains[:5]:  # Top 5 for leg1
                l1_arrival_mins = parse_time_to_minutes(l1["arrival"])
                if l1_arrival_mins < 0:
                    continue

                for l2 in leg2_trains[:5]:  # Top 5 for leg2
                    l2_departure_mins = parse_time_to_minutes(l2["departure"])
                    if l2_departure_mins < 0:
                        continue

                    # Calculate layover (handle day change)
                    layover = l2_departure_mins - l1_arrival_mins
                    if layover < 0:
                        layover += 24 * 60  # Next day connection

                    # Valid layover: 45 minutes to 8 hours
                    if 45 <= layover <= 480:
                        total_duration = (l1.get("duration_mins", 0) +
                                         layover +
                                         l2.get("duration_mins", 0))

                        connecting_routes.append({
                            "type": "connecting",
                            "via_station": junction,
                            "total_duration": minutes_to_duration(total_duration),
                            "total_duration_mins": total_duration,
                            "layover": minutes_to_duration(layover),
                            "layover_mins": layover,
                            "leg1": {
                                "train_number": l1["train_number"],
                                "train_name": l1["train_name"],
                                "from": l1["from_code"],
                                "to": junction,
                                "departure": l1["departure"],
                                "arrival": l1["arrival"],
                                "duration": l1["duration"]
                            },
                            "leg2": {
                                "train_number": l2["train_number"],
                                "train_name": l2["train_name"],
                                "from": junction,
                                "to": l2["to_code"],
                                "departure": l2["departure"],
                                "arrival": l2["arrival"],
                                "duration": l2["duration"]
                            }
                        })

    # Sort connecting routes by total duration
    connecting_routes.sort(key=lambda x: x.get("total_duration_mins", 9999))

    # Limit results
    direct_trains = direct_trains[:10]
    connecting_routes = connecting_routes[:5]

    if not direct_trains and not connecting_routes:
        return {"error": f"No routes found from {source} to {destination}. Try different stations or dates."}

    return {
        "journey_query": f"{source} to {destination}",
        "date": date,
        "direct_trains": {
            "count": len(direct_trains),
            "trains": direct_trains
        },
        "connecting_options": {
            "count": len(connecting_routes),
            "routes": connecting_routes
        },
        "recommendation": (
            f"Direct train available - {direct_trains[0]['train_name']} ({direct_trains[0]['duration']})"
            if direct_trains else
            f"No direct trains. Best connection via {connecting_routes[0]['via_station']} ({connecting_routes[0]['total_duration']})"
            if connecting_routes else
            "No routes found"
        )
    }


if __name__ == "__main__":
    mcp.run()