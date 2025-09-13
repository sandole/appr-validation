from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class DisruptionType(str, Enum):
    DELAY = "delay"
    CANCELLATION = "cancellation"
    DENIED_BOARDING = "denied_boarding"
    TARMAC_DELAY = "tarmac_delay"
    DOWNGRADE = "downgrade"
    BAGGAGE_ISSUE = "baggage_issue"


class DisruptionCategory(str, Enum):
    WITHIN_CARRIER_CONTROL = "within_carrier_control"
    WITHIN_CARRIER_CONTROL_SAFETY = "within_carrier_control_safety"
    OUTSIDE_CARRIER_CONTROL = "outside_carrier_control"


class PassengerType(str, Enum):
    REGULAR = "regular"
    MINOR = "minor"
    DISABILITY = "disability"


class FlightInfo(BaseModel):
    flight_number: str = Field(..., description="Flight number (e.g., WS123)")
    departure_airport: str = Field(..., description="IATA airport code for departure")
    arrival_airport: str = Field(..., description="IATA airport code for arrival")
    scheduled_departure: datetime = Field(..., description="Scheduled departure datetime")
    actual_departure: Optional[datetime] = Field(None, description="Actual departure datetime")
    scheduled_arrival: datetime = Field(..., description="Scheduled arrival datetime")
    actual_arrival: Optional[datetime] = Field(None, description="Actual arrival datetime")
    
    @field_validator('departure_airport', 'arrival_airport')
    @classmethod
    def validate_airport_codes(cls, v):
        if len(v) != 3 or not v.isalpha():
            raise ValueError('Airport code must be 3 letters')
        return v.upper()


class PassengerInfo(BaseModel):
    passenger_type: PassengerType = PassengerType.REGULAR
    minor_age: Optional[int] = Field(None, description="Age if passenger is a minor")
    has_disability: bool = Field(False, description="Whether passenger has disability requiring assistance")
    ticket_price: float = Field(..., description="Original ticket price in CAD")
    booking_class: str = Field(..., description="Booking class (economy, business, etc.)")


class DisruptionEvent(BaseModel):
    disruption_type: DisruptionType
    disruption_category: DisruptionCategory
    delay_duration_hours: Optional[float] = Field(None, description="Delay duration in hours")
    cancellation_notice_days: Optional[int] = Field(None, description="Days of advance notice for cancellation")
    tarmac_delay_hours: Optional[float] = Field(None, description="Tarmac delay duration in hours")
    reason: Optional[str] = Field(None, description="Reason for disruption")
    weather_related: bool = Field(False, description="Whether disruption was weather-related")


class CompensationResult(BaseModel):
    eligible_for_compensation: bool
    compensation_amount: float = Field(0.0, description="Compensation amount in CAD")
    care_obligations: List[str] = Field(default_factory=list)
    rebooking_rights: List[str] = Field(default_factory=list)
    refund_rights: List[str] = Field(default_factory=list)
    compliance_notes: List[str] = Field(default_factory=list)
    alternative_arrangements: List[str] = Field(default_factory=list)


class APPRValidationRequest(BaseModel):
    flight_info: FlightInfo
    passenger_info: PassengerInfo
    disruption_event: DisruptionEvent


class APPRValidationResponse(BaseModel):
    request_id: str = Field(..., description="Unique identifier for this validation request")
    is_appr_applicable: bool = Field(..., description="Whether APPR regulations apply")
    appr_eligibility_reason: str = Field(..., description="Reason for APPR eligibility determination")
    compensation_result: CompensationResult
    processing_timestamp: datetime = Field(default_factory=datetime.utcnow)