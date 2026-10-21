import json
import requests

# We will test using Cloudflare, one of the target companies from your configuration[cite: 1]
COMPANY = "cloudflare"
ENDPOINT = f"https://boards-api.greenhouse.io/v1/boards/{COMPANY}/jobs?content=true"

def inspect_api():
    print(f"Fetching data from: {ENDPOINT}")
    
    # 1. Execute the network call
    response = requests.get(ENDPOINT, timeout=10)
    
    # 2. Halt if the API rejects us
    if response.status_code != 200:
        print(f"Failed! Status Code: {response.status_code}")
        return
        
    # 3. Parse the raw JSON
    raw_payload = response.json()
    
    # 4. Save to a local file for easy reading in VS Code
    output_file = "sample_api_response.json"
    with open(output_file, "w", encoding="utf-8") as f:
        # indent=4 formats the JSON beautifully instead of a single massive string
        json.dump(raw_payload, f, indent=4)
        
    print(f"Success! Open '{output_file}' in VS Code to inspect the exact structure.")
    
    # Optional: Print just the top-level keys to the terminal
    print(f"\nTop-level JSON keys found: {list(raw_payload.keys())}")
    
    if "jobs" in raw_payload:
        print(f"Total jobs returned: {len(raw_payload['jobs'])}")
        # Print the keys of the very first job node
        if len(raw_payload['jobs']) > 0:
            first_job = raw_payload['jobs'][0]
            print(f"Keys inside a single 'job' node: {list(first_job.keys())}")

if __name__ == "__main__":
    inspect_api()
    