import os
import json
import requests


API_KEY = os.environ.get("MAPQUEST_API_KEY", "EGVIJZBu6OlzjazQolRueK1VFVfoi30D")
BASE_URL = "http://www.mapquestapi.com/directions/v2/route"
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
    if info.get("statuscode") != 0:
        messages = info.get("messages") or ["Unknown error from MapQuest."]
        return {
            "status": "error",
            "message": "; ".join(messages),
        }

    route = raw_data["route"]
    locations = route.get("locations", [])
    origin_loc = location_summary(locations[0]) if locations else {}
    destination_loc = location_summary(locations[-1]) if len(locations) > 1 else {}

    distance_mi = route.get("distance", 0)
    bbox = route.get("boundingBox", {})

    return {
        "status": "success",
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


def save_json(data, filepath=OUTPUT_FILE):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved simplified route data to {filepath}")


def main():
    origin = input("Enter starting address: ").strip()
    destination = input("Enter destination address: ").strip()

    print("Fetching route from MapQuest...")
    raw_data = fetch_route(origin, destination)

    simplified = simplify_route(raw_data, origin, destination)
    save_json(simplified)

    if simplified["status"] == "success":
        s = simplified["summary"]
        print(f"\n{origin} -> {destination}")
        print(f"Distance: {s['distance_miles']} mi ({s['distance_km']} km)")
        print(f"Time: {s['time_formatted']}")
        print(f"Steps: {len(simplified['steps'])}")
    else:
        print(f"Error: {simplified['message']}")


if __name__ == "__main__":
    main()
