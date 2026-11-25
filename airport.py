#!/usr/bin/env python3
"""
airport.py — Swedavia FlightInfo API v2 Terminal Client

Interaktivt terminalprogram som hämtar och presenterar flyginformation
i realtid från Swedavias tio flygplatser i Sverige via Swedavia FlightInfo API v2.

Innehåller:
- Val 1: Live-ankomster (Arrivals) med filter för kommande eller hela dagen
- Val 2: Live-avgångar (Departures) med filter för kommande eller hela dagen
- Val 3: Sök flygning på flygnummer, flygbolag eller destination
- Val 4: OData / Egen frågemöjlighet mot Swedavia /query
- Val 5: API-hälsokontroll och svarstid
- Val 6: Automatisk systemdemonstration (Auto Demo)
"""

import sys
import os
import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Any
import requests
import re

try:
    import destinationer
except ImportError:
    destinationer = None

#
# Konfiguration
#
API_KEY = "0652d4a747e9450c8ba858e5955faeb6"
BASE_URL = "https://api.swedavia.se/flightinfo/v2"

HEADERS = {
    "Ocp-Apim-Subscription-Key": API_KEY,
    "Accept": "application/json"
}

# De 10 Swedavia-drivna flygplatserna i Sverige
AIRPORTS = {
    "ARN": "Stockholm Arlanda Airport",
    "BMA": "Bromma Stockholm Airport",
    "GOT": "Göteborg Landvetter Airport",
    "MMX": "Malmö Airport",
    "LLA": "Luleå Airport",
    "UME": "Umeå Airport",
    "OSD": "Åre Östersund Airport",
    "VBY": "Visby Airport",
    "RNB": "Ronneby Airport",
    "KRN": "Kiruna Airport"
}

_AIRPORT_ALIASES = {
    "arlanda": "ARN",
    "stockholm": "ARN",
    "bromma": "BMA",
    "landvetter": "GOT",
    "göteborg": "GOT",
    "gothenburg": "GOT",
    "malmö": "MMX",
    "malmo": "MMX",
    "luleå": "LLA",
    "lulea": "LLA",
    "umeå": "UME",
    "umea": "UME",
    "östersund": "OSD",
    "ostersund": "OSD",
    "åre": "OSD",
    "visby": "VBY",
    "gotland": "VBY",
    "ronneby": "RNB",
    "kiruna": "KRN"
}

try:
    _SE_TZ = ZoneInfo("Europe/Stockholm")
except Exception:
    _SE_TZ = timezone(timedelta(hours=1))

PAGE_SIZE = 5

def _fmt_time(utc_str: str | None) -> str:
    """Konverterar UTC-tidsstämpel till lokal svensk tid (Europe/Stockholm)."""
    if not utc_str or utc_str == "N/A":
        return "-"
    try:
        dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        dt_se = dt_utc.astimezone(_SE_TZ)
        tz_name = dt_se.strftime("%Z") or "CET"
        return f"{dt_se.strftime('%H:%M')} {tz_name} ({dt_utc.strftime('%H:%M')} UTC)"
    except Exception:
        return str(utc_str)


def _get_scheduled_utc(flight: dict, is_departure: bool = True) -> str:
    """Returnerar den ursprungliga tidtabellstiden (scheduledUtc) för sortering."""
    times = flight.get("departureTime" if is_departure else "arrivalTime") or {}
    return times.get("scheduledUtc") or ""

def _get_estimated_local(flight: dict, is_departure: bool = True):
    """
    Hämtar beräknad ny tid som datetime i svensk lokal tid.
    Undersöker både estimatedUtc i tidsobjektet och 'Beräknad HH:MM' i statusfältet.
    """
    times = flight.get("departureTime" if is_departure else "arrivalTime") or {}
    est_utc = times.get("estimatedUtc")
    if est_utc:
        dt = _parse_local_time(est_utc)
        if dt:
            return dt

    loc = flight.get("locationAndStatus") or {}
    sw = loc.get("flightLegStatusSwedish") or ""
    m = re.search(r"Beräknad\s+(\d{1,2}):(\d{2})", sw, re.IGNORECASE)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        sched_dt = _parse_local_time(times.get("scheduledUtc"))
        if sched_dt:
            est_dt = sched_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if (est_dt - sched_dt).total_seconds() < -12 * 3600:
                est_dt += timedelta(days=1)
            elif (est_dt - sched_dt).total_seconds() > 12 * 3600:
                est_dt -= timedelta(days=1)
            return est_dt
    return None

def _get_effective_utc(flight: dict, is_departure: bool = True) -> str:
    """Returnerar den mest aktuella UTC-tiden (beräknad ny tid om sådan finns, annars tidtabell)."""
    times = flight.get("departureTime" if is_departure else "arrivalTime") or {}
    return times.get("estimatedUtc") or times.get("scheduledUtc") or ""


def _parse_local_time(utc_str: str | None):
    """Parse UTC timestamps and convert them to Swedish local time."""
    if not utc_str:
        return None
    try:
        return datetime.fromisoformat(utc_str.replace("Z", "+00:00")).astimezone(_SE_TZ)
    except (ValueError, TypeError):
        return None


def _format_status(flight: dict, is_departure: bool = True) -> str:
    """Formaterar flyg- och gatestatusar till tydliga svenska etiketter med förseningsinfo."""
    loc = flight.get("locationAndStatus") or {}
    times = flight.get("departureTime" if is_departure else "arrivalTime") or {}
    leg_status = loc.get("flightLegStatus") or ""
    gate_action = loc.get("gateAction") or ""

    scheduled_dt = _parse_local_time(times.get("scheduledUtc"))
    estimated_dt = _get_estimated_local(flight, is_departure=is_departure)
    actual_dt = _parse_local_time(times.get("actualUtc"))

    if leg_status == "CAN":
        return "Inställt"
    if leg_status == "DEL":
        return "Borttaget"

    rem_texts = [r.get("text", "").strip() for r in flight.get("remarksSwedish", []) if r.get("text")]
    has_sista = any("sista bagage" in t.lower() for t in rem_texts)
    has_forsta = any("första bagage" in t.lower() for t in rem_texts)
    is_approach = any("inkommande" in t.lower() for t in rem_texts)

    # Faktisk avgång har företräde
    if is_departure and (leg_status == "ACT" or actual_dt):
        return f"Lyfte kl. {actual_dt:%H:%M}" if actual_dt else "Har lyft"

    # För ankomster: visa landning och bagagestatus
    if not is_departure:
        if leg_status in ("ACT", "LAN") or actual_dt:
            land_time = f"Landade kl. {actual_dt:%H:%M}" if actual_dt else "Landat"
            if has_sista:
                return f"{land_time} · Sista bagage levererat"
            elif has_forsta:
                return f"{land_time} · Första bagage på bandet"
            return land_time

        parts = []
        if is_approach:
            parts.append("Inkommande")
        if estimated_dt and scheduled_dt:
            diff_min = int((estimated_dt - scheduled_dt).total_seconds() / 60)
            if diff_min >= 5:
                parts.append(f"Försenad till {estimated_dt:%H:%M} (+{diff_min} min)")
            elif diff_min <= -5:
                parts.append(f"Tidig · Beräknad {estimated_dt:%H:%M}")
            else:
                parts.append(f"I tid · Ankommer {estimated_dt:%H:%M}")
        else:
            ank_rem = [t for t in rem_texts if "ankommer" in t.lower() or "beräknad" in t.lower()]
            if ank_rem:
                parts.append(ank_rem[0])
            else:
                parts.append("I tid")
        return " · ".join(parts)

    # För avgångar
    parts = []
    if estimated_dt and scheduled_dt:
        diff_min = int((estimated_dt - scheduled_dt).total_seconds() / 60)
        if diff_min >= 5:
            parts.append(f"Försenad till {estimated_dt:%H:%M} (+{diff_min} min)")
        elif diff_min <= -5:
            parts.append(f"Ny tid {estimated_dt:%H:%M}")

    gate_labels = {
        "B": "Bordas",
        "F": "Sista utrop",
        "I": "Gå till gate",
        "C": "Gate stängd",
        "O": "Gate öppen",
    }
    if gate_action in gate_labels:
        parts.append(gate_labels[gate_action])

    if not parts:
        raw_status = loc.get("flightLegStatusSwedish") or ""
        if raw_status and "Beräknad" in raw_status:
            parts.append(raw_status)
        elif raw_status in ("Planerad", ""):
            parts.append("I tid")
        else:
            parts.append(raw_status)

    return " · ".join(parts)

def _get(url: str, params: dict | None = None) -> dict | None:
    """Utför GET-anrop mot Swedavias API med felhantering och rate limit-skydd."""
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        print(f" [HTTP {resp.status_code}]", end="", flush=True)

        if resp.status_code == 200:
            print()
            return resp.json()
        elif resp.status_code == 429:
            print("\n [Rate limit] Väntar 2 sekunder...")
            time.sleep(2)
            retry_resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
            print(f" [HTTP {retry_resp.status_code}]", end="", flush=True)
            if retry_resp.status_code == 200:
                print()
                return retry_resp.json()
            return None
        elif resp.status_code == 404:
            print("\n [Info] Inga flygningar hittades för angiven flygplats/datum.")
            return None
        else:
            print(f"\n [API-fel] Status {resp.status_code}: {resp.text[:150]}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"\n [Nätverksfel] {e}")
        return None

def _is_valid_flight(flight: dict) -> bool:
    """Kontrollerar att flygposten har giltigt flightId och tidsangivelse."""
    has_id = bool(flight.get("flightId"))
    times = flight.get("arrivalTime") or flight.get("departureTime") or {}
    has_time = bool(times.get("scheduledUtc"))
    return has_id and has_time

def _print_flight(flight: dict, index: int, home_airport: str | None = None, is_departure: bool = False) -> None:
    """Skriver ut ett enskilt flyg i strukturerat kortformat med svensk lokal tid och förseningsinfo."""
    fid = flight.get("flightId", "N/A")
    op = flight.get("airlineOperator", {})
    airline_name = op.get("name", "Okänt flygbolag")
    airline_iata = op.get("iata", "??")

    times = flight.get("departureTime" if is_departure else "arrivalTime") or {}
    loc = flight.get("locationAndStatus") or {}
    bag = flight.get("baggage") or {}

    status_se = _format_status(flight, is_departure=is_departure)
    terminal = loc.get("terminal") or "-"
    gate = loc.get("gate") or "-"
    belt = bag.get("baggageClaimUnit") or bag.get("belt") or bag.get("claim") or "-"

    sched_dt = _parse_local_time(times.get("scheduledUtc"))
    est_dt = _get_estimated_local(flight, is_departure=is_departure)
    actual_dt = _parse_local_time(times.get("actualUtc"))

    sched_str = f"{sched_dt:%H:%M} CET" if sched_dt else "-"
    actual_str = f"{actual_dt:%H:%M} CET" if actual_dt else "-"

    est_str = "-"
    diff_label = ""
    diff_min = 0
    if est_dt and sched_dt:
        diff_min = int((est_dt - sched_dt).total_seconds() / 60)
        if diff_min >= 5:
            diff_label = f" (+{diff_min} min)"
        elif diff_min <= -5:
            diff_label = f" ({diff_min} min)"
        est_str = f"{est_dt:%H:%M} CET"

    if is_departure:
        raw_dest = flight.get("arrivalAirportSwedish") or flight.get("arrivalAirportEnglish") or "Okänd"
        city = destinationer.clean_city_name(raw_dest) if destinationer else raw_dest
        country = destinationer.lookup_country(city) if destinationer else "Okänt land"
        from_str = f"{home_airport} ({AIRPORTS.get(home_airport, 'Lokal')})" if home_airport else "Lokal flygplats"
        to_str = f"{city}, {country}"
    else:
        raw_orig = flight.get("departureAirportSwedish") or flight.get("departureAirportEnglish") or "Okänd"
        city = destinationer.clean_city_name(raw_orig) if destinationer else raw_orig
        country = destinationer.lookup_country(city) if destinationer else "Okänt land"
        from_str = f"{city}, {country}"
        to_str = f"{home_airport} ({AIRPORTS.get(home_airport, 'Lokal')})" if home_airport else "Lokal flygplats"

    print(f"\n[{index}] » {fid} | {airline_name} ({airline_iata})")
    print(f"  Från       : {from_str}")
    print(f"  Till       : {to_str}")
    print(f"  Tidtabell  : {sched_str}")
    if est_dt and diff_min != 0:
        print(f"  Ny tid     : {est_str}{diff_label}")
    if actual_str != "-":
        act_label = "Lyfte" if is_departure else "Landade"
        print(f"  {act_label:<10} : {actual_str}")
    print(f"  Status     : {status_se}")
    if is_departure:
        print(f"  Terminal   : {terminal:<4}  Gate: {gate}")
    else:
        belt_str = f"Band {belt}" if belt != "-" else "Ej tilldelat"
        print(f"  Terminal   : {terminal:<4}  Bagageband: {belt_str}")

def _print_flights_paged(flights: list[dict], home_airport: str | None = None, is_departure: bool = False) -> None:
    """Skriver ut flyg paginerat (PAGE_SIZE åt gången) med interaktiv meny."""
    total = len(flights)
    if total == 0:
        print(" Inga flygningar att visa.")
        return

    start = 0
    while start < total:
        end = min(start + PAGE_SIZE, total)
        for i in range(start, end):
            _print_flight(flights[i], i + 1, home_airport=home_airport, is_departure=is_departure)

        if end >= total:
            print(f"\nVisade alla {total} flygningar.")
            break

        remaining = total - end
        cmd = input(f"\n--- Visar {end}/{total} ({remaining} kvar). [Enter]=nästa sida, [a]=visa alla, [q]=tillbaka: ").strip().lower()
        if cmd == "q":
            break
        elif cmd == "a":
            for i in range(end, total):
                _print_flight(flights[i], i + 1, home_airport=home_airport, is_departure=is_departure)
            print(f"\nVisade alla {total} flygningar.")
            break
        else:
            start += PAGE_SIZE

def _choose_airport() -> str:
    """Hanterar val av flygplats med validering och stöd för alias."""
    while True:
        raw = input(" Ange flygplats (t.ex. ARN, GOT, Arlanda) [ARN]: ").strip()
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
            print(" ⚠️  Felaktigt datumformat. Använd YYYY-MM-DD (t.ex. 2026-11-24).")

#
# Menyval 1-6
#

def option_arrivals():
    print("\n--- 1. VISA ANKOMSTER (ARRIVALS) ---")
    airport = _choose_airport()
    date_str = _choose_date()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    only_upcoming = False
    if date_str == today_str:
        ans = input(" Visa: [1] Kommande ankomster (från nu) [standard], [2] Hela dagen: ").strip()
        if ans != "2":
            only_upcoming = True

    print(f" Hämtar live-ankomster för {AIRPORTS[airport]} ({airport}) den {date_str}...")
    
    url = f"{BASE_URL}/{airport}/arrivals/{date_str}"
    data = _get(url)
    if not data:
        return

    raw_flights = data.get("flights", [])
    now_utc = datetime.now(timezone.utc)
    now_se = now_utc.astimezone(_SE_TZ)
    filtered = []

    for f in raw_flights:
        if not _is_valid_flight(f):
            continue
        status = f.get("locationAndStatus", {}).get("flightLegStatus")
        if status == "DEL":
            continue

        if only_upcoming:
            times = f.get("arrivalTime", {})
            actual_dt = _parse_local_time(times.get("actualUtc"))
            rem_texts = [r.get("text", "").strip().lower() for r in f.get("remarksSwedish", []) if r.get("text")]
            has_sista = any("sista bagage" in t for t in rem_texts)

            # Swedavias webbtavla visar BARA plan som är i luften / på väg in.
            # Så fort ett plan har landat tas det bort från webbens ankomsttavla.
            if status in ("ACT", "LAN") or actual_dt:
                continue

            # Plan som inte landat än: kolla beräknad eller tidtabellstid
            est_dt = _get_estimated_local(f, is_departure=False)
            sched_dt = _parse_local_time(times.get("scheduledUtc"))
            eff_dt = est_dt or sched_dt
            # Ignorera gamla flyg som borde ha kommit för mer än 30 min sen utan uppdatering
            if eff_dt and (eff_dt - now_se).total_seconds() < -1800:
                continue

        filtered.append(f)

    # Sortera kronologiskt efter ursprunglig tidtabellstid (originaltid)
    filtered.sort(key=lambda f: (_get_scheduled_utc(f, is_departure=False), f.get("flightId", "")))
    label = "kommande/aktuella" if only_upcoming else "aktiva"
    print(f" Hittade {len(filtered)} {label} ankomster.")
    _print_flights_paged(filtered, home_airport=airport, is_departure=False)

def option_departures():
    print("\n--- 2. VISA AVGÅNGAR (DEPARTURES) ---")
    airport = _choose_airport()
    date_str = _choose_date()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    only_upcoming = False
    if date_str == today_str:
        ans = input(" Visa: [1] Aktuell avgångstavla (från nu) [standard], [2] Hela dagen: ").strip()
        if ans != "2":
            only_upcoming = True

    print(f" Hämtar live-avgångar för {AIRPORTS[airport]} ({airport}) den {date_str}...")

    url = f"{BASE_URL}/{airport}/departures/{date_str}"
    data = _get(url)
    if not data:
        return

    raw_flights = data.get("flights", [])
    now_utc = datetime.now(timezone.utc)
    now_se = now_utc.astimezone(_SE_TZ)
    filtered = []

    for f in raw_flights:
        if not _is_valid_flight(f):
            continue
        loc = f.get("locationAndStatus", {})
        status = loc.get("flightLegStatus")
        if status == "DEL":
            continue

        if only_upcoming:
            # Ta bort flygningar som lyfte för mer än 5 minuter sedan (Swedavia tar bort dem från sin tavla)
            times = f.get("departureTime", {})
            actual_dt = _parse_local_time(times.get("actualUtc"))
            if status == "ACT" and actual_dt:
                if (now_se - actual_dt).total_seconds() > 300:  # > 5 min sedan start
                    continue
            else:
                # Plan som ännu inte lyft: kolla beräknad ny tid eller tidtabellstid
                est_dt = _get_estimated_local(f, is_departure=True)
                sched_dt = _parse_local_time(times.get("scheduledUtc"))
                eff_dt = est_dt or sched_dt
                gate_action = loc.get("gateAction")
                if eff_dt and (eff_dt - now_se).total_seconds() < -900 and gate_action not in ("B", "I", "O", "C"):
                    continue

        filtered.append(f)

    # Sortera kronologiskt efter ursprunglig tidtabellstid (originaltid)
    filtered.sort(key=lambda f: (_get_scheduled_utc(f, is_departure=True), f.get("flightId", "")))
    label = "aktuella på tavlan" if only_upcoming else "aktiva"
    print(f" Hittade {len(filtered)} {label} avgångar.")
    _print_flights_paged(filtered, home_airport=airport, is_departure=True)

def option_search_flight():
    print("\n--- 3. SÖK SPECIFIK FLYGNING ---")
    flight_id = input(" Ange flight ID eller sökord (t.ex. SK1415, LH805, SAS): ").strip().upper()
    if not flight_id:
        print(" Inget flight ID angavs.")
        return
    airport = _choose_airport()
    date_str = _choose_date()

    print(f" Söker efter '{flight_id}' på {airport} den {date_str}...")
    matched = []

    # Sök bland avgångar
    dep_data = _get(f"{BASE_URL}/{airport}/departures/{date_str}")
    if dep_data:
        for f in dep_data.get("flights", []):
            fid = f.get("flightId", "").upper()
            op_iata = f.get("airlineOperator", {}).get("iata", "").upper()
            op_name = f.get("airlineOperator", {}).get("name", "").upper()
            dest = (f.get("arrivalAirportSwedish") or f.get("arrivalAirportEnglish") or "").upper()
            if flight_id in fid or flight_id == op_iata or flight_id in op_name or flight_id in dest:
                matched.append((f, True))

    # Sök bland ankomster
    arr_data = _get(f"{BASE_URL}/{airport}/arrivals/{date_str}")
    if arr_data:
        for f in arr_data.get("flights", []):
            fid = f.get("flightId", "").upper()
            op_iata = f.get("airlineOperator", {}).get("iata", "").upper()
            op_name = f.get("airlineOperator", {}).get("name", "").upper()
            orig = (f.get("departureAirportSwedish") or f.get("departureAirportEnglish") or "").upper()
            if flight_id in fid or flight_id == op_iata or flight_id in op_name or flight_id in orig:
                matched.append((f, False))

    if not matched:
        print(f" Hittade ingen flygning med sökterm '{flight_id}'.")
    else:
        print(f" Hittade {len(matched)} matchning(ar):")
        for i, (f, is_dep) in enumerate(matched, 1):
            _print_flight(f, i, home_airport=airport, is_departure=is_dep)

def option_odata_query():
    print("\n--- 4. KÖR ODATA / EGEN FRÅGA (/query) ---")
    print(" Swedavias /query-endpoint stödjer flexibla filter:")
    airport = _choose_airport()
    query_str = input(" Ange OData-filter eller tryck Enter för standard: ").strip()
    
    url = f"{BASE_URL}/query"
    params = {"airport": airport}
    if query_str:
        params["$filter"] = query_str
    else:
        params["take"] = "5"

    print(f" Skickar fråga till {url} med {params}...")
    data = _get(url, params)
    if not data:
        return

    flights = data.get("flights", [])
    print(f" /query returnerade {len(flights)} poster.")
    if flights:
        sample = flights[0]
        print(" Exempelpost:")
        import json
        print(json.dumps(sample, indent=2, ensure_ascii=False)[:350] + "...")

def option_health_check():
    print("\n--- 5. KONTROLLERA API-HÄLSA ---")
    print(f" Testar anslutning mot Swedavia Flightinfo API v2 ({BASE_URL})...")
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/ARN/departures/{today}"
    start_t = time.time()
    data = _get(url)
    elapsed = time.time() - start_t

    if data is not None:
        flights_count = len(data.get("flights", []))
        print(f" ✅ API är online! Svarstid: {elapsed:.2f} sekunder.")
        print(f" 🔑 API-nyckel är godkänd ({flights_count} live-flyg hämtade).")
    else:
        print(" ❌ Kunde inte nå API:et eller ogiltig API-nyckel.")

def option_auto_demo():
    print("\n--- 6. KÖR FULL AUTO-DEMO ---")
    print(" Kör automatisk demonstration av systemets funktioner med live-data...")
    time.sleep(1)
    
    print("\n[Steg 1] Testar API-anslutning...")
    option_health_check()
    time.sleep(1)

    print("\n[Steg 2] Hämtar aktuella live-avgångar från Stockholm Arlanda (ARN)...")
    today = datetime.now().strftime("%Y-%m-%d")
    data = _get(f"{BASE_URL}/ARN/departures/{today}")
    if data:
        raw_flights = data.get("flights", [])
        now_utc = datetime.now(timezone.utc)
        active = []
        for f in raw_flights:
            if not _is_valid_flight(f):
                continue
            status = f.get("locationAndStatus", {}).get("flightLegStatus")
            if status == "DEL":
                continue
            eff = _get_effective_utc(f, is_departure=True)
            if eff:
                try:
                    dt_eff = datetime.fromisoformat(eff.replace("Z", "+00:00"))
                    if (dt_eff - now_utc).total_seconds() < -300:
                        continue
                except Exception:
                    pass
            active.append(f)
            
        active.sort(key=lambda f: (_get_scheduled_utc(f, is_departure=True), f.get("flightId", "")))
        print(f" Totalt {len(active)} aktuella avgångar på tavlan.")
        for i, f in enumerate(active[:3], 1):
            _print_flight(f, i, home_airport="ARN", is_departure=True)
            
    time.sleep(1)
    print("\n[Steg 3] Testar destinationsuppslag med destinationer.py...")
    if destinationer:
        sample_cities = ["London", "Paris CDG", "New York EWR", "Umeå", "Tokyo"]
        for c in sample_cities:
            print(f"  {c:<18} -> {destinationer.lookup_country(c)}")
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
