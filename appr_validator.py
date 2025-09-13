from datetime import datetime, timedelta
from typing import List, Tuple
from models import (
    APPRValidationRequest, 
    CompensationResult, 
    DisruptionType, 
    DisruptionCategory,
    PassengerType
)
from canadian_airports import is_canadian_airport


class APPRValidator:
    """
    APPR (Air Passenger Protection Rights) validation engine.
    Handles Canadian passenger rights regulations compliance.
    """
    
    LARGE_CARRIER_COMPENSATION = {
        "3_to_6_hours": 400.0,
        "6_to_9_hours": 700.0,
        "9_plus_hours": 1000.0,
        "denied_boarding_domestic": 900.0,
        "denied_boarding_international": 1800.0,
        "denied_boarding_international_long": 2400.0
    }
    
    def __init__(self):
        self.carrier_type = "large"
    
    def validate_appr_request(self, request: APPRValidationRequest) -> Tuple[bool, str, CompensationResult]:
        """
        Main validation method that determines APPR applicability and compensation.
        
        Returns:
            Tuple of (is_appr_applicable, reason, compensation_result)
        """
        # Check if APPR applies (flight must depart from Canada)
        if not is_canadian_airport(request.flight_info.departure_airport):
            return False, f"APPR does not apply - flight departs from {request.flight_info.departure_airport} (non-Canadian airport)", CompensationResult(eligible_for_compensation=False)
        
        # APPR applies - now determine compensation and rights
        appr_reason = f"APPR applies - flight departs from Canadian airport {request.flight_info.departure_airport}"
        
        compensation_result = self._calculate_compensation_and_rights(request)
        
        return True, appr_reason, compensation_result
    
    def _calculate_compensation_and_rights(self, request: APPRValidationRequest) -> CompensationResult:
        """Calculate compensation amount and passenger rights based on disruption details."""
        
        result = CompensationResult(eligible_for_compensation=False)
        
        disruption = request.disruption_event
        flight = request.flight_info
        passenger = request.passenger_info
        
        # Handle different disruption types
        if disruption.disruption_type == DisruptionType.DELAY:
            result = self._handle_delay(request)
        elif disruption.disruption_type == DisruptionType.CANCELLATION:
            result = self._handle_cancellation(request)
        elif disruption.disruption_type == DisruptionType.DENIED_BOARDING:
            result = self._handle_denied_boarding(request)
        elif disruption.disruption_type == DisruptionType.TARMAC_DELAY:
            result = self._handle_tarmac_delay(request)
        elif disruption.disruption_type == DisruptionType.DOWNGRADE:
            result = self._handle_downgrade(request)
        elif disruption.disruption_type == DisruptionType.BAGGAGE_ISSUE:
            result = self._handle_baggage_issue(request)
        
        # Add care obligations based on delay duration
        self._add_care_obligations(request, result)
        
        # Add rebooking and refund rights
        self._add_rebooking_refund_rights(request, result)
        
        # Add special passenger considerations
        self._add_special_passenger_rights(request, result)
        
        return result
    
    def _handle_delay(self, request: APPRValidationRequest) -> CompensationResult:
        """Handle flight delays."""
        result = CompensationResult(eligible_for_compensation=False)
        disruption = request.disruption_event
        
        if not disruption.delay_duration_hours:
            result.compliance_notes.append("Delay duration not specified")
            return result
        
        delay_hours = disruption.delay_duration_hours
        
        # No compensation for delays under 3 hours
        if delay_hours < 3:
            result.compliance_notes.append(f"Delay of {delay_hours} hours is under 3-hour threshold - no compensation required")
            return result
        
        # Check disruption category
        if disruption.disruption_category == DisruptionCategory.OUTSIDE_CARRIER_CONTROL:
            result.compliance_notes.append("Delay outside carrier control - no monetary compensation required")
            return result
        
        if disruption.disruption_category == DisruptionCategory.WITHIN_CARRIER_CONTROL_SAFETY:
            result.compliance_notes.append("Delay within carrier control but required for safety - no monetary compensation required")
            return result
        
        # Within carrier control - full compensation
        if disruption.disruption_category == DisruptionCategory.WITHIN_CARRIER_CONTROL:
            result.eligible_for_compensation = True
            
            if 3 <= delay_hours < 6:
                result.compensation_amount = self.LARGE_CARRIER_COMPENSATION["3_to_6_hours"]
            elif 6 <= delay_hours < 9:
                result.compensation_amount = self.LARGE_CARRIER_COMPENSATION["6_to_9_hours"]
            else:  # 9+ hours
                result.compensation_amount = self.LARGE_CARRIER_COMPENSATION["9_plus_hours"]
            
            result.compliance_notes.append(f"Delay of {delay_hours} hours within carrier control - compensation required")
        
        return result
    
    def _handle_cancellation(self, request: APPRValidationRequest) -> CompensationResult:
        """Handle flight cancellations."""
        result = CompensationResult(eligible_for_compensation=False)
        disruption = request.disruption_event
        
        # Check if 14-day advance notice was given
        if disruption.cancellation_notice_days and disruption.cancellation_notice_days >= 14:
            result.compliance_notes.append("Cancellation with 14+ days notice - no compensation required")
            return result
        
        # Same logic as delays for compensation categories
        if disruption.disruption_category == DisruptionCategory.OUTSIDE_CARRIER_CONTROL:
            result.compliance_notes.append("Cancellation outside carrier control - no monetary compensation required")
            return result
        
        if disruption.disruption_category == DisruptionCategory.WITHIN_CARRIER_CONTROL_SAFETY:
            result.compliance_notes.append("Cancellation within carrier control but required for safety - no monetary compensation required")
            return result
        
        # Within carrier control - compensation based on delay to alternative flight
        if disruption.disruption_category == DisruptionCategory.WITHIN_CARRIER_CONTROL:
            result.eligible_for_compensation = True
            
            # Use delay_duration_hours to represent delay to alternative flight
            delay_hours = disruption.delay_duration_hours or 0
            
            if delay_hours < 3:
                result.compensation_amount = 0
                result.compliance_notes.append("Alternative flight within 3 hours - no compensation required")
            elif 3 <= delay_hours < 6:
                result.compensation_amount = self.LARGE_CARRIER_COMPENSATION["3_to_6_hours"]
            elif 6 <= delay_hours < 9:
                result.compensation_amount = self.LARGE_CARRIER_COMPENSATION["6_to_9_hours"]
            else:  # 9+ hours
                result.compensation_amount = self.LARGE_CARRIER_COMPENSATION["9_plus_hours"]
            
            result.compliance_notes.append(f"Cancellation within carrier control - compensation based on {delay_hours} hour delay to alternative flight")
        
        return result
    
    def _handle_denied_boarding(self, request: APPRValidationRequest) -> CompensationResult:
        """Handle denied boarding situations."""
        result = CompensationResult(eligible_for_compensation=True)
        flight = request.flight_info
        
        # Determine if international flight
        is_international = not (is_canadian_airport(flight.departure_airport) and 
                               is_canadian_airport(flight.arrival_airport))
        
        if not is_international:
            # Domestic flight
            result.compensation_amount = self.LARGE_CARRIER_COMPENSATION["denied_boarding_domestic"]
            result.compliance_notes.append("Denied boarding on domestic flight")
        else:
            # International flight - check distance/duration
            # For simplicity, using higher amount for all international flights
            # In production, would calculate actual distance
            result.compensation_amount = self.LARGE_CARRIER_COMPENSATION["denied_boarding_international_long"]
            result.compliance_notes.append("Denied boarding on international flight")
        
        return result
    
    def _handle_tarmac_delay(self, request: APPRValidationRequest) -> CompensationResult:
        """Handle tarmac delays."""
        result = CompensationResult(eligible_for_compensation=False)
        disruption = request.disruption_event
        
        if not disruption.tarmac_delay_hours:
            result.compliance_notes.append("Tarmac delay duration not specified")
            return result
        
        tarmac_hours = disruption.tarmac_delay_hours
        
        # Mandatory disembarkation after 4 hours
        if tarmac_hours >= 4:
            result.compliance_notes.append("Tarmac delay of 4+ hours requires mandatory disembarkation")
            result.alternative_arrangements.append("Passenger disembarkation required after 4 hours on tarmac")
        
        # Regular delay compensation rules also apply
        if disruption.delay_duration_hours:
            delay_result = self._handle_delay(request)
            result.eligible_for_compensation = delay_result.eligible_for_compensation
            result.compensation_amount = delay_result.compensation_amount
            result.compliance_notes.extend(delay_result.compliance_notes)
        
        return result
    
    def _handle_downgrade(self, request: APPRValidationRequest) -> CompensationResult:
        """Handle service downgrades."""
        result = CompensationResult(eligible_for_compensation=True)
        passenger = request.passenger_info
        
        # Calculate refund based on ticket price difference
        # For simplicity, using percentage of original ticket price
        if passenger.booking_class.lower() in ["business", "first"]:
            result.compensation_amount = passenger.ticket_price * 0.75  # 75% refund for premium downgrades
        else:
            result.compensation_amount = passenger.ticket_price * 0.50  # 50% refund for economy downgrades
        
        result.compliance_notes.append(f"Service downgrade from {passenger.booking_class} class")
        
        return result
    
    def _handle_baggage_issue(self, request: APPRValidationRequest) -> CompensationResult:
        """Handle baggage issues."""
        result = CompensationResult(eligible_for_compensation=False)
        
        # Baggage issues typically handled under separate regulations
        # But carrier must provide compensation for essential items
        result.compliance_notes.append("Baggage issue - carrier must reimburse reasonable interim expenses")
        result.alternative_arrangements.append("Reimbursement for essential items while baggage is delayed")
        
        return result
    
    def _add_care_obligations(self, request: APPRValidationRequest, result: CompensationResult):
        """Add care obligations based on delay duration."""
        disruption = request.disruption_event
        delay_hours = disruption.delay_duration_hours or disruption.tarmac_delay_hours or 0
        
        if delay_hours >= 2:
            result.care_obligations.append("Communication: Provide updates on delay status and passenger rights")
        
        if delay_hours >= 3:
            result.care_obligations.append("Food and drink: Provide meals and refreshments")
        
        if delay_hours >= 8:
            result.care_obligations.append("Accommodation: Provide overnight accommodation if required")
            result.care_obligations.append("Transportation: Provide transport between airport and accommodation")
    
    def _add_rebooking_refund_rights(self, request: APPRValidationRequest, result: CompensationResult):
        """Add rebooking and refund rights."""
        disruption = request.disruption_event
        
        if disruption.disruption_type in [DisruptionType.DELAY, DisruptionType.CANCELLATION]:
            result.rebooking_rights.append("Right to rebooking on next available flight at no additional cost")
            result.refund_rights.append("Right to refund if passenger chooses not to travel")
        
        if disruption.disruption_type == DisruptionType.DENIED_BOARDING:
            result.rebooking_rights.append("Right to alternative flight or rebooking")
            result.refund_rights.append("Right to full refund if alternative not acceptable")
    
    def _add_special_passenger_rights(self, request: APPRValidationRequest, result: CompensationResult):
        """Add special considerations for minors and passengers with disabilities."""
        passenger = request.passenger_info
        
        if passenger.passenger_type == PassengerType.MINOR:
            result.compliance_notes.append("Minor passenger - enhanced care obligations apply")
            result.care_obligations.append("Special assistance for unaccompanied minors")
        
        if passenger.has_disability or passenger.passenger_type == PassengerType.DISABILITY:
            result.compliance_notes.append("Passenger with disability - enhanced protections apply")
            result.care_obligations.append("Assistance appropriate to passenger's disability")
            result.alternative_arrangements.append("Priority rebooking for passengers with disabilities")