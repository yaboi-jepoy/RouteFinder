import os
import json
import datetime
import requests
from dotenv import load_dotenv

#Load configurations
load_dotenv()

# NOTE: no hardcoded fallback key here on purpose — if MAPQUEST_API_KEY
# isn't set, fail loudly rather than silently using a key that might be
# stale, shared, or (as in the version pasted into chat) already exposed.
API_KEY = os.getenv("MAPQUEST_API_KEY") or os.getenv("API_KEY")
BASE_URL = "https://www.mapquestapi.com/directions/v2/route?"
LOG_FILE = "activity_log.txt"


#Appends timestamps and server events to a local text file.
def write_to_log(event_type: str, details: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{event_type.upper()}] {details}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass 


#Converts raw miles values into kilometers, rounded to 2 decimals.
def miles_to_km(miles: float) -> float:
    if miles is None: 
        return 0.0
    return round(miles * 1.60934, 2)


#Extract address fields from MapQuest locations object.
def location_summary(loc: dict) -> dict:
    lat_lng = loc.get("latLng", {}) or {}
    return {
        "address": loc.get("street", ""),
        "city": loc.get("adminArea5", ""),
        "state": loc.get("adminArea3", ""),
        "country": loc.get("adminArea1", ""),
        "postal_code": loc.get("postalCode", ""),
        "lat": lat_lng.get("lat"),
        "lng": lat_lng.get("lng"),
    }


#Organize every maneuvers into a single sequential list.
def build_steps(route: dict) -> list:
    steps = []
    step_number = 1
    for leg in route.get("legs", []) or []:
        for maneuver in leg.get("maneuvers", []) or []:
            distance_mi = maneuver.get("distance", 0)
            steps.append({
                "step": step_number,
                "instruction": maneuver.get("narrative", ""),
                "street": ", ".join(maneuver.get("streets", [])) or None,
                "distance_miles": distance_mi,
                "distance_km": miles_to_km(distance_mi),
                "time_seconds": maneuver.get("time", 0),
                "time_formatted": maneuver.get("formattedTime", ""),
                "turn_icon_url": maneuver.get("iconUrl"),
            })
            step_number += 1
    return steps


#Call the MapQuest Directions API.
def fetch_route(origin: str, destination: str, unit: str = "m") -> dict:
    if not API_KEY:
        raise RuntimeError("No MapQuest API key found. Set MAPQUEST_API_KEY in your .env file.")
    params = {
        "key": API_KEY,
        "from": origin,
        "to": destination,
        "unit": unit,
    }
    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


#Transform raw API data into a formatted structure for the UI.
def simplify_route(raw_data: dict, origin: str, destination: str) -> dict:
    info = raw_data.get("info", {}) or {}
    status_code = info.get("statuscode")

    if status_code != 0:
        messages = info.get("messages") or ["Unknown error from MapQuest."]
        return {
            "status": "error",
            "status_code": status_code,
            "message": "; ".join(messages),
        }

    route = raw_data.get("route", {}) or {}
    locations = route.get("locations", []) or []
    origin_loc = location_summary(locations[0]) if locations else {}
    destination_loc = location_summary(locations[-1]) if len(locations) > 1 else {}

    distance_mi = route.get("distance", 0)
    bbox = route.get("boundingBox", {}) or {}

    return {
        "status": "success",
        "status_code": 0,
        "query": {
            "origin": origin,
            "destination": destination,
        },
        "summary": {
            "distance_miles": distance_mi,
            "distance_km": miles_to_km(distance_mi),
            "time_seconds": route.get("time", 0),
            "time_formatted": route.get("formattedTime", ""),
            "traffic_time_seconds": route.get("realTime"),
            "fuel_used_gallons": route.get("fuelUsed"),
            "route_warnings": {
                "toll_road": route.get("hasTollRoad", False),
                "highway": route.get("hasHighway", False),
                "ferry": route.get("hasFerry", False),
                "seasonal_closure": route.get("hasSeasonalClosure", False),
                "unpaved_road": route.get("hasUnpaved", False),
                "crosses_country_border": route.get("hasCountryCross", False),
            },
        },
        "origin": origin_loc,
        "destination": destination_loc,
        "map_bounds": {
            "northeast": bbox.get("ul"),
            "southwest": bbox.get("lr"),
        },
        "steps": build_steps(route),
    }


#Fetch directions data from MapQuest and build a formatted message.
def get_route(orig: str, dest: str) -> dict:
    write_to_log("request_received", f"Origin: '{orig}' | Destination: '{dest}'")
    
    #Reject empty text fields immediately
    if not orig.strip() or not dest.strip():
        write_to_log("request_failed", "User submitted empty string inputs.")
        return {
            "status": 611,
            "message": "Missing an entry for one or both locations.",
            "data": None
        }

    #Transmit data request to endpoint pipeline
    try:
        raw_data = fetch_route(orig, dest)
    except requests.exceptions.Timeout:
        write_to_log("error", "Request to MapQuest timed out.")
        return {"status": 598, "message": "Request to MapQuest timed out.", "data": None}
    except requests.exceptions.RequestException as e:
        write_to_log("error", f"Pipeline connection breakdown: {e}")
        return {"status": 599, "message": f"Network error: {e}", "data": None}

    simplified = simplify_route(raw_data, orig, dest)

    # CASE A: Successful search
    if simplified["status"] == "success":
        write_to_log("success", f"Resolved. Steps Count: {len(simplified.get('steps', []))}")
        return {"status": 0, "data": simplified}

    status_code = simplified.get("status_code")
    write_to_log("failed", f"MapQuest error validation hit code {status_code}")
    
    # CASE B: Invalid/Wrong inputs
    if status_code == 402:
        return {"status": 402, "message": "Invalid user inputs for one or both locations.", "data": None}
    elif status_code == 611:
        return {"status": 611, "message": "Missing an entry for one or both locations.", "data": None}
    else:
        return {
            "status": status_code if status_code is not None else -1,
            "message": simplified.get("message", "Unknown MapQuest API error"),
            "data": None
        }


#Compiles route statistics into a summary string.
def summarize_route(route_data: dict) -> str:
    write_to_log("summarize", "User triggered text report generation snapshot.")
    
    s = route_data.get("summary", {}) or {}
    steps = route_data.get("steps", []) or []
    q = route_data.get("query", {}) or {}

    # Extract major named roads and filter duplicates
    major_roads = []
    for step in steps:
        street = step.get("street")
        if street and (not major_roads or major_roads[-1] != street):
            major_roads.append(street)

    # Compile the list of primary highways or transit roads used
    road_list = "None detected"
    if major_roads:
        shown = major_roads[:6]
        road_list = ", ".join(shown)
        if len(major_roads) > 6:
            road_list += f", and {len(major_roads) - 6} more"

    # Evaluate dynamic road characteristics and conditions
    road_notice = "Route favors local roads over expressways."
    if s.get("has_highways"):
        road_notice = "Route utilizes major expressways and highways."

    # Evaluate toll payment requirements
    toll_warning = "No toll roads detected along this itinerary."
    if s.get("has_tolls"):
        toll_warning = "Warning: This route includes toll gates. Electronic transit passes or cash fees required."


    # Build a clean, structured text block layout
    summary_content = [
        "TRIP OVERVIEW SUMMARY",
        "--------------------------------------------------",
        f"Trip Path    : {q.get('origin')} to {q.get('destination')}",
        f"Total Metrics: {s.get('distance_miles')} mi ({s.get('distance_km')} km) | Approx. {s.get('time_formatted')}",
        f"Total Steps  : {len(steps)} navigation directions total",
        "",
        "ROAD CONFIGURATION & NOTICES",
        "--------------------------------------------------",
        f"Main Roads   : {road_list}",
        f"Road Notice  : {road_notice}",
        "",
        "TRAVEL WARNINGS",
        "--------------------------------------------------",
        f"Toll Warning : {toll_warning}"
    ]

    # Evaluate miscellaneous safety warnings present in the telemetry data
    warnings = s.get("route_warnings", {}) or {}
    other_warnings = [name.replace("_", " ") for name, val in warnings.items() if val and name not in ["toll_road", "highway"]]
    if other_warnings:
        summary_content.append(f"Other Hazards: Heads up, route includes " + ", ".join(other_warnings) + ".")

    return "\n".join(summary_content)

