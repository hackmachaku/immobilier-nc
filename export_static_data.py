import json
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

endpoints = [
    ("http://localhost:8080/api/listings", BASE_DIR / "data_listings.json"),
    ("http://localhost:8080/api/sources", BASE_DIR / "data_sources.json"),
    ("http://localhost:8080/api/agencies", BASE_DIR / "data_agencies.json"),
]

print("Exporting static snapshots from local server...")
for url, filepath in endpoints:
    try:
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
            with open(filepath, "wb") as f:
                f.write(data)
            print(f"  Exported {filepath.name} ({len(data)} bytes)")
    except Exception as e:
        print(f"  Error exporting {url}: {e}")

print("Static data snapshot ready for GitHub Pages / Vercel / Netlify!")
