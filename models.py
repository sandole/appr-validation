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


# Multi-Flight Journey Support Models

class FlightLeg(BaseModel):
    """Represents a single flight leg within a multi-flight journey."""
    leg_number: int = Field(..., description="Sequential leg number (1, 2, 3, etc.)")
    flight_info: FlightInfo
    disruption_event: Optional[DisruptionEvent] = Field(None, description="Disruption specific to this leg")
    is_connection: bool = Field(True, description="Whether this leg is a connecting flight")
    minimum_connection_time_minutes: Optional[int] = Field(None, description="Minimum connection time required at this connection point")


class ConnectionStatus(str, Enum):
    """Status of a connection between flight legs."""
    SUCCESSFUL = "successful"
    MISSED_DUE_TO_DELAY = "missed_due_to_delay"
    MISSED_DUE_TO_CANCELLATION = "missed_due_to_cancellation"
    NOT_APPLICABLE = "not_applicable"


class LegResult(BaseModel):
    """Validation result for a single leg within a journey."""
    leg_number: int
    flight_number: str
    is_appr_applicable: bool
    disruption_detected: bool
    connection_status: ConnectionStatus = ConnectionStatus.NOT_APPLICABLE
    connection_notes: List[str] = Field(default_factory=list)
    individual_compensation: CompensationResult = Field(default_factory=lambda: CompensationResult(eligible_for_compensation=False))


class JourneyValidationRequest(BaseModel):
    """Request for validating a multi-flight journey."""
    passenger_info: PassengerInfo
    flight_legs: List[FlightLeg] = Field(..., description="Ordered list of flight legs (from origin to final destination)")
    journey_level_disruption: Optional[DisruptionEvent] = Field(None, description="Journey-wide disruption event (e.g., entire journey cancelled)")

    @field_validator('flight_legs')
    @classmethod
    def validate_flight_legs(cls, v):
        if len(v) < 2:
            raise ValueError('Journey must have at least 2 flight legs')

        # Validate leg numbers are sequential
        for i, leg in enumerate(v, start=1):
            if leg.leg_number != i:
                raise ValueError(f'Flight leg numbers must be sequential starting from 1')

        # Validate connections (arrival airport of leg N must match departure of leg N+1)
        for i in range(len(v) - 1):
            if v[i].flight_info.arrival_airport != v[i + 1].flight_info.departure_airport:
                raise ValueError(f'Connection mismatch: leg {i+1} arrives at {v[i].flight_info.arrival_airport} but leg {i+2} departs from {v[i + 1].flight_info.departure_airport}')

        return v


class JourneyValidationResponse(BaseModel):
    """Response for journey validation with multi-flight support."""
    request_id: str = Field(..., description="Unique identifier for this validation request")
    is_appr_applicable: bool = Field(..., description="Whether APPR regulations apply to this journey")
    appr_eligibility_reason: str = Field(..., description="Reason for APPR eligibility determination")

    # Journey-level results
    journey_compensation_result: CompensationResult = Field(..., description="Aggregated compensation for entire journey")
    total_journey_delay_hours: Optional[float] = Field(None, description="Total delay to final destination")
    missed_connections: List[int] = Field(default_factory=list, description="List of leg numbers where connections were missed")

    # Individual leg results
    leg_results: List[LegResult] = Field(default_factory=list, description="Detailed results for each leg")

    # Journey summary
    origin_airport: str = Field(..., description="Journey origin")
    final_destination: str = Field(..., description="Journey final destination")
    total_legs: int = Field(..., description="Total number of flight legs")

    processing_timestamp: datetime = Field(default_factory=datetime.utcnow)