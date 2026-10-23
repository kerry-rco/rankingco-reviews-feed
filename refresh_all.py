#!/usr/bin/env python3
"""Refresh reviews/<slug>.json for every client in clients.json. A failed client keeps its previous file."""
import json, subprocess, sys, os
fails = 0
if not os.environ.get('GBP_REFRESH_TOKEN') and not os.environ.get('PLACES_API_KEY'):
    print('No GBP/Places secrets set; skipping refresh and keeping existing feeds.'); sys.exit(0)
for c in json.load(open('clients.json')):
    cmd = [sys.executable, 'feed/fetch_reviews.py', '--name', c['name'], '--place-id', c['placeId'], '--out', f"reviews/{c['slug']}.json.tmp"]
    if c.get('gbpParent'): cmd += ['--parent', c['gbpParent']]
    r = subprocess.run(cmd)
    if r.returncode == 0: os.replace(f"reviews/{c['slug']}.json.tmp", f"reviews/{c['slug']}.json")
    else: fails += 1; print('FAILED', c['slug'], file=sys.stderr)
sys.exit(1 if fails else 0)
