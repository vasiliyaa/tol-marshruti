#!/usr/bin/env python3
"""Rebuild road_live.js: live BGTOLL counting-point data + incidents.json.

Runs in GitHub Actions every 15 minutes. incidents.json is pushed separately
from the owner's Mac (road conditions from АПИ need reading by hand/Claude).
"""
import datetime
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://bgtoll.bg/index.php/traffic_passes/data"
LIGHT = ("class0_moto", "class1_light", "class2_light_trl")
BUS = ("class8_bus_12t", "class9_bus_heavy")
HEAVY = ("class3_heavy_12t", "class4_heavy_2a", "class5_heavy_3a", "class6_heavy_4a", "class7_heavy_5a")


def traffic():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://bgtoll.bg/traffic_passes/"})
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = json.loads(r.read().decode("utf-8-sig"))
    points, times = [], []
    for x in rows:
        try:
            lon, lat = round(float(x["lon"]), 5), round(float(x["lat"]), 5)
        except (KeyError, TypeError, ValueError):
            continue
        cl = x.get("classes1Hour") or {}
        s = lambda keys: int(sum(cl.get(k, 0) or 0 for k in keys))
        points.append([int(x["scp"]), lon, lat, x.get("name", ""), int(x.get("count15min") or 0),
                       int(x.get("count1Hour") or 0), s(LIGHT), s(HEAVY), s(BUS)])
        if x.get("time"):
            times.append(x["time"])
    return {"time": max(times).replace(" ", "T") + "Z" if times else "",
            "source": "БГТОЛ, карта на преминавания (bgtoll.bg/traffic_passes)", "points": points}


def main():
    out = os.path.join(ROOT, "road_live.js")
    old = {}
    if os.path.exists(out):
        try:
            old = json.loads(open(out, encoding="utf-8").read().split("=", 1)[1].rstrip().rstrip(";"))
        except (ValueError, IndexError):
            old = {}
    try:
        tr = traffic()
    except Exception as e:  # keep the last good traffic snapshot
        print("BGTOLL fetch failed:", e)
        tr = old.get("traffic")
    try:
        inc = json.load(open(os.path.join(ROOT, "incidents.json"), encoding="utf-8"))
    except (OSError, ValueError):
        inc = old.get("incidents", [])
    payload = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "traffic": tr, "incidents": inc}
    with open(out, "w", encoding="utf-8") as f:
        f.write("window.ROAD_LIVE=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"{len((tr or {}).get('points', []))} traffic points, {len(inc)} incidents")


if __name__ == "__main__":
    main()
