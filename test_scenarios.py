import json
from datetime import datetime, timedelta
from models import (
    APPRValidationRequest,
    FlightInfo,
    PassengerInfo,
    DisruptionEvent,
    DisruptionType,
    DisruptionCategory,
    PassengerType
)
from appr_validator import APPRValidator

def create_test_scenarios():
    """Create comprehensive test scenarios for APPR validation."""
    
    scenarios = []
    
    # Scenario 1: Delay within carrier control (3-6 hours) - Should get $400
    scenarios.append({
        "name": "Delay 4 hours within carrier control - Canadian departure",
        "request": APPRValidationRequest(
            flight_info=FlightInfo(
                flight_number="WS123",
                departure_airport="YYZ",  # Toronto
                arrival_airport="YVR",    # Vancouver
                scheduled_departure=datetime(2024, 3, 15, 8, 0),
                actual_departure=datetime(2024, 3, 15, 12, 0),
                scheduled_arrival=datetime(2024, 3, 15, 11, 0),
                actual_arrival=datetime(2024, 3, 15, 15, 0)
            ),
            passenger_info=PassengerInfo(
                passenger_type=PassengerType.REGULAR,
                ticket_price=350.0,
                booking_class="Economy"
            ),
            disruption_event=DisruptionEvent(
                disruption_type=DisruptionType.DELAY,
                disruption_category=DisruptionCategory.WITHIN_CARRIER_CONTROL,
                delay_duration_hours=4.0,
                reason="Aircraft maintenance"
            )
        ),
        "expected_compensation": 400.0,
        "expected_eligible": True
    })
    
    # Scenario 2: Delay outside carrier control - No compensation
    scenarios.append({
        "name": "Delay 5 hours outside carrier control (weather) - Canadian departure",
        "request": APPRValidationRequest(
            flight_info=FlightInfo(
                flight_number="WS456",
                departure_airport="YYC",  # Calgary
                arrival_airport="YUL",    # Montreal
                scheduled_departure=datetime(2024, 3, 15, 14, 0),
                actual_departure=datetime(2024, 3, 15, 19, 0),
                scheduled_arrival=datetime(2024, 3, 15, 18, 30),
                actual_arrival=datetime(2024, 3, 15, 23, 30)
            ),
            passenger_info=PassengerInfo(
                passenger_type=PassengerType.REGULAR,
                ticket_price=420.0,
                booking_class="Economy"
            ),
            disruption_event=DisruptionEvent(
                disruption_type=DisruptionType.DELAY,
                disruption_category=DisruptionCategory.OUTSIDE_CARRIER_CONTROL,
                delay_duration_hours=5.0,
                reason="Severe weather conditions",
                weather_related=True
            )
        ),
        "expected_compensation": 0.0,
        "expected_eligible": False
    })
    
    # Scenario 3: Long delay (9+ hours) within carrier control - Should get $1000
    scenarios.append({
        "name": "Delay 10 hours within carrier control - Canadian departure",
        "request": APPRValidationRequest(
            flight_info=FlightInfo(
                flight_number="WS789",
                departure_airport="YOW",  # Ottawa
                arrival_airport="YEG",    # Edmonton
                scheduled_departure=datetime(2024, 3, 15, 9, 0),
                actual_departure=datetime(2024, 3, 15, 19, 0),
                scheduled_arrival=datetime(2024, 3, 15, 11, 30),
                actual_arrival=datetime(2024, 3, 15, 21, 30)
            ),
            passenger_info=PassengerInfo(
                passenger_type=PassengerType.REGULAR,
                ticket_price=580.0,
                booking_class="Economy"
            ),
            disruption_event=DisruptionEvent(
                disruption_type=DisruptionType.DELAY,
                disruption_category=DisruptionCategory.WITHIN_CARRIER_CONTROL,
                delay_duration_hours=10.0,
                reason="Crew scheduling issue"
            )
        ),
        "expected_compensation": 1000.0,
        "expected_eligible": True
    })
    
    # Scenario 4: Non-Canadian departure - APPR does not apply
    scenarios.append({
        "name": "Delay from US airport - APPR does not apply",
        "request": APPRValidationRequest(
            flight_info=FlightInfo(
                flight_number="WS999",
                departure_airport="LAX",  # Los Angeles (US)
                arrival_airport="YYZ",    # Toronto
                scheduled_departure=datetime(2024, 3, 15, 12, 0),
                actual_departure=datetime(2024, 3, 15, 16, 0),
                scheduled_arrival=datetime(2024, 3, 15, 20, 0),
                actual_arrival=datetime(2024, 3, 16, 0, 0)
            ),
            passenger_info=PassengerInfo(
                passenger_type=PassengerType.REGULAR,
                ticket_price=650.0,
                booking_class="Economy"
            ),
            disruption_event=DisruptionEvent(
                disruption_type=DisruptionType.DELAY,
                disruption_category=DisruptionCategory.WITHIN_CARRIER_CONTROL,
                delay_duration_hours=4.0,
                reason="Aircraft maintenance"
            )
        ),
        "expected_compensation": 0.0,
        "expected_eligible": False,
        "expected_appr_applicable": False
    })
    
    # Scenario 5: Cancellation with short notice - within carrier control
    scenarios.append({
        "name": "Cancellation with 2 days notice - within carrier control",
        "request": APPRValidationRequest(
            flight_info=FlightInfo(
                flight_number="WS321",
                departure_airport="YHZ",  # Halifax
                arrival_airport="YYZ",    # Toronto
                scheduled_departure=datetime(2024, 3, 15, 16, 0),
                actual_departure=None,
                scheduled_arrival=datetime(2024, 3, 15, 18, 30),
                actual_arrival=None
            ),
            passenger_info=PassengerInfo(
                passenger_type=PassengerType.REGULAR,
                ticket_price=280.0,
                booking_class="Economy"
            ),
            disruption_event=DisruptionEvent(
                disruption_type=DisruptionType.CANCELLATION,
                disruption_category=DisruptionCategory.WITHIN_CARRIER_CONTROL,
                cancellation_notice_days=2,
                delay_duration_hours=6.0,  # Alternative flight delay
                reason="Equipment change"
            )
        ),
        "expected_compensation": 700.0,  # 6-hour delay to alternative
        "expected_eligible": True
    })
    
    # Scenario 6: Denied boarding - domestic flight
    scenarios.append({
        "name": "Denied boarding - domestic flight",
        "request": APPRValidationRequest(
            flight_info=FlightInfo(
                flight_number="WS654",
                departure_airport="YWG",  # Winnipeg
                arrival_airport="YQR",    # Regina
                scheduled_departure=datetime(2024, 3, 15, 7, 30),
                actual_departure=datetime(2024, 3, 15, 7, 30),
                scheduled_arrival=datetime(2024, 3, 15, 8, 45),
                actual_arrival=datetime(2024, 3, 15, 8, 45)
            ),
            passenger_info=PassengerInfo(
                passenger_type=PassengerType.REGULAR,
                ticket_price=220.0,
                booking_class="Economy"
            ),
            disruption_event=DisruptionEvent(
                disruption_type=DisruptionType.DENIED_BOARDING,
                disruption_category=DisruptionCategory.WITHIN_CARRIER_CONTROL,
                reason="Oversold flight"
            )
        ),
        "expected_compensation": 900.0,
        "expected_eligible": True
    })
    
    # Scenario 7: Tarmac delay with regular delay
    scenarios.append({
        "name": "Tarmac delay 5 hours with overall 7-hour delay",
        "request": APPRValidationRequest(
            flight_info=FlightInfo(
                flight_number="WS888",
                departure_airport="YXE",  # Saskatoon
                arrival_airport="YYC",    # Calgary
                scheduled_departure=datetime(2024, 3, 15, 13, 0),
                actual_departure=datetime(2024, 3, 15, 20, 0),
                scheduled_arrival=datetime(2024, 3, 15, 14, 15),
                actual_arrival=datetime(2024, 3, 15, 21, 15)
            ),
            passenger_info=PassengerInfo(
                passenger_type=PassengerType.REGULAR,
                ticket_price=180.0,
                booking_class="Economy"
            ),
            disruption_event=DisruptionEvent(
                disruption_type=DisruptionType.TARMAC_DELAY,
                disruption_category=DisruptionCategory.WITHIN_CARRIER_CONTROL,
                delay_duration_hours=7.0,
                tarmac_delay_hours=5.0,
                reason="Air traffic control delays"
            )
        ),
        "expected_compensation": 700.0,  # 6-9 hour delay
        "expected_eligible": True
    })
    
    # Scenario 8: Minor passenger with delay
    scenarios.append({
        "name": "Minor passenger with 5-hour delay - within carrier control",
        "request": APPRValidationRequest(
            flight_info=FlightInfo(
                flight_number="WS777",
                departure_airport="YQB",  # Quebec City
                arrival_airport="YYZ",    # Toronto
                scheduled_departure=datetime(2024, 3, 15, 11, 0),
                actual_departure=datetime(2024, 3, 15, 16, 0),
                scheduled_arrival=datetime(2024, 3, 15, 12, 30),
                actual_arrival=datetime(2024, 3, 15, 17, 30)
            ),
            passenger_info=PassengerInfo(
                passenger_type=PassengerType.MINOR,
                minor_age=12,
                ticket_price=320.0,
                booking_class="Economy"
            ),
            disruption_event=DisruptionEvent(
                disruption_type=DisruptionType.DELAY,
                disruption_category=DisruptionCategory.WITHIN_CARRIER_CONTROL,
                delay_duration_hours=5.0,
                reason="Mechanical issue"
            )
        ),
        "expected_compensation": 400.0,  # 3-6 hour delay
        "expected_eligible": True
    })
    
    return scenarios

def run_test_scenarios():
    """Run all test scenarios and display results."""
    validator = APPRValidator()
    scenarios = create_test_scenarios()
    
    print("=" * 80)
    print("APPR Validation Engine - Test Scenarios")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\nTest {i}: {scenario['name']}")
        print("-" * 60)
        
        try:
            is_applicable, reason, result = validator.validate_appr_request(scenario['request'])
            
            # Check APPR applicability if specified
            if 'expected_appr_applicable' in scenario:
                if is_applicable != scenario['expected_appr_applicable']:
                    print(f"❌ FAIL: APPR applicability mismatch")
                    print(f"   Expected: {scenario['expected_appr_applicable']}, Got: {is_applicable}")
                    failed += 1
                    continue
            
            # Check compensation eligibility and amount
            expected_eligible = scenario['expected_eligible']
            expected_amount = scenario['expected_compensation']
            
            if result.eligible_for_compensation == expected_eligible and result.compensation_amount == expected_amount:
                print(f"✅ PASS")
                passed += 1
            else:
                print(f"❌ FAIL")
                failed += 1
            
            # Display results
            print(f"   APPR Applicable: {is_applicable}")
            print(f"   Reason: {reason}")
            print(f"   Eligible for Compensation: {result.eligible_for_compensation}")
            print(f"   Compensation Amount: CAD ${result.compensation_amount}")
            print(f"   Expected Amount: CAD ${expected_amount}")
            
            if result.care_obligations:
                print(f"   Care Obligations: {len(result.care_obligations)} items")
            if result.compliance_notes:
                print(f"   Notes: {'; '.join(result.compliance_notes[:2])}")
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 80)
    
    return passed, failed

if __name__ == "__main__":
    run_test_scenarios()