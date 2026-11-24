# Swedavia Flightinfo API v2 – Terminal Application

An interactive Python terminal tool built for **APL Project 2026 (Reverse Engineer a Result)** that interfaces with the **Swedavia Flightinfo Open Data API v2** to explore real-time arrivals, departures, flight tracking, and destination statistics across Sweden's 10 state-owned airports.

---

## ✈️ Supported Airports

| IATA | Airport Name | City / Location |
| :--- | :--- | :--- |
| **ARN** | Stockholm Arlanda Airport | Stockholm / Sigtuna |
| **GOT** | Göteborg Landvetter Airport | Gothenburg / Härryda |
| **BMA** | Bromma Stockholm Airport | Stockholm |
| **MMX** | Malmö Airport | Malmö / Svedala |
| **LLA** | Luleå Airport | Luleå / Kallax |
| **UME** | Umeå Airport | Umeå |
| **OSD** | Åre Östersund Airport | Östersund / Frösön |
| **VBY** | Visby Airport | Visby / Gotland |
| **RNB** | Ronneby Airport | Ronneby / Blekinge |
| **KRN** | Kiruna Airport | Kiruna |

*(User input supports case-insensitive city aliases such as `arlanda`, `landvetter`, `malmo`, etc.)*

---

## 📁 Project Structure

```text
├── airport.py          # Main terminal application with interactive menu
├── destinationer.py    # Destination & origin aggregator with country resolution
├── city_country.json   # Reference database mapping global cities to countries
├── DOCUMENTATION.md    # Formal coursework report (Research, Implementation, QA)
└── README.md           # Project guide and instructions
```

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10 or higher
- `requests` library

```bash
pip install requests
```

### 2. Run the Main Application
```bash
python airport.py
```

### 3. Run the Destination Explorer
```bash
python destinationer.py
```

---

## 🧭 Menu Features (`airport.py`)

1. **Visa ankomster (View Arrivals):** Live incoming flights with origin city, country, scheduled & estimated times, terminal, and baggage belts.
2. **Visa avgångar (View Departures):** Live outbound flights with destination city, country, gate, terminal, and scheduled departure.
3. **Sök specifik flygning (Search Flight):** Direct lookup by Flight ID (e.g., `SK100`, `FR4627`, `BLX762`).
4. **Kör OData-fråga (OData Query):** Advanced query filtering using Swedavia's backend query interface.
5. **Kontrollera API-hälsa (Health Check):** Pings Swedavia endpoints and validates the subscription key and response latency.
6. **Kör full auto-demo (Auto Demo):** Guided walkthrough demonstrating all system capabilities.

---

## 🛠️ Key Technical Implementations

- **Timezone Synchronization:** Swedavia returns UTC ISO strings (`2026-02-25T10:05:00Z`). The application uses Python's `zoneinfo` module (`Europe/Stockholm`) to dynamically convert UTC timestamps into local Swedish time (`CET` / `CEST`).
- **Interactive Terminal Pagination:** Flights are paginated (`PAGE_SIZE = 5`) allowing the user to press `[Enter]` for the next page, `[a]` to show all remaining flights, or `[q]` to exit back to the main menu.
- **Rate-limit Protection:** Automatically handles HTTP 429 throttling with exponential backoff and retry.
- **Ghost Entry Filtering:** Raw payloads occasionally contain empty flight legs; the `_is_valid_flight()` function filters out unpopulated records.
