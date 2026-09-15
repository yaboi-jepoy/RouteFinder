import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# NOTE: no hardcoded fallback key here on purpose — if MAPQUEST_API_KEY
# isn't set, fail loudly rather than silently using a key that might be
# stale, shared, or (as in the version pasted into chat) already exposed.
API_KEY = os.getenv("MAPQUEST_API_KEY") or os.getenv("API_KEY")
BASE_URL = "https://www.mapquestapi.com/directions/v2/route"
OUTPUT_FILE = "route_output.json"


def miles_to_km(miles):
    """Convert miles to kilometers, rounded to 2 decimals."""
    return round(miles * 1.60934, 2)


def location_summary(loc):
    """Pull out just the address fields the frontend needs from a
    MapQuest 'location' object (used for both origin and destination)."""
    lat_lng = loc.get("latLng", {})
    return {
        "address": loc.get("street", ""),
        "city": loc.get("adminArea5", ""),
        "state": loc.get("adminArea3", ""),
        "country": loc.get("adminArea1", ""),
        "postal_code": loc.get("postalCode", ""),
        "lat": lat_lng.get("lat"),
        "lng": lat_lng.get("lng"),
    }


def build_steps(route):
    """Flatten every leg's maneuvers into one numbered turn-by-turn list."""
    steps = []
    step_number = 1
    for leg in route.get("legs", []):
        for maneuver in leg.get("maneuvers", []):
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


def fetch_route(origin, destination, unit="m"):
    """Call the MapQuest Directions API and return the raw JSON response.
    unit: 'm' for miles, 'k' for kilometers (MapQuest's own unit switch)."""
    if not API_KEY:
        raise RuntimeError(
            "No MapQuest API key found. Set MAPQUEST_API_KEY in your .env file."
        )
    params = {
        "key": API_KEY,
        "from": origin,
        "to": destination,
        "unit": unit,
    }
    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def simplify_route(raw_data, origin, destination):
    """Transform MapQuest's raw JSON response into the simplified
    structure the frontend will actually read."""
    info = raw_data.get("info", {})
    status_code = info.get("statuscode")

    if status_code != 0:
        messages = info.get("messages") or ["Unknown error from MapQuest."]
        return {
            "status": "error",
            "status_code": status_code,
            "message": "; ".join(messages),
        }

    route = raw_data.get("route", {})
    locations = route.get("locations", [])
    origin_loc = location_summary(locations[0]) if locations else {}
    destination_loc = location_summary(
        locations[-1]) if len(locations) > 1 else {}

    distance_mi = route.get("distance", 0)
    bbox = route.get("boundingBox", {})

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


def summarize_route(simplified):
    """Turn a simplified route dict into a short, human-readable summary
    paragraph — used by the GUI's 'Summarize' button."""
    if simplified.get("status") != "success":
        return simplified.get("message", "No route available to summarize.")

    s = simplified["summary"]
    steps = simplified.get("steps", [])
    q = simplified["query"]

    lines = []
    lines.append(f"{q['origin']} to {q['destination']}")
    lines.append(
        f"{s['distance_miles']} mi ({s['distance_km']} km), "
        f"about {s['time_formatted']}."
    )

    # Pull out the major named roads (skip short/unnamed maneuvers like
    # "Turn left" with no street, dedupe consecutive repeats)
    major_roads = []
    for step in steps:
        street = step.get("street")
        if street and (not major_roads or major_roads[-1] != street):
            major_roads.append(street)

    if major_roads:
        shown = major_roads[:6]
        road_list = ", ".join(shown)
        if len(major_roads) > 6:
            road_list += f", and {len(major_roads) - 6} more"
        lines.append(f"Main roads: {road_list}.")

    warnings = s.get("route_warnings", {})
    flagged = [name.replace("_", " ") for name, val in warnings.items() if val]
    if flagged:
        lines.append("Heads up: route includes " + ", ".join(flagged) + ".")

    lines.append(f"{len(steps)} turn-by-turn steps total.")

    return "\n".join(lines)


def get_route(orig, dest):
    """Kept for backward compatibility with the existing GUI call site.
    Now returns the simplified structure (with 'steps', 'summary', etc.)
    instead of the raw MapQuest payload."""
    try:
        raw_data = fetch_route(orig, dest)
    except requests.exceptions.Timeout:
        return {"status": 598, "message": "Request to MapQuest timed out."}
    except requests.exceptions.RequestException as e:
        return {"status": 599, "message": f"Network error: {e}"}

    simplified = simplify_route(raw_data, orig, dest)

    if simplified["status"] == "success":
        return {"status": 0, "data": simplified}

    status_code = simplified.get("status_code")
    if status_code == 402:
        return {"status": 402, "message": "Invalid user inputs for one or both locations"}
    elif status_code == 611:
        return {"status": 611, "message": "Missing an entry for one or both locations"}
    else:
        return {
            "status": status_code if status_code is not None else -1,
            "message": simplified.get("message", "Unknown MapQuest API error"),
        }


def save_json(data, filepath=OUTPUT_FILE):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved simplified route data to {filepath}")


def main():
    origin = input("Enter starting address: ").strip()
    destination = input("Enter destination address: ").strip()

    print("Fetching route from MapQuest...")
    result = get_route(origin, destination)

    if result["status"] == 0:
        simplified = result["data"]
        save_json(simplified)
        print("\n" + summarize_route(simplified))
    else:
        print(f"Error: {result.get('message')}")


if __name__ == "__main__":
    main()
