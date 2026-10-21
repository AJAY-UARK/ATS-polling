import json
import requests

# We will test using Palantir, one of the target companies from your configuration
COMPANY = "palantir"
# Note Lever's query parameter '?mode=json' is required, otherwise it returns HTML
ENDPOINT = f"https://api.lever.co/v0/postings/{COMPANY}?mode=json"

def inspect_lever_api():
    print(f"Fetching data from: {ENDPOINT}")
    
    # Execute the network call
    response = requests.get(ENDPOINT, timeout=10)
    
    if response.status_code != 200:
        print(f"Failed! Status Code: {response.status_code}")
        return
        
    # Lever returns a direct array, not a dictionary with a 'jobs' key
    raw_payload = response.json()
    
    output_file = "sample_lever_response.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(raw_payload, f, indent=4)
        
    print(f"Success! Open '{output_file}' in VS Code.")
    
    if isinstance(raw_payload, list) and len(raw_payload) > 0:
        print(f"Total jobs returned: {len(raw_payload)}")
        first_job = raw_payload[0]
        print(f"Keys inside a single Lever 'job' node: {list(first_job.keys())}")

if __name__ == "__main__":
    inspect_lever_api()
    