"""
destinationer.py — Visa unika avgångsorter / destinationer

Hämtar alla ankomster eller avgångar för en vald flygplats och dag,
och skriver ut en sorterad lista med alla unika platser.

Visar vilket land varje stad tillhör (från Swedavias statistikfil / city_country.json).
Kan filtrera på land.

Kör: python destinationer.py
"""

import json
import os
import sys
import requests
from datetime import datetime

API_KEY = "0652d4a747e9450c8ba858e5955faeb6"
BASE_URL = "https://api.swedavia.se/flightinfo/v2"
HEADERS = {
    "Ocp-Apim-Subscription-Key": API_KEY,
    "Accept": "application/json"
}

DATA_FILE = os.path.join(os.path.dirname(__file__), "city_country.json")
_CITY_TO_COUNTRY = {}
_COUNTRY_TO_CITIES = {}

def load_destinations():
    global _CITY_TO_COUNTRY, _COUNTRY_TO_CITIES
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _CITY_TO_COUNTRY = data.get("city_to_country", {})
                _COUNTRY_TO_CITIES = data.get("country_to_cities", {})
        except Exception as e:
            print(f"[Varning] Kunde inte läsa {DATA_FILE}: {e}")

load_destinations()

def lookup_country(city_name: str) -> str:
    """Slår upp land baserat på stad (skiftlägesokänsligt)."""
    if not city_name:
        return "Okänt land"
    clean = city_name.strip().lower()
    return _CITY_TO_COUNTRY.get(clean, "Okänt land")

def lookup_cities(country_name: str) -> list[str]:
    """Returnerar kända städer för ett givet land."""
    clean = country_name.strip().title()
    return _COUNTRY_TO_CITIES.get(clean, [])

def fetch_unique_destinations(airport: str = "ARN", direction: str = "D", date_str: str | None = None) -> list[tuple[str, str, int]]:
    """
    Hämtar flyg från Swedavia och returnerar en sorterad lista av
    (stad, land, antal_flyg).
    direction: 'D' för avgångar (destinations), 'A' för ankomster (ursprung).
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    url = f"{BASE_URL}/query"
    params = {"airport": airport, "date": date_str}
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"Fel vid anrop till Swedavia API: HTTP {resp.status_code}")
            return []
        data = resp.json()
    except Exception as e:
        print(f"Nätverksfel vid hämtning: {e}")
        return []

    flights = data.get("flights", [])
    counts: dict[str, int] = {}

    target_key = "departure" if direction.upper() == "D" else "arrival"
    airport_field = "arrivalAirportEnglish" if direction.upper() == "D" else "departureAirportEnglish"

    for item in flights:
        f_info = item.get(target_key)
        if not f_info:
            continue
        city = f_info.get(airport_field)
        if city:
            counts[city] = counts.get(city, 0) + 1

    results = []
    for city, count in counts.items():
        country = lookup_country(city)
        results.append((city, country, count))

    # Sortera i alfabetisk ordning efter stad
    results.sort(key=lambda x: x[0].lower())
    return results

def main():
    print("=" * 60)
    print("✈️  Swedavia Destination Explorer (destinationer.py)")
    print("=" * 60)

    airport = input("Ange flygplatskod [ARN]: ").strip().upper() or "ARN"
    dir_choice = input("Riktning ([D] avgångar / [A] ankomster) [D]: ").strip().upper() or "D"
    today = datetime.now().strftime("%Y-%m-%d")
    date_val = input(f"Ange datum (YYYY-MM-DD) [{today}]: ").strip() or today

    print(f"\nHämtar data för {airport} ({'Avgångar' if dir_choice == 'D' else 'Ankomster'}) den {date_val}...")
    destinations = fetch_unique_destinations(airport, dir_choice, date_val)

    if not destinations:
        print("Inga destinationer hittades eller API-begränsning uppstod.")
        return

    filter_country = input("\nVill du filtrera på ett specifikt land? (Tryck Enter för att visa alla): ").strip()
    if filter_country:
        destinations = [d for d in destinations if filter_country.lower() in d[1].lower()]

    print(f"\nHittade {len(destinations)} unika destinationer:\n")
    print(f"{'Stad/Flygplats':<30} {'Land':<22} {'Antal flyg':<10}")
    print("-" * 62)
    for city, country, count in destinations:
        print(f"{city:<30} {country:<22} {count:<10}")

if __name__ == "__main__":
    main()
