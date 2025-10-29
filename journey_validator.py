from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from models import (
    JourneyValidationRequest,
    JourneyValidationResponse,
    FlightLeg,
    LegResult,
    ConnectionStatus,
    CompensationResult,
    APPRValidationRequest,
    DisruptionType,
    DisruptionCategory,
    DisruptionEvent
)
from appr_validator import APPRValidator
from canadian_airports import is_canadian_airport
import uuid


class JourneyValidator:
    """
    Journey-level APPR validation engine for multi-flight itineraries.
    Handles complex scenarios including missed connections, cascading delays,
    and journey-wide compensation calculations.
    """

    def __init__(self):
        self.single_flight_validator = APPRValidator()
        # Minimum connection time defaults (in minutes)
        self.DEFAULT_DOMESTIC_CONNECTION_TIME = 45
        self.DEFAULT_INTERNATIONAL_CONNECTION_TIME = 60

    def validate_journey(self, request: JourneyValidationRequest) -> JourneyValidationResponse:
        """
        Main validation method for multi-flight journeys.

        Returns:
            JourneyValidationResponse with comprehensive journey analysis
        """
        request_id = str(uuid.uuid4())

        # Check if APPR applies (journey must originate from Canada)
        first_leg = request.flight_legs[0]
        origin_airport = first_leg.flight_info.departure_airport

        if not is_canadian_airport(origin_airport):
            return self._create_non_applicable_response(
                request_id=request_id,
                request=request,
                reason=f"APPR does not apply - journey originates from {origin_airport} (non-Canadian airport)"
            )

        # APPR applies - perform comprehensive journey analysis
        leg_results = self._validate_individual_legs(request)
        missed_connections = self._detect_missed_connections(request, leg_results)
        journey_delay = self._calculate_journey_delay(request, missed_connections)
        journey_compensation = self._calculate_journey_compensation(request, leg_results, missed_connections, journey_delay)

        # Build response
        last_leg = request.flight_legs[-1]
        response = JourneyValidationResponse(
            request_id=request_id,
            is_appr_applicable=True,
            appr_eligibility_reason=f"APPR applies - journey originates from Canadian airport {origin_airport}",
            journey_compensation_result=journey_compensation,
            total_journey_delay_hours=journey_delay,
            missed_connections=missed_connections,
            leg_results=leg_results,
            origin_airport=origin_airport,
            final_destination=last_leg.flight_info.arrival_airport,
            total_legs=len(request.flight_legs)
        )

        return response

    def _validate_individual_legs(self, request: JourneyValidationRequest) -> List[LegResult]:
        """Validate each leg individually using single-flight validator."""
        leg_results = []

        for leg in request.flight_legs:
            # Create single-flight validation request
            single_flight_request = APPRValidationRequest(
                flight_info=leg.flight_info,
                passenger_info=request.passenger_info,
                disruption_event=leg.disruption_event or DisruptionEvent(
                    disruption_type=DisruptionType.DELAY,
                    disruption_category=DisruptionCategory.OUTSIDE_CARRIER_CONTROL,
                    delay_duration_hours=0
                )
            )

            # Validate leg
            is_applicable, reason, compensation = self.single_flight_validator.validate_appr_request(
                single_flight_request
            )

            leg_result = LegResult(
                leg_number=leg.leg_number,
                flight_number=leg.flight_info.flight_number,
                is_appr_applicable=is_applicable,
                disruption_detected=leg.disruption_event is not None,
                individual_compensation=compensation
            )

            leg_results.append(leg_result)

        return leg_results

    def _detect_missed_connections(
        self,
        request: JourneyValidationRequest,
        leg_results: List[LegResult]
    ) -> List[int]:
        """
        Detect missed connections due to delays or cancellations.

        Returns:
            List of leg numbers where connections were missed
        """
        missed_connections = []

        for i in range(len(request.flight_legs) - 1):
            current_leg = request.flight_legs[i]
            next_leg = request.flight_legs[i + 1]
            current_result = leg_results[i]
            next_result = leg_results[i + 1]

            # Get minimum connection time
            min_connection_minutes = (
                next_leg.minimum_connection_time_minutes or
                self._get_default_connection_time(current_leg, next_leg)
            )

            # Check if connection was missed
            connection_status, notes = self._check_connection_status(
                current_leg, next_leg, min_connection_minutes
            )

            # Update leg result with connection information
            next_result.connection_status = connection_status
            next_result.connection_notes = notes

            if connection_status in [ConnectionStatus.MISSED_DUE_TO_DELAY, ConnectionStatus.MISSED_DUE_TO_CANCELLATION]:
                missed_connections.append(next_leg.leg_number)

        return missed_connections

    def _check_connection_status(
        self,
        current_leg: FlightLeg,
        next_leg: FlightLeg,
        min_connection_minutes: int
    ) -> Tuple[ConnectionStatus, List[str]]:
        """
        Check if a connection was successful or missed.

        Returns:
            Tuple of (ConnectionStatus, list of notes)
        """
        notes = []

        # If current leg was cancelled, connection is definitely missed
        if current_leg.disruption_event and current_leg.disruption_event.disruption_type == DisruptionType.CANCELLATION:
            notes.append(f"Connection missed due to cancellation of flight {current_leg.flight_info.flight_number}")
            return ConnectionStatus.MISSED_DUE_TO_CANCELLATION, notes

        # If next leg was cancelled independently, mark it but don't count as missed connection from previous leg
        if next_leg.disruption_event and next_leg.disruption_event.disruption_type == DisruptionType.CANCELLATION:
            notes.append(f"Flight {next_leg.flight_info.flight_number} was cancelled")
            return ConnectionStatus.MISSED_DUE_TO_CANCELLATION, notes

        # Check if delay caused missed connection
        actual_arrival = current_leg.flight_info.actual_arrival
        scheduled_departure = next_leg.flight_info.scheduled_departure

        if actual_arrival and scheduled_departure:
            # Calculate actual connection time
            connection_time = (scheduled_departure - actual_arrival).total_seconds() / 60  # in minutes

            if connection_time < min_connection_minutes:
                notes.append(
                    f"Connection missed: Only {connection_time:.0f} minutes between flights "
                    f"(minimum {min_connection_minutes} minutes required)"
                )
                notes.append(f"Flight {current_leg.flight_info.flight_number} delayed, causing missed connection to {next_leg.flight_info.flight_number}")
                return ConnectionStatus.MISSED_DUE_TO_DELAY, notes

        # Connection was successful
        notes.append(f"Connection successful at {current_leg.flight_info.arrival_airport}")
        return ConnectionStatus.SUCCESSFUL, notes

    def _get_default_connection_time(self, current_leg: FlightLeg, next_leg: FlightLeg) -> int:
        """Get default minimum connection time based on route type."""
        connection_airport = current_leg.flight_info.arrival_airport

        # Check if this is an international connection
        current_origin = current_leg.flight_info.departure_airport
        next_destination = next_leg.flight_info.arrival_airport

        is_international_connection = (
            not is_canadian_airport(current_origin) or
            not is_canadian_airport(connection_airport) or
            not is_canadian_airport(next_destination)
        )

        if is_international_connection:
            return self.DEFAULT_INTERNATIONAL_CONNECTION_TIME
        else:
            return self.DEFAULT_DOMESTIC_CONNECTION_TIME

    def _calculate_journey_delay(
        self,
        request: JourneyValidationRequest,
        missed_connections: List[int]
    ) -> Optional[float]:
        """
        Calculate total delay to final destination.
        This is the key metric for journey-level compensation.

        Returns:
            Delay in hours, or None if no delay
        """
        last_leg = request.flight_legs[-1]

        # If there are missed connections, we need to calculate the delay differently
        if missed_connections:
            # For missed connections, use the delay_duration_hours from the last leg's disruption
            # This represents when the passenger actually arrived vs. when they should have arrived
            if last_leg.disruption_event and last_leg.disruption_event.delay_duration_hours:
                return last_leg.disruption_event.delay_duration_hours

            # If not specified, try to calculate from actual vs. scheduled arrival
            if last_leg.flight_info.actual_arrival and last_leg.flight_info.scheduled_arrival:
                delay_timedelta = last_leg.flight_info.actual_arrival - last_leg.flight_info.scheduled_arrival
                return delay_timedelta.total_seconds() / 3600  # convert to hours

        # No missed connections - check if final leg was delayed
        if last_leg.disruption_event and last_leg.disruption_event.delay_duration_hours:
            return last_leg.disruption_event.delay_duration_hours

        # Check actual vs scheduled arrival times
        if last_leg.flight_info.actual_arrival and last_leg.flight_info.scheduled_arrival:
            delay_timedelta = last_leg.flight_info.actual_arrival - last_leg.flight_info.scheduled_arrival
            delay_hours = delay_timedelta.total_seconds() / 3600
            return delay_hours if delay_hours > 0 else None

        return None

    def _calculate_journey_compensation(
        self,
        request: JourneyValidationRequest,
        leg_results: List[LegResult],
        missed_connections: List[int],
        journey_delay_hours: Optional[float]
    ) -> CompensationResult:
        """
        Calculate compensation for the entire journey.

        Key principle: Compensation is based on delay to FINAL DESTINATION, not sum of individual legs.
        """
        result = CompensationResult(eligible_for_compensation=False)

        # Determine the disruption category for compensation purposes
        # Use the most passenger-favorable interpretation
        disruption_category = self._determine_journey_disruption_category(request, missed_connections)

        # Check if any leg had denied boarding
        denied_boarding_leg = self._check_denied_boarding(request)
        if denied_boarding_leg:
            return self._handle_journey_denied_boarding(request, denied_boarding_leg)

        # Calculate compensation based on journey delay
        if journey_delay_hours is not None and journey_delay_hours >= 3:
            # Only compensate if within carrier control
            if disruption_category == DisruptionCategory.WITHIN_CARRIER_CONTROL:
                result.eligible_for_compensation = True

                # Apply standard APPR compensation tiers based on journey delay
                if 3 <= journey_delay_hours < 6:
                    result.compensation_amount = 400.0
                elif 6 <= journey_delay_hours < 9:
                    result.compensation_amount = 700.0
                else:  # 9+ hours
                    result.compensation_amount = 1000.0

                result.compliance_notes.append(
                    f"Journey delay of {journey_delay_hours:.1f} hours to final destination - compensation required"
                )
            elif disruption_category == DisruptionCategory.OUTSIDE_CARRIER_CONTROL:
                result.compliance_notes.append(
                    f"Journey delay of {journey_delay_hours:.1f} hours due to circumstances outside carrier control - no monetary compensation required"
                )
            elif disruption_category == DisruptionCategory.WITHIN_CARRIER_CONTROL_SAFETY:
                result.compliance_notes.append(
                    f"Journey delay of {journey_delay_hours:.1f} hours required for safety - no monetary compensation required"
                )

        # Add journey-level care obligations
        self._add_journey_care_obligations(journey_delay_hours, result)

        # Add rebooking rights for missed connections
        if missed_connections:
            result.rebooking_rights.append(
                f"Right to rebooking on all remaining journey segments ({len(missed_connections)} connection(s) missed)"
            )
            result.refund_rights.append("Right to refund for remaining journey if rebooking not acceptable")
            result.alternative_arrangements.append(
                f"Carrier must rebook passenger on next available flights for all {len(missed_connections)} missed connection(s)"
            )

        # Add special passenger considerations
        self._add_journey_special_passenger_rights(request, result)

        # Add journey-specific notes
        if missed_connections:
            result.compliance_notes.append(
                f"Journey disruption: {len(missed_connections)} connection(s) missed, affecting remaining itinerary"
            )

        return result

    def _determine_journey_disruption_category(
        self,
        request: JourneyValidationRequest,
        missed_connections: List[int]
    ) -> DisruptionCategory:
        """
        Determine the disruption category for the journey.
        Uses most passenger-favorable interpretation when multiple categories exist.
        """
        categories = []

        # Check journey-level disruption
        if request.journey_level_disruption:
            categories.append(request.journey_level_disruption.disruption_category)

        # Check individual leg disruptions
        for leg in request.flight_legs:
            if leg.disruption_event:
                categories.append(leg.disruption_event.disruption_category)

        if not categories:
            # No disruptions specified, default to outside carrier control
            return DisruptionCategory.OUTSIDE_CARRIER_CONTROL

        # Priority: within_carrier_control > within_carrier_control_safety > outside_carrier_control
        # This ensures passenger gets compensation if ANY leg was within carrier control
        if DisruptionCategory.WITHIN_CARRIER_CONTROL in categories:
            return DisruptionCategory.WITHIN_CARRIER_CONTROL
        elif DisruptionCategory.WITHIN_CARRIER_CONTROL_SAFETY in categories:
            return DisruptionCategory.WITHIN_CARRIER_CONTROL_SAFETY
        else:
            return DisruptionCategory.OUTSIDE_CARRIER_CONTROL

    def _check_denied_boarding(self, request: JourneyValidationRequest) -> Optional[FlightLeg]:
        """Check if any leg had denied boarding."""
        for leg in request.flight_legs:
            if leg.disruption_event and leg.disruption_event.disruption_type == DisruptionType.DENIED_BOARDING:
                return leg
        return None

    def _handle_journey_denied_boarding(
        self,
        request: JourneyValidationRequest,
        denied_boarding_leg: FlightLeg
    ) -> CompensationResult:
        """
        Handle denied boarding on any leg of the journey.
        Denied boarding affects the entire remaining journey.
        """
        result = CompensationResult(eligible_for_compensation=True)

        # Create a single-flight request for the denied boarding leg
        single_request = APPRValidationRequest(
            flight_info=denied_boarding_leg.flight_info,
            passenger_info=request.passenger_info,
            disruption_event=denied_boarding_leg.disruption_event
        )

        # Use single-flight validator for denied boarding calculation
        _, _, denied_boarding_result = self.single_flight_validator.validate_appr_request(single_request)

        # Copy compensation details
        result.compensation_amount = denied_boarding_result.compensation_amount
        result.compliance_notes = denied_boarding_result.compliance_notes.copy()
        result.compliance_notes.append(
            f"Denied boarding on leg {denied_boarding_leg.leg_number} affects entire journey"
        )

        # Add journey-specific rebooking rights
        result.rebooking_rights.append(
            f"Right to rebooking on all remaining journey segments (from leg {denied_boarding_leg.leg_number} onward)"
        )
        result.refund_rights.append("Right to full refund for remaining journey if alternative not acceptable")

        return result

    def _add_journey_care_obligations(self, journey_delay_hours: Optional[float], result: CompensationResult):
        """Add care obligations for journey-level delays."""
        if journey_delay_hours is None:
            return

        if journey_delay_hours >= 2:
            result.care_obligations.append("Communication: Provide updates on journey status and passenger rights")

        if journey_delay_hours >= 3:
            result.care_obligations.append("Food and drink: Provide meals and refreshments during journey disruption")

        if journey_delay_hours >= 8:
            result.care_obligations.append("Accommodation: Provide overnight accommodation if journey extends overnight")
            result.care_obligations.append("Transportation: Provide transport between airport and accommodation")

    def _add_journey_special_passenger_rights(
        self,
        request: JourneyValidationRequest,
        result: CompensationResult
    ):
        """Add special considerations for vulnerable passengers on multi-leg journeys."""
        passenger = request.passenger_info

        if passenger.passenger_type.value == "minor":
            result.compliance_notes.append("Minor passenger - enhanced care obligations apply throughout journey")
            result.care_obligations.append("Special assistance for unaccompanied minors during connections and disruptions")

        if passenger.has_disability:
            result.compliance_notes.append("Passenger with disability - enhanced protections apply throughout journey")
            result.care_obligations.append("Assistance appropriate to passenger's disability at all connection points")
            result.alternative_arrangements.append("Priority rebooking for passengers with disabilities on all journey segments")

    def _create_non_applicable_response(
        self,
        request_id: str,
        request: JourneyValidationRequest,
        reason: str
    ) -> JourneyValidationResponse:
        """Create a response for journeys where APPR does not apply."""
        first_leg = request.flight_legs[0]
        last_leg = request.flight_legs[-1]

        return JourneyValidationResponse(
            request_id=request_id,
            is_appr_applicable=False,
            appr_eligibility_reason=reason,
            journey_compensation_result=CompensationResult(eligible_for_compensation=False),
            origin_airport=first_leg.flight_info.departure_airport,
            final_destination=last_leg.flight_info.arrival_airport,
            total_legs=len(request.flight_legs)
        )
