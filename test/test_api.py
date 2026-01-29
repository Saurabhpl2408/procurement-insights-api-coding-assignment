import requests
import json

API_URL = "http://localhost:8000/generate-insights"

with open("examples/example_request.json", "r") as f:
    payload = json.load(f)

print("Sending request to API...")
print(json.dumps(payload, indent=2))
print("\n" + "="*80 + "\n")

try:
    response = requests.post(API_URL, json=payload)
    
    print(f"Status Code: {response.status_code}")
    print("\nResponse:")
    print(json.dumps(response.json(), indent=2))
    
    if response.status_code == 200:
        with open("examples/example_response.json", "w") as f:
            json.dump(response.json(), f, indent=2)
        print("\n✓ Response saved to examples/example_response.json")
    
except requests.exceptions.ConnectionError:
    print("Error: Could not connect to API. Make sure the server is running on http://localhost:8000")
except Exception as e:
    print(f"Error: {str(e)}")