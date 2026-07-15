import urllib.request, json, time

BASE = "http://localhost:8000"

# Step 1: Check HCPs exist
r = urllib.request.urlopen(f"{BASE}/interactions/hcps")
hcps = json.loads(r.read())
print("HCPs in DB:", len(hcps))
for h in hcps:
    print(f"  - {h['name']} ({h['specialty']})")

# Step 2: Log a meeting
print("\n=== LOGGING MEETING ===")
data = json.dumps({
    "message": "I met Dr. John Smith today at City Medical Center. We discussed the new cardiac drug. Govind also attended. Dr. Smith agreed to start using the medication next month. I will send him the brochure tomorrow."
}).encode()
req = urllib.request.Request(f"{BASE}/interactions/chat", data=data, headers={"Content-Type": "application/json"}, method="POST")
r = urllib.request.urlopen(req, timeout=15)
resp = json.loads(r.read())
print("Response:", json.dumps(resp, indent=2))

# Step 3: Query - Who attended?
print("\n=== QUERY: Who attended? ===")
data = json.dumps({"message": "Who attended the meeting with Dr. John Smith?"}).encode()
req = urllib.request.Request(f"{BASE}/interactions/chat", data=data, headers={"Content-Type": "application/json"}, method="POST")
r = urllib.request.urlopen(req, timeout=15)
resp = json.loads(r.read())
print("Response:", json.dumps(resp, indent=2))

# Step 4: Query - What topics?
print("\n=== QUERY: What was discussed? ===")
data = json.dumps({"message": "What topics were discussed with Dr. John Smith?"}).encode()
req = urllib.request.Request(f"{BASE}/interactions/chat", data=data, headers={"Content-Type": "application/json"}, method="POST")
r = urllib.request.urlopen(req, timeout=15)
resp = json.loads(r.read())
print("Response:", json.dumps(resp, indent=2))

# Step 5: Query - Follow-up
print("\n=== QUERY: Follow-up actions? ===")
data = json.dumps({"message": "What are the follow-up actions for Dr. John Smith?"}).encode()
req = urllib.request.Request(f"{BASE}/interactions/chat", data=data, headers={"Content-Type": "application/json"}, method="POST")
r = urllib.request.urlopen(req, timeout=15)
resp = json.loads(r.read())
print("Response:", json.dumps(resp, indent=2))