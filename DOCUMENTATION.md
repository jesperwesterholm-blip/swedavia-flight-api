# Flight API Exploration – Project Documentation

> **Course:** APL Project 2026  
> **Task:** 4. Reverse Engineer a Result  
> **Language:** English (Required)  
> **Repository:** GitHub (`jesperwesterholm-blip/swedavia-flight-api`)  

---

## Executive Summary
This project reverse engineers and implements a fully featured Python terminal application that interfaces with the **Swedavia Flightinfo Open Data API v2**. The application provides real-time arrivals, departures, detailed flight lookups, and destination statistics across all 10 state-owned commercial airports in Sweden operated by Swedavia.

---

## Phase 1: Research Phase (Preliminary Study)

### 1.1 Objective & Reverse Engineering Analysis
The objective was to analyze a demonstration video and output of a flight tracking tool, deduce its underlying architecture, data contracts, and operational logic, and re-create a high-fidelity implementation.

#### Step 1: Observing the Target Output
- The target system displayed a live terminal console with real-time airport schedules.
- Key data entities identified from responses:
  - Flight identification (`flightId`, airline name, IATA/ICAO code)
  - Airport details (3-letter IATA code, e.g., `ARN`, `GOT`, Swedish/English names)
  - Timestamp attributes: Scheduled UTC time, estimated time, and actual event time
  - Flight status indicators (e.g., On Time, Delayed, Landed, Departed, Gate Closed, Boarding)
  - Origin and destination city names.

#### Step 2: Deducing the Underlying API
- Identified the source API as the official **Swedavia Flightinfo API v2**:
  - **Base URL:** `https://api.swedavia.se/flightinfo/v2`
  - **Authentication:** Subscription key passed via HTTP header `Ocp-Apim-Subscription-Key`
  - **Endpoints Analyzed:**
    1. `/{airport}/departures/{date}` – Live departures for an airport on a specific date
    2. `/{airport}/arrivals/{date}` – Live arrivals for an airport on a specific date
    3. `/flight/{airport}/{flightId}` – Single flight lookup
    4. `/query` – Generic OData-filtered flight endpoint

#### Step 3: Deducing Required Inputs & User Flow
- User selects an airport (by 3-letter IATA code, e.g., `ARN`, or case-insensitive aliases like `arlanda`, `landvetter`, `malmo`).
- User selects a date (`YYYY-MM-DD`, defaulting to today's date).
- The system presents a filtered, chronologically sorted view of flights.
- Results are paginated (5 flights per page) with interactive navigation (`[Enter]` next page, `[a]` show all, `[q]` return to menu).
- Additional modules provide airport destination aggregation, OData queries, and automated API health checks.

#### Step 4: Logic & Process Deduction (Pseudocode)
```python
def fetch_and_display_flights(airport_code, date, is_departure):
    # 1. Validate inputs (normalize airport aliases and date format)
    # 2. Call Swedavia live REST endpoint with subscription header
    # 3. Filter out invalid/deleted records (flightLegStatus == 'DEL')
    # 4. Filter for real-time board parity (hide departed/landed flights in live view)
    # 5. Enrich city names with country mappings using destinationer module
    # 6. Format UTC timestamps to Swedish local time (Europe/Stockholm, CET/CEST)
    # 7. Calculate real-time delay minutes (estimatedUtc - scheduledUtc)
    # 8. Render paginated, formatted terminal cards
```

### 1.2 Technology & Tool Selection
- **Programming Language:** Python 3.10+ (clean terminal handling, rich datetime & JSON standard libraries)
- **HTTP Client:** `requests` for robust REST communication and status code handling
- **Timezone Management:** `zoneinfo.ZoneInfo("Europe/Stockholm")` with fallback support for accurate CET/CEST daylight saving time
- **Data Enrichment:** Local JSON database (`city_country.json`) mapping 203 cities across 52 countries
- **Version Control:** Git & GitHub (`main` branch)
- **Screen Recording:** OBS Studio / Loom for technical demonstration video

### 1.3 Research Phase: Problems Encountered & Solutions
- **Problem 1: Generic `/query` endpoint returned non-live / incomplete data.**  
  *Investigation:* Early tests against `/query` returned test/static records that did not match Swedavia's live consumer board.  
  *Solution:* Switched to the dedicated live endpoints `/{airport}/departures/{date}` and `/{airport}/arrivals/{date}`, which reflect real-time airport operations.
- **Problem 2: Missing country metadata in Swedavia's API.**  
  *Investigation:* Swedavia returns destination names like `"London LHR"`, `"Paris CDG"`, or `"München"`, without country names.  
  *Solution:* Developed `destinationer.py` and an expanded offline dictionary `city_country.json` that strips airport suffix codes and maps cities to their correct countries.
- **Problem 3: UTC timestamps vs. local passenger expectations.**  
  *Investigation:* Timestamps in API responses are ISO 8601 UTC (e.g., `12:25:00Z`), causing confusion when comparing against local Swedish flight monitors.  
  *Solution:* Built local time conversions using `Europe/Stockholm` timezone, displaying local CET/CEST prominently while retaining UTC for technical reference.

---

## Phase 2: Implementation & Structure

### 2.1 File Architecture
- **`airport.py`**: Core interactive terminal application. Contains API request handlers, rate limiting protection, airport alias resolvers, filtering logic, and interactive pagination.
- **`destinationer.py`**: Dedicated utility module for sanitizing airport/city strings and resolving countries.
- **`city_country.json`**: Static mapping database containing 203 international and domestic airport cities across 52 nations.
- **`README.md`**: Complete user guide, setup instructions, and table of supported Swedavia airports.
- **`DOCUMENTATION.md`**: Full project technical report adhering to course rubric.

### 2.2 Menu Features
1. **View Arrivals:** Live arrivals sorted chronologically by scheduled time, displaying original schedule, estimated arrival, delay calculations, terminal, and assigned baggage claim belt (`baggageClaimUnit`).
2. **View Departures:** Live departures showing scheduled time, gate assignments, boarding/gate status actions (`Bordas`, `Gå till gate`, `Sista utrop`, `Gate stängd`), and delay tracking.
3. **Search Specific Flight:** Search by flight number (e.g., `SK1422`, `QR167`) across all daily flights.
4. **OData Query:** Direct OData filter execution on raw flight data for power users.
5. **API Health Check:** Live connectivity and credential verification with Swedavia gateway.
6. **Full Auto-Demo:** Automated walkthrough executing all core API capabilities sequentially.

### 2.3 Implementation Phase: Problems Encountered & Solutions
- **Problem 1: Windows ZoneInfo crash (`ModuleNotFoundError: No module named 'tzdata'`).**  
  *Investigation:* On Windows, Python's `zoneinfo` requires the `tzdata` package to access the IANA time zone database. Running on clean Windows machines threw `ZoneInfoNotFoundError: 'No time zone found with key Europe/Stockholm'`.  
  *Solution:* Added automatic fallback handling in `airport.py` using fixed UTC+1 offset with warning suppression, and documented `pip install tzdata` for full daylight-saving support.
- **Problem 2: API Rate Limiting (HTTP 429 Too Many Requests).**  
  *Investigation:* Rapid successive requests occasionally triggered Swedavia API rate throttling.  
  *Solution:* Implemented backoff delays and informative console alerts explaining the rate limit and suggesting brief wait times.
- **Problem 3: Console text wrapping on split screens.**  
  *Investigation:* When users ran the terminal alongside web browsers (split screen ~60 character width), long lines wrapped awkwardly in the middle of words (e.g., `(+43 min f` / `örsenad)`).  
  *Solution:* Redesigned the card output format with concise labels (`Ny tid: 14:08 CET (+43 min)`), ensuring all output fits cleanly on narrow command prompts.

---

## Phase 3: Finalization, Testing & Optimization

### 3.1 Real-Time Board Parity (Matching Swedavia's Web Portal)
A critical optimization phase was ensuring exact 1-to-1 data parity with Swedavia's public flight boards (`swedavia.com/arlanda/departures/` and `arrivals/`):
- **Departures Parity:** Departed flights (`status == 'ACT'` or `actualUtc`) are automatically pruned from the active board after 5 minutes, matching Swedavia's physical airport monitor behavior.
- **Arrivals Parity:** On Swedavia's web arrival board, flights disappear the moment they land (`status == 'LAN'` or `actualUtc`), leaving only planes that are currently en route. The default view was configured to replicate this behavior, while Option `[2]` allows users to inspect the full day's history including landed flights and baggage belts.
- **Scheduled Time Sorting:** Flight lists are sorted strictly by their original scheduled timetable time (`scheduledUtc`), maintaining consistent chronological order while highlighting delays prominently.

### 3.2 Finalization Phase: Problems Encountered & Solutions
- **Problem 1: Landed arrivals remaining in upcoming view.**  
  *Investigation:* Landed flights (e.g., SK1422 Copenhagen) stayed in the list to show baggage claim belts, causing discrepancy with Swedavia's web board which hides landed planes.  
  *Solution:* Updated default arrival filter to exclude flights with `actualUtc` or `LAN` status from the upcoming list, providing exact parity with Swedavia's online table.
- **Problem 2: Baggage claim vs. Gate confusion on arrivals.**  
  *Investigation:* Initial versions rendered gate information for arrivals where passengers actually need the baggage reclaim carousel number.  
  *Solution:* Extracted `baggage.baggageClaimUnit` from Swedavia's payload and formatted it as `Bagageband: Band X`.

---

## Phase 4: Problems & Solutions Summary Table

| Phase | Problem Identified | Root Cause | Implemented Solution |
| :--- | :--- | :--- | :--- |
| **Research** | Incomplete data from `/query` | `/query` returns unstructured test data | Replaced with live endpoints `/{airport}/departures` and `arrivals` |
| **Research** | Missing country names | API provides only destination city | Created `destinationer.py` and 203-city `city_country.json` |
| **Research** | UTC timestamps confusing | API outputs UTC `Z` strings | Converted to local Swedish time (`Europe/Stockholm`) |
| **Implementation** | `tzdata` missing on Windows | Windows Python lacks built-in IANA tz database | Added resilient UTC+1 fallback + `pip install tzdata` documentation |
| **Implementation** | HTTP 429 Rate Limiting | Swedavia subscription key throttling | Added automatic retry delay and HTTP error feedback |
| **Implementation** | Terminal line wrap on narrow windows | Output strings exceeded 70 columns | Streamlined card formatting to fit 60-column terminal splits |
| **Finalization** | Departed/Landed flights cluttering board | Raw API returns all flights regardless of completion | Added live board parity filtering (5-min departure cutoff, landed arrival filter) |
| **Finalization** | Gate shown instead of baggage belt on arrivals | Reused departure card template | Mapped `baggage.baggageClaimUnit` to baggage carousel output |

---

## Conclusion & Learnings
- **Accomplishments:** Successfully reverse engineered the target flight information application, achieving full functional equivalence and live parity with Swedavia's official digital boards across 10 commercial Swedish airports.
- **Key Learnings:**
  1. Gained deep understanding of API reverse engineering and REST contract analysis.
  2. Mastered practical Python datetime conversion, timezone handling across operating systems, and resilient fallbacks.
  3. Learned the importance of data normalization, user input validation (IATA code aliases), and clean terminal UI design.
  4. Understood real-world airport data lifecycles (scheduled vs. estimated vs. actual departure/arrival times).
- **Future Improvements:**
  - Build a web-based dashboard using React/Tailwind to mirror airport display monitors graphically.
  - Implement push notifications (via webhooks or SMS) when a tracked flight changes gate or reports delays over 15 minutes.
