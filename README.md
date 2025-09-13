# APPR Validation Engine

A production-ready Air Passenger Protection Rights (APPR) validation engine designed to ensure compliance with Canadian passenger rights regulations.

## Overview

This FastAPI-based microservice validates flight disruptions against APPR regulations and provides:
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
# Run comprehensive test scenarios
python test_scenarios.py
```

## API Endpoints

### Core Validation
- `POST /validate-appr` - Main APPR validation endpoint
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
├── main.py                 # FastAPI application and endpoints
├── models.py              # Pydantic data models
├── appr_validator.py      # Core validation logic
├── canadian_airports.py   # Canadian airport codes and validation
├── test_scenarios.py      # Comprehensive test scenarios
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Core Components

### Data Models (models.py)
- `FlightInfo`: Flight details with departure/arrival times
- `PassengerInfo`: Passenger type, pricing, and special needs
- `DisruptionEvent`: Disruption details with categories and timing
- `CompensationResult`: Validation results with compensation and rights

### Validation Engine (appr_validator.py)
- **APPRValidator**: Main validation class with business logic
- **Canadian departure check**: APPR applicability determination
- **Compensation calculation**: Rules-based compensation amounts
- **Care obligations**: Time-based passenger care requirements
- **Special passenger handling**: Enhanced protections for minors/disabilities

### Canadian Airports (canadian_airports.py)
- Comprehensive list of 50+ Canadian airport codes
- IATA code validation for APPR eligibility
- Major international and regional airports included

## Test Scenarios

The engine includes 8 comprehensive test scenarios covering:

1. ✅ **4-hour delay within carrier control** → CAD $400
2. ✅ **5-hour weather delay (outside control)** → CAD $0
3. ✅ **10-hour delay within carrier control** → CAD $1000
4. ✅ **US departure (APPR not applicable)** → CAD $0
5. ✅ **Cancellation with short notice** → CAD $700
6. ✅ **Denied boarding domestic** → CAD $900
7. ✅ **Tarmac delay with mandatory disembarkation** → CAD $700
8. ✅ **Minor passenger with enhanced care** → CAD $400

Run with: `python test_scenarios.py`

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