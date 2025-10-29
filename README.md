# APPR Validation Engine

A production-ready Air Passenger Protection Rights (APPR) validation engine designed to ensure compliance with Canadian passenger rights regulations.

## Overview

This FastAPI-based microservice validates flight disruptions against APPR regulations and provides:
- **Single flight validation** - Individual flight disruption analysis
- **Multi-flight journey validation** - Complex multi-leg journey analysis with connection handling
- Compensation eligibility determination
- Compensation amount calculations
- Care obligations based on delay duration
- Passenger rights and rebooking options
- Compliance with Canadian aviation regulations

## Key Features

### APPR Compliance
- ✅ **Canadian Departure Validation**: Only applies to flights departing from Canada
- ✅ **Large Carrier Classifications**: Large carrier specific compensation rates
- ✅ **Six Disruption Types**: Delays, cancellations, denied boarding, tarmac delays, downgrades, baggage issues
- ✅ **Three Control Categories**: Within/outside carrier control, safety-related

### Multi-Flight Journey Support (NEW!)
- ✅ **Connection Analysis**: Automatic missed connection detection
- ✅ **Journey-Level Compensation**: Based on delay to final destination (not sum of individual legs)
- ✅ **Cascading Delay Handling**: Tracks how delays propagate through journey
- ✅ **Smart Rebooking Rights**: Automatic rebooking for all affected segments
- ✅ **Minimum Connection Time**: Configurable per airport (domestic: 45min, international: 60min)
- ✅ **Complex Scenarios**: Handles denied boarding, cancellations, and delays across multiple legs

### Compensation Structure (Large Carrier)
- **3-6 hours**: CAD $400
- **6-9 hours**: CAD $700
- **9+ hours**: CAD $1000
- **Denied boarding**: CAD $900-$2400

### Special Rules
- **Tarmac delays**: Mandatory disembarkation after 4 hours
- **Cancellations**: 14-day notice period affects eligibility
- **Care obligations**: Food (3+ hrs), accommodation (8+ hrs), communication (2+ hrs)
- **Enhanced protections**: Special handling for minors and passengers with disabilities

## Quick Start

### Installation

```bash
# Clone or create the project directory
cd appr-validation

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

### Run the Server

```bash
# Development mode with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **Server**: http://localhost:8000
- **Interactive docs**: http://localhost:8000/docs
- **OpenAPI schema**: http://localhost:8000/openapi.json

### Run Tests

```bash
# Run end-to-end API tests (recommended for validation)
python -m pytest test_e2e.py -v

# Run single-flight test scenarios
python test_scenarios.py

# Run multi-flight journey test scenarios
python test_journey_scenarios.py

# Run all tests
python test_scenarios.py && python test_journey_scenarios.py && python -m pytest test_e2e.py -v
```

**Test Coverage**: 24 E2E tests + 8 single-flight scenarios + 7 journey scenarios = 39 total tests
See [TEST_COVERAGE.md](TEST_COVERAGE.md) for detailed test coverage report.

## API Endpoints

### Core Validation
- `POST /validate-appr` - Single flight APPR validation endpoint
- `POST /validate-journey` - Multi-flight journey validation endpoint (NEW!)
- `GET /health` - Health check
- `GET /appr-info` - APPR regulations information

### Utilities
- `GET /canadian-airports` - List of Canadian airports
- `POST /check-airport` - Check if airport is APPR-eligible

## Usage Examples

### Basic Validation Request

```python
import requests
from datetime import datetime

# Example: 4-hour delay within carrier control from Toronto to Vancouver
request_data = {
    "flight_info": {
        "flight_number": "WS123",
        "departure_airport": "YYZ",  # Toronto
        "arrival_airport": "YVR",    # Vancouver
        "scheduled_departure": "2024-03-15T08:00:00",
        "actual_departure": "2024-03-15T12:00:00",
        "scheduled_arrival": "2024-03-15T11:00:00",  
        "actual_arrival": "2024-03-15T15:00:00"
    },
    "passenger_info": {
        "passenger_type": "regular",
        "ticket_price": 350.0,
        "booking_class": "Economy"
    },
    "disruption_event": {
        "disruption_type": "delay",
        "disruption_category": "within_carrier_control", 
        "delay_duration_hours": 4.0,
        "reason": "Aircraft maintenance"
    }
}

response = requests.post("http://localhost:8000/validate-appr", json=request_data)
result = response.json()

print(f"Eligible: {result['compensation_result']['eligible_for_compensation']}")
print(f"Amount: CAD ${result['compensation_result']['compensation_amount']}")
```

### Multi-Flight Journey Validation Request

```python
import requests
from datetime import datetime, timedelta

# Example: 2-leg journey with missed connection due to delay
# YUL -> YYZ -> YVR (Montreal -> Toronto -> Vancouver)
# First leg delayed by 2 hours, causing missed connection

base_time = datetime(2024, 6, 15, 9, 0, 0)

journey_request = {
    "passenger_info": {
        "passenger_type": "regular",
        "ticket_price": 650.0,
        "booking_class": "economy"
    },
    "flight_legs": [
        {
            "leg_number": 1,
            "flight_info": {
                "flight_number": "AC301",
                "departure_airport": "YUL",
                "arrival_airport": "YYZ",
                "scheduled_departure": base_time.isoformat(),
                "actual_departure": (base_time + timedelta(hours=2)).isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=1, minutes=30)).isoformat(),
                "actual_arrival": (base_time + timedelta(hours=3, minutes=30)).isoformat()
            },
            "is_connection": False,
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 2.0,
                "reason": "Aircraft maintenance"
            }
        },
        {
            "leg_number": 2,
            "flight_info": {
                "flight_number": "AC302",
                "departure_airport": "YYZ",
                "arrival_airport": "YVR",
                "scheduled_departure": (base_time + timedelta(hours=2, minutes=15)).isoformat(),
                "actual_departure": (base_time + timedelta(hours=7)).isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=6, minutes=45)).isoformat(),
                "actual_arrival": (base_time + timedelta(hours=11, minutes=30)).isoformat()
            },
            "is_connection": True,
            "minimum_connection_time_minutes": 45,
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 4.75,
                "reason": "Missed connection due to earlier delay"
            }
        }
    ]
}

response = requests.post("http://localhost:8000/validate-journey", json=journey_request)
result = response.json()

print(f"Origin: {result['origin_airport']}")
print(f"Destination: {result['final_destination']}")
print(f"Journey Delay: {result['total_journey_delay_hours']} hours")
print(f"Missed Connections: {result['missed_connections']}")
print(f"Eligible: {result['journey_compensation_result']['eligible_for_compensation']}")
print(f"Amount: CAD ${result['journey_compensation_result']['compensation_amount']}")
```

### Expected Journey Response

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "is_appr_applicable": true,
  "appr_eligibility_reason": "APPR applies - journey originates from Canadian airport YUL",
  "journey_compensation_result": {
    "eligible_for_compensation": true,
    "compensation_amount": 400.0,
    "care_obligations": [
      "Communication: Provide updates on journey status and passenger rights",
      "Food and drink: Provide meals and refreshments during journey disruption"
    ],
    "rebooking_rights": [
      "Right to rebooking on all remaining journey segments (1 connection(s) missed)"
    ],
    "refund_rights": [
      "Right to refund for remaining journey if rebooking not acceptable"
    ],
    "compliance_notes": [
      "Journey delay of 4.8 hours to final destination - compensation required",
      "Journey disruption: 1 connection(s) missed, affecting remaining itinerary"
    ],
    "alternative_arrangements": [
      "Carrier must rebook passenger on next available flights for all 1 missed connection(s)"
    ]
  },
  "total_journey_delay_hours": 4.8,
  "missed_connections": [2],
  "leg_results": [
    {
      "leg_number": 1,
      "flight_number": "AC301",
      "is_appr_applicable": true,
      "disruption_detected": true,
      "connection_status": "not_applicable"
    },
    {
      "leg_number": 2,
      "flight_number": "AC302",
      "is_appr_applicable": true,
      "disruption_detected": true,
      "connection_status": "missed_due_to_delay",
      "connection_notes": [
        "Connection missed: Only -75 minutes between flights (minimum 45 minutes required)",
        "Flight AC301 delayed, causing missed connection to AC302"
      ]
    }
  ],
  "origin_airport": "YUL",
  "final_destination": "YVR",
  "total_legs": 2
}
```

### Expected Response

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "is_appr_applicable": true,
  "appr_eligibility_reason": "APPR applies - flight departs from Canadian airport YYZ",
  "compensation_result": {
    "eligible_for_compensation": true,
    "compensation_amount": 400.0,
    "care_obligations": [
      "Communication: Provide updates on delay status and passenger rights",
      "Food and drink: Provide meals and refreshments"
    ],
    "rebooking_rights": [
      "Right to rebooking on next available flight at no additional cost"
    ],
    "refund_rights": [
      "Right to refund if passenger chooses not to travel"
    ],
    "compliance_notes": [
      "Delay of 4.0 hours within carrier control - compensation required"
    ]
  }
}
```

## Project Structure

```
appr-validation/
├── main.py                      # FastAPI application and endpoints
├── models.py                    # Pydantic data models (includes journey models)
├── appr_validator.py            # Single-flight validation logic
├── journey_validator.py         # Multi-flight journey validation logic (NEW!)
├── canadian_airports.py         # Canadian airport codes and validation
├── test_scenarios.py            # Single-flight test scenarios
├── test_journey_scenarios.py    # Multi-flight journey test scenarios (NEW!)
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Core Components

### Data Models (models.py)
- `FlightInfo`: Flight details with departure/arrival times
- `PassengerInfo`: Passenger type, pricing, and special needs
- `DisruptionEvent`: Disruption details with categories and timing
- `CompensationResult`: Validation results with compensation and rights
- **Journey Models (NEW!)**:
  - `FlightLeg`: Individual leg within multi-flight journey
  - `ConnectionStatus`: Connection state tracking (successful, missed, etc.)
  - `LegResult`: Validation results for individual journey legs
  - `JourneyValidationRequest`: Multi-flight validation request
  - `JourneyValidationResponse`: Comprehensive journey results

### Single-Flight Validation Engine (appr_validator.py)
- **APPRValidator**: Main validation class with business logic
- **Canadian departure check**: APPR applicability determination
- **Compensation calculation**: Rules-based compensation amounts
- **Care obligations**: Time-based passenger care requirements
- **Special passenger handling**: Enhanced protections for minors/disabilities

### Journey Validation Engine (journey_validator.py - NEW!)
- **JourneyValidator**: Multi-flight journey analysis
- **Missed connection detection**: Automatic detection using connection time thresholds
- **Journey-level compensation**: Based on delay to final destination
- **Cascading delay tracking**: Monitors how delays propagate through legs
- **Connection time validation**: Domestic (45min) vs International (60min) defaults
- **Rebooking orchestration**: Automatic rebooking for all affected remaining segments

### Canadian Airports (canadian_airports.py)
- Comprehensive list of 50+ Canadian airport codes
- IATA code validation for APPR eligibility
- Major international and regional airports included

## Test Scenarios

### Single-Flight Scenarios

The engine includes 8 comprehensive single-flight test scenarios:

1. ✅ **4-hour delay within carrier control** → CAD $400
2. ✅ **5-hour weather delay (outside control)** → CAD $0
3. ✅ **10-hour delay within carrier control** → CAD $1000
4. ✅ **US departure (APPR not applicable)** → CAD $0
5. ✅ **Cancellation with short notice** → CAD $700
6. ✅ **Denied boarding domestic** → CAD $900
7. ✅ **Tarmac delay with mandatory disembarkation** → CAD $700
8. ✅ **Minor passenger with enhanced care** → CAD $400

Run with: `python test_scenarios.py`

### Multi-Flight Journey Scenarios (NEW!)

The engine includes 7 comprehensive journey test scenarios:

1. ✅ **Successful 2-leg journey (no disruptions)** → CAD $0, all connections successful
2. ✅ **Missed connection due to delay** → CAD $400, 1 connection missed, 4.8hr journey delay
3. ✅ **Cancelled leg causing long delay** → CAD $1000, 12hr journey delay with overnight care
4. ✅ **3-leg journey with multiple delays** → Complex cascading delay analysis
5. ✅ **Denied boarding on connection** → CAD $900, rebooking all remaining segments
6. ✅ **Journey from non-Canadian airport** → APPR not applicable (LAX origin)
7. ✅ **Minor passenger with missed connection** → Enhanced care obligations throughout journey

Run with: `python test_journey_scenarios.py`

## Deployment

### Production Configuration

```bash
# Install production ASGI server
pip install gunicorn

# Run with gunicorn (Linux/Mac)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or use uvicorn for production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

```bash
# Optional configuration
LOG_LEVEL=info
PORT=8000
HOST=0.0.0.0
```

## APPR Regulations Covered

### Applicability
- Flights departing from Canadian airports only
- Large carrier classification
- Domestic and international flights

### Disruption Categories
- **Within Carrier Control**: Full compensation required
- **Within Carrier Control (Safety)**: Care obligations only
- **Outside Carrier Control**: Limited care obligations

### Compensation Tiers
- Delays 3-6 hours: CAD $400
- Delays 6-9 hours: CAD $700  
- Delays 9+ hours: CAD $1000
- Denied boarding: CAD $900-$2400

### Care Obligations Timeline
- **2+ hours**: Communication and status updates
- **3+ hours**: Food and beverages provided
- **8+ hours**: Overnight accommodation and transportation