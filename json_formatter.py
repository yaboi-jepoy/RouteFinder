import urllib.parse
import json
import requests

def get_route_json(orig: str, dest: str) -> str:
    """
    Fetches route data from MapQuest and returns a standardized JSON response
    for the frontend, handling success and error states uniformly.
    """
    main_api = "https://www.mapquestapi.com/directions/v2/route?"
    key = "EGVIJZBu6OlzjazQolRueK1VFVfoi30D"
    
    # 1. Input Validation
    if not orig.strip() or not dest.strip():
        return json.dumps({
            "success": False,
            "status_code": 611,
            "error": "Missing an entry for one or both locations.",
            "data": None
        }, indent=4)

    # 2. Build URL and Request Data
    url = main_api + urllib.parse.urlencode({"key": key, "from": orig, "to": dest})
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        json_data = response.json()
    except requests.exceptions.RequestException as e:
        return json.dumps({
            "success": False,
            "status_code": 500,
            "error": f"Network or API error: {str(e)}",
            "data": None
        }, indent=4)

    # 3. Parse MapQuest Status Codes
    json_status = json_data.get("info", {}).get("statuscode", -1)

    # Case A: Success
    if json_status == 0:
        route_info = json_data.get("route", {})
        
        # Extract and format maneuvers (directions steps)
        maneuvers = []
        legs = route_info.get("legs", [])
        if legs:
            for step in legs[0].get("maneuvers", []):
                maneuvers.append({
                    "instruction": step.get("narrative", ""),
                    "distance_km": round(step.get("distance", 0) * 1.61, 2)
                })

        # Build successful response payload
        payload = {
            "success": True,
            "status_code": json_status,
            "error": None,
            "data": {
                "route": {
                    "from": orig,
                    "to": dest,
                    "duration": route_info.get("formattedTime", "00:00:00"),
                    "distance_km": round(route_info.get("distance", 0) * 1.61, 2),
                    "steps": maneuvers
                }
            }
        }
    
    # Case B: Standard MapQuest Client Errors
    elif json_status == 402:
        error_msg = "Invalid user inputs for one or both locations."
    elif json_status == 611:
        error_msg = "Missing an entry for one or both locations."
    else:
        error_msg = f"MapQuest API Error. Reference: https://developer.mapquest.com/documentation/directions-api/status-codes"

    # If it wasn't a success (status != 0), build the error payload/message
    if json_status != 0:
        payload = {
            "success": False,
            "status_code": json_status,
            "error": error_msg,
            "data": None
        }

    # 4. Return formatted JSON
    return json.dumps(payload, indent=4)


"""
# Simulate frontend sending "Manila" and "Quezon City"
frontend_output = get_route_json("Manila", "Quezon City")
print(frontend_output)
"""

