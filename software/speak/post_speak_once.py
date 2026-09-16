import json, urllib.request
from pathlib import Path
url = Path("/workspace/desk-atlas/speak_url.txt").read_text().strip()
secret = Path("/workspace/desk-atlas/speak.secret").read_text().strip()
body = json.dumps({"text": "You already have Endgame locked for Thursday the twenty-fourth at six twenty at University Mall. Seats G four and G five. Want another time?"}).encode()
req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "X-Atlas-Speak-Secret": secret}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("status", r.status)
        print(r.read()[:300].decode())
except Exception as e:
    print("error", type(e).__name__, e)
