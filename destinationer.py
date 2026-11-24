"""
destinationer.py — Visa unika avgångsorter / destinationer

Hämtar alla ankomster eller avgångar för en vald flygplats och dag,
och sammanställer en sorterad lista med alla unika platser.

Visar vilket land varje stad tillhör (från city_country.json).
Kan filtrera på land.

Kör: python destinationer.py
"""

import json
import os
import sys
import re
import requests
from datetime import datetime

API_KEY = "0652d4a747e9450c8ba858e5955faeb6"
BASE_URL = "https://api.swedavia.se/flightinfo/v2"
HEADERS = {
    "Ocp-Apim-Subscription-Key": API_KEY,
    "Accept": "application/json"
}

DATA_FILE = os.path.join(os.path.dirname(__file__), "city_country.json")
_CITY_TO_COUNTRY: dict[str, str] = {}
_COUNTRY_TO_CITIES: dict[str, list[str]] = {}

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

def clean_city_name(raw_city: str | None) -> str:
    """Rensar flygplatskoder och extra specifikationer från stadsnamn.
    Exempel: 'Paris CDG' -> 'Paris', 'London LHR' -> 'London', 'Stockholm (ARN)' -> 'Stockholm'."""
    if not raw_city:
        return ""
    # Ta bort parenteser
    city = re.sub(r"\(.*?\)", "", raw_city).strip()
    
    # Kända IATA-koder som läggs till stadsnamn
    suffixes = [
        " CDG", " ORY", " LHR", " LGW", " STN", " LTN", " LCY", " SEN",
        " EWR", " JFK", " LGA", " IST", " SAW", " LIN", " MXP", " BGY",
        " BBU", " OTP", " HND", " NRT", " ARN", " BMA", " GOT", " MMX",
        " TGL", " BER", " SXF", " CIA", " FCO"
    ]
    for s in suffixes:
        if city.upper().endswith(s):
            city = city[:-len(s)].strip()
            break
            
    return city

def lookup_country(city_name: str) -> str:
    """Slår upp land baserat på stad (skiftlägesokänsligt och med normalisering)."""
    if not city_name:
        return "Okänt land"
    
    cleaned = clean_city_name(city_name).lower()
    if cleaned in _CITY_TO_COUNTRY:
        return _CITY_TO_COUNTRY[cleaned]
    
    # Testa även råsträngen
    raw_lower = city_name.strip().lower()
    if raw_lower in _CITY_TO_COUNTRY:
        return _CITY_TO_COUNTRY[raw_lower]
        
    return "Okänt land"

def lookup_cities(country_name: str) -> list[str]:
    """Returnerar kända städer för ett givet land."""
    clean = country_name.strip().title()
    return _COUNTRY_TO_CITIES.get(clean, [])

def fetch_unique_destinations(airport: str = "ARN", direction: str = "D", date_str: str | None = None) -> list[tuple[str, str, int]]:
    """
    Hämtar live-flyg från Swedavias departures- eller arrivals-endpoint och
    returnerar en sorterad lista av (stad, land, antal_flyg).
    direction: 'D' för avgångar, 'A' för ankomster.
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    endpoint = "departures" if direction.upper() == "D" else "arrivals"
    url = f"{BASE_URL}/{airport}/{endpoint}/{date_str}"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"Fel vid anrop till Swedavia API: HTTP {resp.status_code}")
            return []
        data = resp.json()
    except Exception as e:
        print(f"Nätverksfel vid hämtning: {e}")
        return []

    flights = data.get("flights", [])
    city_counts: dict[str, int] = {}

    for f in flights:
        if f.get("locationAndStatus", {}).get("flightLegStatus") == "DEL":
            continue
            
        if direction.upper() == "D":
            raw_city = f.get("arrivalAirportSwedish") or f.get("arrivalAirportEnglish")
        else:
            raw_city = f.get("departureAirportSwedish") or f.get("departureAirportEnglish")
            
        if not raw_city:
            continue
            
        city = clean_city_name(raw_city)
        city_counts[city] = city_counts.get(city, 0) + 1

    result = []
    for city, count in city_counts.items():
        country = lookup_country(city)
        result.append((city, country, count))

    # Sortera i fallande ordning efter antal flygningar, sedan alfabetiskt
    result.sort(key=lambda x: (-x[2], x[0]))
    return result

def main():
    print("=" * 60)
    print(" 🌍  SWEDAVIA DESTINATIONER & LÄNDER")
    print("=" * 60)
    
    airport = input(" Ange flygplats IATA [ARN]: ").strip().upper() or "ARN"
    direction = input(" Avgångar (D) eller Ankomster (A) [D]: ").strip().upper() or "D"
    
    label = "Destinationer (Avgångar)" if direction == "D" else "Ursprung (Ankomster)"
    print(f"\n Hämtar live {label} för {airport}...")
    
    dests = fetch_unique_destinations(airport=airport, direction=direction)
    
    if not dests:
        print(" Inga flygningar hittades.")
        return
        
    print(f"\n Hittade {len(dests)} unika städer:")
    print("-" * 60)
    print(f" {'Stad':<22} {'Land':<25} {'Flyg':>6}")
    print("-" * 60)
    
    unknown_count = 0
    for city, country, count in dests:
        if country == "Okänt land":
            unknown_count += 1
        print(f" {city:<22} {country:<25} {count:>6}")
        
    print("-" * 60)
    print(f" Totalt: {sum(x[2] for x in dests)} flygningar till/från {len(dests)} städer.")
    if unknown_count > 0:
        print(f" [Obs] {unknown_count} destination(er) saknar land i databasen.")
    else:
        print(" ✅ Alla destinationer matchades mot kända länder!")

if __name__ == "__main__":
    main()
