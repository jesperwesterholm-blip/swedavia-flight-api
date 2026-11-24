# Flight API Exploration – Project Documentation

> **Course:** APL Project 2026  
> **Task:** 4. Reverse Engineer a Result  
> **Language:** English (Required)  
> **Repository:** GitHub  

---

## Executive Summary
This project reverse engineers and implements a complete Python terminal application that interacts with the **Swedavia Flightinfo API v2**. The application monitors real-time arrivals, departures, detailed flight statuses, and custom queries across all 10 Swedavia-operated commercial airports in Sweden.

---

## Phase 1: Research Phase (Preliminary Study)

### 1.1 Objective & Reverse Engineering Analysis
The objective was to analyze an existing demonstration application, dissect its behavior, understand the underlying data structures, and deduce how the application was built.

#### Step 1: Observing the Target Output
- The target system displays live airport flight schedules.
- Key data entities identified from responses:
  - Flight identification (`flightId`, flight numbers)
  - Airport details (IATA codes e.g. `ARN`, `GOT`, English & Swedish names)
  - Time attributes: Scheduled UTC time, estimated time, and actual departure/arrival time
  - Flight status codes (e.g., On Time, Delayed, Landed, Departed, Boarding)
  - Destination / origin city names.

#### Step 2: Deducing the Underlying API
- Identified the source as **Swedavia Flightinfo API v2**:
  - Base URL: `https://api.swedavia.se/flightinfo/v2`
  - Authentication: Subscription key passed via header (`Ocp-Apim-Subscription-Key`)
  - Endpoints identified:
    1. `/query` – General OData-filtered flight search
    2. `/flight/{airport}/{flightId}` – Single flight details
    3. `/airport/{airport}/departures/{date}` – Daily departure board
    4. `/airport/{airport}/arrivals/{date}` – Daily arrival board

#### Step 3: Deducing Required Inputs & User Flow
- User selects an airport (by 3-letter IATA code, e.g., `ARN`, or case-insensitive city aliases like `stockholm`, `arlanda`).
- User selects a flight date (`YYYY-MM-DD`, defaulting to current UTC/CET date).
- User paginates through results (`PAGE_SIZE = 5` or `50` flights per view) with interactive controls (`[Enter]` next page, `[a]` show all, `[q]` return to menu).
- User can search directly by flight number or run custom OData queries.

#### Step 4: Logic & Process Deduction (Pseudocode)
```python
# Core lookup and processing logic
def fetch_flights(airport_code, date, flight_type):
    # 1. Validate airport and date inputs
    # 2. Call Swedavia endpoint with headers
    # 3. Filter out ghost/empty entries (_is_valid_flight)
    # 4. Enrich city names with country using destinationer.py
    # 5. Format timestamps to Sweden local time (Europe/Stockholm)
    # 6. Display paginated terminal output
```

### 1.2 Technology & Tool Selection
- **Programming Language:** Python 3.10+ (standard, clean terminal handling, robust datetime support)
- **HTTP Client:** `requests` / standard library for reliable REST requests
- **Timezone Management:** `zoneinfo.ZoneInfo("Europe/Stockholm")` for Swedish CET/CEST time conversion
- **Data Storage:** JSON (`city_country.json`) for offline country mapping
- **Version Control:** Git & GitHub for branch tracking and commit history
- **Screen Recording:** OBS Studio / Loom for the minimum 4-minute demonstration video

### 1.3 Research Phase: Problems Encountered & Solutions
- **Problem 1:** Swedavia returns UTC timestamps (`2026-02-25T10:05:00Z`), which are confusing for local Swedish travelers.  
  *Solution:* Built a timestamp conversion utility using `ZoneInfo("Europe/Stockholm")` that formats times to both UTC and local Swedish time (CET/CEST).
- **Problem 2:** Incomplete or "ghost" flight objects in the raw API response with missing flight IDs or times.  
  *Solution:* Implemented an input validation filter `_is_valid_flight(flight)` ensuring entries have at least an ID, an origin/destination, and a scheduled time.
- **Problem 3:** Airport API only returns destination city names without the corresponding country.  
  *Solution:* Created a dedicated lookup module (`destinationer.py`) backed by `city_country.json` to automatically resolve cities to their respective countries.

---

## Phase 2: Implementation & Structure

### 2.1 File Architecture
- `airport.py`: Main executable containing the interactive terminal loop, pagination logic, API calling routines, and Swedavia configuration.
- `destinationer.py`: Helper module handling city-to-country lookup and reverse lookup.
- `city_country.json`: Reference dataset mapping international and domestic destinations.
- `README.md`: Setup instructions and quickstart guide.

### 2.2 Menu Options in `airport.py`
1. **View Arrivals:** Fetch upcoming arrivals for any Swedavia airport on a given date.
2. **View Departures:** Fetch upcoming departures for any Swedavia airport on a given date.
3. **Search Specific Flight:** Direct lookup by flight ID or number.
4. **OData Query:** Advanced filtering on Swedavia's raw dataset.
5. **API Health Check:** Ping endpoints to verify key and connection availability.
6. **Full Auto-Demo:** Automatically test each endpoint and display sample data.

---

## Phase 3: Finalization, Testing & Optimization
- **Pagination Control:** Implemented interactive page breaks so long flight lists do not flood the terminal buffer.
- **Robust Exception Handling:** Network errors, HTTP 401/403 (invalid API key), and HTTP 404 (no flights found) are handled gracefully with friendly terminal prompts.
- **Aliases & Validation:** Users can type "got", "landvetter", "gothenburg", or "GOT" and the program automatically normalizes to the correct Swedavia IATA code.

---

## Phase 4: Problems & Solutions Summary Table
| Phase | Identified Issue | Implemented Solution |
| :--- | :--- | :--- |
| **Research** | Unclear API response format & empty fields | Inspected raw payloads and created `_is_valid_flight()` filter |
| **Research** | City names lack country context | Added `city_country.json` & `destinationer.py` lookup table |
| **Implementation** | Terminal buffer overflow on busy airports (e.g. ARN) | Implemented interactive page navigation (`PAGE_SIZE = 5`) |
| **Implementation** | Date formatting errors from user input | Added strict `YYYY-MM-DD` regex validation with fallback to today |
| **Finalization** | UTC vs Swedish local daylight saving changes | Leveraged Python `zoneinfo` for automatic CET/CEST transitions |

---

## Conclusion & Learnings
- **Accomplishments:** Successfully reverse engineered the target flight information system, implemented clean Python modules, and established complete endpoint coverage for all 10 Swedavia airports.
- **Key Learnings:** Gained practical experience in reverse engineering API contracts, building terminal-based user interfaces with pagination, handling timezone transformations, and structuring technical documentation.
- **Future Improvements:** Add a graphical web dashboard (e.g. React/Tailwind) and real-time push notifications for gate and delay changes.
