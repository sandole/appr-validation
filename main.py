import uuid
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from models import (
    APPRValidationRequest, 
    APPRValidationResponse,
    CompensationResult
)
from appr_validator import APPRValidator
from canadian_airports import CANADIAN_AIRPORTS, is_canadian_airport

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="APPR Validation Engine",
    description="Air Passenger Protection Rights validation engine for compliance",
    version="1.0.0",
    contact={
        "name": "Customer Protection Team"
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize validator
validator = APPRValidator()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for logging and error responses."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred while processing your request",
            "request_id": str(uuid.uuid4())
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "APPR Validation Engine",
        "version": "1.0.0"
    }

@app.get("/appr-info")
async def get_appr_info():
    """Get information about APPR regulations and coverage."""
    return {
        "appr_coverage": {
            "applies_to": "Flights departing from Canada",
            "carrier_classification": "Large Carrier",
            "disruption_types": [
                "delays", "cancellations", "denied_boarding", 
                "tarmac_delays", "downgrades", "baggage_issues"
            ]
        },
        "compensation_structure": {
            "large_carrier_rates": {
                "3_to_6_hours": "CAD $400",
                "6_to_9_hours": "CAD $700",
                "9_plus_hours": "CAD $1000",
                "denied_boarding_domestic": "CAD $900",
                "denied_boarding_international": "CAD $1800-$2400"
            }
        },
        "disruption_categories": {
            "within_carrier_control": "Full compensation required",
            "within_carrier_control_safety": "No monetary compensation, care obligations apply",
            "outside_carrier_control": "No compensation, limited care obligations"
        },
        "care_obligations": {
            "2_hours": "Communication and updates",
            "3_hours": "Food and beverages",
            "8_hours": "Accommodation and transportation"
        },
        "canadian_airports_count": len(CANADIAN_AIRPORTS),
        "tarmac_delay_rule": "Mandatory disembarkation after 4 hours"
    }

@app.post("/validate-appr", response_model=APPRValidationResponse)
async def validate_appr(request: APPRValidationRequest):
    """
    Main APPR validation endpoint.
    
    Validates a flight disruption against APPR regulations and returns
    compensation eligibility, amounts, and passenger rights.
    """
    try:
        request_id = str(uuid.uuid4())
        
        logger.info(f"Processing APPR validation request {request_id} for flight {request.flight_info.flight_number}")
        
        # Validate the request
        is_applicable, reason, compensation_result = validator.validate_appr_request(request)
        
        # Create response
        response = APPRValidationResponse(
            request_id=request_id,
            is_appr_applicable=is_applicable,
            appr_eligibility_reason=reason,
            compensation_result=compensation_result,
            processing_timestamp=datetime.utcnow()
        )
        
        logger.info(f"APPR validation completed for request {request_id}. Eligible: {compensation_result.eligible_for_compensation}, Amount: CAD ${compensation_result.compensation_amount}")
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error processing APPR validation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during validation")

@app.get("/canadian-airports")
async def get_canadian_airports():
    """Get list of Canadian airports covered by APPR."""
    return {
        "airports": CANADIAN_AIRPORTS,
        "total_count": len(CANADIAN_AIRPORTS),
        "note": "APPR applies only to flights departing from these Canadian airports"
    }

@app.post("/check-airport")
async def check_airport_eligibility(airport_code: str):
    """Check if a specific airport code is Canadian and APPR-eligible."""
    airport_code = airport_code.upper().strip()
    
    if len(airport_code) != 3:
        raise HTTPException(status_code=400, detail="Airport code must be exactly 3 characters")
    
    is_canadian = is_canadian_airport(airport_code)
    airport_name = CANADIAN_AIRPORTS.get(airport_code, "Unknown")
    
    return {
        "airport_code": airport_code,
        "is_canadian": is_canadian,
        "airport_name": airport_name if is_canadian else "Not a Canadian airport",
        "appr_eligible": is_canadian,
        "note": "APPR applies only to flights departing from Canadian airports"
    }

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "APPR Validation Engine",
        "version": "1.0.0",
        "description": "Air Passenger Protection Rights validation for Canadian flight disruptions",
        "endpoints": {
            "validate": "/validate-appr",
            "health": "/health",
            "info": "/appr-info",
            "airports": "/canadian-airports",
            "check_airport": "/check-airport"
        },
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)