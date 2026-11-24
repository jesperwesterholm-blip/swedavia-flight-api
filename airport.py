"""
airport.py — Swedavia Flightinfo API v2 Exploration Application

An interactive terminal application to monitor real-time flight data
across Sweden's 10 Swedavia airports.

Part of APL Project 2026: Reverse Engineer a Result
"""

import sys
import os
import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Any
import requests

try:
    import destinationer
except ImportError:
    # Ensure current directory is accessible
    sys.path.append(os.path.dirname(__file__))
    import destinationer

#
# Configuration
#
API_KEY = "0652d4a747e9450c8ba858e5955faeb6"
BASE_URL = "https://api.swedavia.se/flightinfo/v2"

HEADERS = {
    "Ocp-Apim-Subscription-Key": API_KEY,
    "Accept": "application/json"
}

# The 10 Swedavia-operated commercial airports in Sweden
AIRPORTS = {
    "ARN": "Stockholm Arlanda",
    "GOT": "Göteborg Landvetter",
    "BMA": "Stockholm Bromma",
    "MMX": "Malmö",
    "LLA": "Luleå",
    "UME": "Umeå",
    "OSD": "Åre Östersund",
    "VBY": "Visby",
    "RNB": "Ronneby",
    "KRN": "Kiruna"
}

_AIRPORT_ALIASES = {
    "arlanda": "ARN",
    "stockholm": "ARN",
    "landvetter": "GOT",
    "gothenburg": "GOT",
    "göteborg": "GOT",
    "bromma": "BMA",
    "malmö": "MMX",
    "malmo": "MMX",
    "luleå": "LLA",
    "lulea": "LLA",
    "umeå": "UME",
    "umea": "UME",
    "östersund": "OSD",
    "ostersund": "OSD",
    "are": "OSD",
    "åre": "OSD",
    "visby": "VBY",
    "gotland": "VBY",
    "ronneby": "RNB",
    "kiruna": "KRN"
}

_SE_TZ = ZoneInfo("Europe/Stockholm")
PAGE_SIZE = 5

def _fmt_time(utc_str: str | None) -> str:
    """Konverterar '2026-02-25T10:05:00Z' till '10:05 UTC -> 11:05 CET/CEST'."""
    if not utc_str or utc_str == "N/A":
        return "-"
    try:
        dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        dt_se = dt_utc.astimezone(_SE_TZ)
        tz_name = dt_se.strftime("%Z")  # 'CET' eller 'CEST'
        return f"{dt_utc.strftime('%H:%M')} UTC -> {dt_se.strftime('%H:%M')} {tz_name}"
    except Exception:
        return str(utc_str)

def _get(url: str, params: dict | None = None) -> dict | None:
    """Utför GET-anrop mot Swedavias API med felhantering och cache-inspektion."""
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        print(f" [HTTP {resp.status_code}]", end="", flush=True)

        for h in ("Last-Modified", "Last-Modified-InMinutes"):
            if h in resp.headers:
                print(f" ({h}: {resp.headers[h]})", end="")
        print()

        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            print(" [Info] Väntar 2 sekunder på grund av Swedavia rate limit...")
            time.sleep(2)
            resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            print(" [Fel] Rate limit kvarstår (HTTP 429).")
        elif resp.status_code == 404:
            print(" [Info] Inga resultat hittades (HTTP 404).")
        else:
            print(f" [Fel] HTTP-fel: {resp.status_code} - {resp.text[:120]}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"\n [Nätverksfel] {e}")
        return None

def _is_valid_flight(flight: dict) -> bool:
    """Returnerar False för spökposter där nyckelfält saknas."""
    has_id = bool(flight.get("flightId"))
    has_origin = bool(flight.get("departureAirportEnglish") or flight.get("arrivalAirportEnglish"))
    times = flight.get("arrivalTime") or flight.get("departureTime") or {}
    has_time = bool(times.get("scheduledUtc"))
    return has_id or has_origin or has_time

def _is_upcoming(flight: dict) -> bool:
    """Kontrollerar om flyget är kommande eller redan avklarat."""
    times = flight.get("arrivalTime") or flight.get("departureTime") or {}
    if not times:
        return False
    return not bool(times.get("actualUtc"))

def _print_flight(flight: dict, index: int, home_airport: str | None = None, is_departure: bool = False) -> None:
    """Skriver ut ett enskilt flyg i strukturerat kortformat i terminalen."""
    fid = flight.get("flightId", "N/A")
    op = flight.get("airlineOperator", {})
    airline_name = op.get("name", "Okänt flygbolag")
    airline_iata = op.get("iata", "??")

    times = flight.get("departureTime" if is_departure else "arrivalTime") or {}
    loc = flight.get("locationAndStatus") or {}
    bag = flight.get("baggage") or {}

    status_eng = loc.get("flightLegStatusEnglish") or loc.get("flightLegStatusSwedish") or "Scheduled"
    terminal = loc.get("terminal") or "N/A"
    gate = loc.get("gate") or "N/A"
    baggage = bag.get("belt") or bag.get("claim") or "-"

    sched = _fmt_time(times.get("scheduledUtc"))
    est = _fmt_time(times.get("estimatedUtc"))
    actual = _fmt_time(times.get("actualUtc"))

    if is_departure:
        dest_city = flight.get("arrivalAirportEnglish") or "N/A"
        country = destinationer.lookup_country(dest_city)
        from_str = f"({home_airport})" if home_airport else "Local"
        to_str = f"{dest_city}, {country}"
    else:
        origin_city = flight.get("departureAirportEnglish") or "N/A"
        country = destinationer.lookup_country(origin_city)
        from_str = f"{origin_city}, {country}"
        to_str = f"({home_airport})" if home_airport else "Local"

    print(f"\n[{index}] » {fid} | {airline_name} ({airline_iata})")
    print(f"  Från     : {from_str}")
    print(f"  Till     : {to_str}")
    print(f"  Status   : {status_eng}")
    print(f"  Terminal : {terminal:<4}  Gate: {gate}")
    if not is_departure:
        print(f"  Bagage   : {baggage}")
    print(f"  Tidtabell: {sched}")
    if est != "-":
        print(f"  Beräknad : {est}")
    if actual != "-":
        print(f"  Faktisk  : {actual}")

def _print_flights_paged(flights: list[dict], home_airport: str | None = None, is_departure: bool = False) -> None:
    """Skriver ut flyg paginerat (PAGE_SIZE åt gången) med interaktiv meny."""
    total = len(flights)
    if total == 0:
        print(" Inga flyg att visa.")
        return

    start = 0
    while start < total:
        end = min(start + PAGE_SIZE, total)
        for i in range(start, end):
            _print_flight(flights[i], i + 1, home_airport, is_departure)

        print(f"\n— Visar {end}/{total} — ({total - end} kvar)")
        if end >= total:
            break

        nav = input(" [Enter] nästa sida | [a] visa alla | [q] tillbaka till menyn: ").strip().lower()
        if nav == "q":
            print(f" Avbröt efter {end} flyg.")
            break
        elif nav == "a":
            # Skriv ut resterande utan paus
            for i in range(end, total):
                _print_flight(flights[i], i + 1, home_airport, is_departure)
            print(f"\nVisade alla {total} flyg.")
            break
        else:
            start += PAGE_SIZE

def _choose_airport() -> str:
    """Hanterar val av flygplats med validering och stöd för alias."""
    while True:
        raw = input(" Ange flygplats (t.ex. ARN, GOT, Arlanda): ").strip()
        if not raw:
            return "ARN"
        upper = raw.upper()
        if upper in AIRPORTS:
            return upper
        lower = raw.lower()
        if lower in _AIRPORT_ALIASES:
            return _AIRPORT_ALIASES[lower]
        print(f" ⚠️  Okänd flygplats '{raw}'. Giltiga IATA: {', '.join(AIRPORTS.keys())}")

def _choose_date() -> str:
    """Hanterar datumval med formatkontroll."""
    today = datetime.now().strftime("%Y-%m-%d")
    while True:
        raw = input(f" Ange datum YYYY-MM-DD [{today}]: ").strip()
        if not raw:
            return today
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            print(" ⚠️  Felaktigt datumformat. Använd formatet YYYY-MM-DD.")

#
# Menyval 1-6
#

def option_arrivals():
    print("\n--- 1. VISA ANKOMSTER ---")
    airport = _choose_airport()
    date_str = _choose_date()
    print(f" Hämtar ankomster för {AIRPORTS[airport]} ({airport}) den {date_str}...")
    
    url = f"{BASE_URL}/query"
    params = {"airport": airport, "date": date_str}
    data = _get(url, params)
    if not data:
        return

    raw_flights = data.get("flights", [])
    arrivals = [f["arrival"] for f in raw_flights if "arrival" in f and _is_valid_flight(f["arrival"])]
    print(f" Hittade {len(arrivals)} ankomster.")
    _print_flights_paged(arrivals, home_airport=airport, is_departure=False)

def option_departures():
    print("\n--- 2. VISA AVGÅNGAR ---")
    airport = _choose_airport()
    date_str = _choose_date()
    print(f" Hämtar avgångar för {AIRPORTS[airport]} ({airport}) den {date_str}...")

    url = f"{BASE_URL}/query"
    params = {"airport": airport, "date": date_str}
    data = _get(url, params)
    if not data:
        return

    raw_flights = data.get("flights", [])
    departures = [f["departure"] for f in raw_flights if "departure" in f and _is_valid_flight(f["departure"])]
    print(f" Hittade {len(departures)} avgångar.")
    _print_flights_paged(departures, home_airport=airport, is_departure=True)

def option_search_flight():
    print("\n--- 3. SÖK SPECIFIK FLYGNING ---")
    flight_id = input(" Ange flight ID (t.ex. SK100, FR4627): ").strip().upper()
    if not flight_id:
        print(" Inget flight ID angavs.")
        return
    airport = _choose_airport()
    date_str = _choose_date()

    print(f" Söker efter {flight_id} på {airport} den {date_str}...")
    url = f"{BASE_URL}/query"
    params = {"airport": airport, "date": date_str}
    data = _get(url, params)
    if not data:
        return

    matched = []
    for item in data.get("flights", []):
        for k in ("arrival", "departure"):
            f = item.get(k)
            if f and f.get("flightId", "").upper() == flight_id:
                matched.append((f, k == "departure"))

    if not matched:
        print(f" Hittade ingen flygning med ID '{flight_id}'.")
    else:
        print(f" Hittade {len(matched)} matchning(ar):")
        for i, (f, is_dep) in enumerate(matched, 1):
            _print_flight(f, i, home_airport=airport, is_departure=is_dep)

def option_odata_query():
    print("\n--- 4. KÖR ODATA / EGEN FRÅGA ---")
    print(" Exempel på OData-filter eller parametrar som Swedavia stöder via /query:")
    airport = _choose_airport()
    query_str = input(" Ange OData $filter (t.ex. flightId eq 'SK100' eller lämna tomt för standard): ").strip()
    
    url = f"{BASE_URL}/query"
    params = {"airport": airport}
    if query_str:
        params["$filter"] = query_str

    data = _get(url, params)
    if not data:
        return

    flights = data.get("flights", [])
    print(f" Svaret innehåller {len(flights)} poster.")
    if flights:
        sample = flights[0]
        print(" Exempelpost:")
        import json
        print(json.dumps(sample, indent=2, ensure_ascii=False)[:400] + "...")

def option_health_check():
    print("\n--- 5. KONTROLLERA API-HÄLSA ---")
    print(f" Testar anslutning mot Swedavia Flightinfo API v2 ({BASE_URL})...")
    url = f"{BASE_URL}/query"
    start_t = time.time()
    data = _get(url, params={"airport": "ARN", "take": "1"})
    elapsed = time.time() - start_t

    if data is not None:
        print(f" ✅ API är online! Svarstid: {elapsed:.2f} sekunder.")
        print(f" 🔑 API-nyckel är godkänd.")
    else:
        print(" ❌ Kunde inte nå API:et eller ogiltig API-nyckel.")

def option_auto_demo():
    print("\n--- 6. KÖR FULL AUTO-DEMO ---")
    print(" Kör automatisk demonstration av systemets funktioner...")
    time.sleep(1)
    
    print("\n[Steg 1] Testar API-anslutning...")
    option_health_check()
    time.sleep(1)

    print("\n[Steg 2] Hämtar senaste ankomster till Stockholm Arlanda (ARN)...")
    data = _get(f"{BASE_URL}/query", params={"airport": "ARN", "take": "3"})
    if data:
        raw = data.get("flights", [])
        arr = [f["arrival"] for f in raw if "arrival" in f][:2]
        for idx, f in enumerate(arr, 1):
            _print_flight(f, idx, "ARN", is_departure=False)

    print("\n[Steg 3] Testar destinationsuppslag med destinationer.py...")
    sample_cities = ["Barcelona", "Oslo", "London", "Phuket", "Krabi"]
    for c in sample_cities:
        print(f"  {c:<15} -> {destinationer.lookup_country(c)}")

    print("\n Demo slutförd!")

def main():
    while True:
        print("\n" + "=" * 55)
        print(" ✈️   SWEDAVIA FLIGHTINFO API v2 — TERMINAL APP")
        print("=" * 55)
        print(" [1] Visa ankomster (Arrivals)")
        print(" [2] Visa avgångar (Departures)")
        print(" [3] Sök specifik flygning (Search Flight)")
        print(" [4] Kör OData-fråga (OData Query)")
        print(" [5] Kontrollera API-hälsa (Health Check)")
        print(" [6] Kör full auto-demo (Auto Demo)")
        print(" [q] Avsluta programmet")
        print("-" * 55)

        choice = input(" Välj [1-6] eller q: ").strip().lower()

        if choice == "1":
            option_arrivals()
        elif choice == "2":
            option_departures()
        elif choice == "3":
            option_search_flight()
        elif choice == "4":
            option_odata_query()
        elif choice == "5":
            option_health_check()
        elif choice == "6":
            option_auto_demo()
        elif choice == "q":
            print("\nAvslutar programmet. Hej då!\n")
            break
        else:
            print(" ⚠️  Ogiltigt val, försök igen.")

if __name__ == "__main__":
    main()
