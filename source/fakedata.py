import os, json, random, datetime

# BASE_DIR is ~/iaesDash/source when you run this from that folder
BASE_DIR = os.getcwd()
OUTPUT_DIR = os.path.join(BASE_DIR, 'jsondata', 'fakedata', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def make_records(n, minutes_back):
    now = datetime.datetime.utcnow()
    return [
        {
            "timestamp": (now - datetime.timedelta(minutes=random.randint(0, minutes_back))).isoformat(),
            "PROTOCOL": random.choice(["TCP","UDP","ICMP"]),
            "SRCIP": f"192.168.{random.randint(0,255)}.{random.randint(1,254)}",
            "DSTIP": f"10.0.{random.randint(0,255)}.{random.randint(1,254)}",
            "TOTPACKETS": random.randint(1,500),
            "TOTDATA": random.randint(100,50000)
        }
        for _ in range(n)
    ]

specs = [
    ("1_hour_data.json", 60),
    ("24_hours_data.json", 1440),
    ("all_data.json", 10080),
]

for fname, mins in specs:
    path = os.path.join(OUTPUT_DIR, fname)
    with open(path, "w") as f:
        json.dump(make_records(200, mins), f, indent=2)
    print(f"Wrote {path}")
