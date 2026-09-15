import urllib.parse
import requests
import os
from dotenv import load_dotenv

load_dotenv()

main_api = "https://www.mapquestapi.com/directions/v2/route?"
key = os.getenv('API_KEY')

def get_route(orig, dest):
    # Format the URL 
    url = main_api + urllib.parse.urlencode({
        "key": key,
        "from": orig,
        "to": dest
    })

    # Requests json data with the created URL
    json_data = requests.get(url).json()
    # Gets the status 
    json_status = json_data["info"]["statuscode"]

    #Conditional statements for outputs
    if json_status == 0:
        return{
            "status": 0,
            "data": json_data
        }
    elif json_status == 402:
        return{
            "status": 402,
            "message": "Invalid user inputs for one or both locations"
        }
    elif json_status == 611:
        return{
            "status": 611,
            "message": "Missing an entry for one or both locations"
        }

    else:
        return {
            "status": json_status,
            "message": "Unknown MapQuest API error"
        }










# while True:
#     orig = input("Starting Location: ")
#     if orig == "quit" or orig == "q":
#         break

#     dest = input("Destination: ")
#     if dest == "quit" or dest == "q":
#         break

#     url = main_api + urllib.parse.urlencode({"key": key, "from": orig, "to": dest})

#     print(f"URL: {url}")
#     json_data = requests.get(url).json()
#     json_status = json_data["info"]["statuscode"]

#     if json_status == 0:
#         print(f"API Status: {str(json_status)} = A successful route call. \n")
#         print("=" * 20)
#         print(f"Directions from {orig} to {dest}")
#         print(f"Trip Duration {(json_data['route']['formattedTime'])}")
#         print(f"Kilometers: {((json_data['route']['distance'])*1.61):.2f}")
#         print("=" * 20)
#         for number, each in enumerate(json_data["route"]["legs"][0]["maneuvers"], start=1):
#             print(f"{number}. {each["narrative"]} ({each["distance"] *1.61:.2f} km)")
#         print("=" * 20)
#     elif json_status == 402:
#         print("=" * 20)
#         print(f"Status Code: {str(json_status)} ; Invalid user inputs for one or both locations")
#         print("=" * 20)
#     elif json_status == 611:
#         print("=" * 20)
#         print(f"Status Code: {str(json_status)} ; Missing an entry for one or both locations")
#         print("=" * 20)
#     else:
#         print("=" * 20)
#         print(f"For Status Code: {str(json_status)} ; Refere to: ")
#         print("https://developer.mapquest.com/documentation/directions-api/status-codes")
#         print("=" * 20)
    
