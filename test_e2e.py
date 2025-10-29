"""
End-to-End Test Suite for APPR Validation Engine

Tests all API endpoints with real HTTP requests to ensure:
1. Existing single-flight validation works correctly (no regressions)
2. New multi-flight journey validation works as expected
3. Error handling and edge cases are properly handled
4. All endpoints return correct status codes and response formats
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from main import app

# Create test client
client = TestClient(app)


class TestHealthAndInfo:
    """Test health check and info endpoints."""

    def test_health_endpoint(self):
        """Test health check returns 200 and correct structure."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "APPR Validation Engine"
        assert data["version"] == "1.0.0"

    def test_root_endpoint(self):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "APPR Validation Engine"
        assert data["version"] == "2.0.0"
        assert "validate_single_flight" in data["endpoints"]
        assert "validate_journey" in data["endpoints"]
        assert "Multi-flight journey validation" in data["features"]

    def test_appr_info_endpoint(self):
        """Test APPR info endpoint returns regulations info."""
        response = client.get("/appr-info")
        assert response.status_code == 200
        data = response.json()
        assert "appr_coverage" in data
        assert "compensation_structure" in data
        assert "multi_flight_support" in data["appr_coverage"]
        assert data["appr_coverage"]["multi_flight_support"] == "Yes - handles connecting flights and missed connections"

    def test_canadian_airports_endpoint(self):
        """Test Canadian airports endpoint."""
        response = client.get("/canadian-airports")
        assert response.status_code == 200
        data = response.json()
        assert "airports" in data
        assert data["total_count"] > 50
        assert "YYZ" in data["airports"]
        assert "YVR" in data["airports"]

    def test_check_airport_canadian(self):
        """Test airport check for Canadian airport."""
        response = client.post("/check-airport?airport_code=YYZ")
        assert response.status_code == 200
        data = response.json()
        assert data["airport_code"] == "YYZ"
        assert data["is_canadian"] == True
        assert data["appr_eligible"] == True
        assert "Toronto" in data["airport_name"]

    def test_check_airport_non_canadian(self):
        """Test airport check for non-Canadian airport."""
        response = client.post("/check-airport?airport_code=LAX")
        assert response.status_code == 200
        data = response.json()
        assert data["airport_code"] == "LAX"
        assert data["is_canadian"] == False
        assert data["appr_eligible"] == False


class TestSingleFlightValidation:
    """Test single-flight APPR validation (existing functionality)."""

    def test_delay_within_carrier_control_4_hours(self):
        """Test 4-hour delay within carrier control - should get CAD $400."""
        base_time = datetime(2024, 3, 15, 8, 0, 0)
        request_data = {
            "flight_info": {
                "flight_number": "WS123",
                "departure_airport": "YYZ",
                "arrival_airport": "YVR",
                "scheduled_departure": base_time.isoformat(),
                "actual_departure": (base_time + timedelta(hours=4)).isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat(),
                "actual_arrival": (base_time + timedelta(hours=9)).isoformat()
            },
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 350.0,
                "booking_class": "economy"
            },
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 4.0,
                "reason": "Aircraft maintenance"
            }
        }

        response = client.post("/validate-appr", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["is_appr_applicable"] == True
        assert data["compensation_result"]["eligible_for_compensation"] == True
        assert data["compensation_result"]["compensation_amount"] == 400.0
        assert len(data["compensation_result"]["care_obligations"]) >= 2
        assert "request_id" in data
        assert "processing_timestamp" in data

    def test_delay_outside_carrier_control(self):
        """Test weather delay (outside carrier control) - no compensation."""
        base_time = datetime(2024, 3, 15, 8, 0, 0)
        request_data = {
            "flight_info": {
                "flight_number": "AC100",
                "departure_airport": "YUL",
                "arrival_airport": "YYZ",
                "scheduled_departure": base_time.isoformat(),
                "actual_departure": (base_time + timedelta(hours=5)).isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=6)).isoformat(),
                "actual_arrival": (base_time + timedelta(hours=11)).isoformat()
            },
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 300.0,
                "booking_class": "economy"
            },
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "outside_carrier_control",
                "delay_duration_hours": 5.0,
                "reason": "Severe weather",
                "weather_related": True
            }
        }

        response = client.post("/validate-appr", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["is_appr_applicable"] == True
        assert data["compensation_result"]["eligible_for_compensation"] == False
        assert data["compensation_result"]["compensation_amount"] == 0.0

    def test_long_delay_9_plus_hours(self):
        """Test 10-hour delay within carrier control - should get CAD $1000."""
        base_time = datetime(2024, 3, 15, 8, 0, 0)
        request_data = {
            "flight_info": {
                "flight_number": "WS456",
                "departure_airport": "YVR",
                "arrival_airport": "YYZ",
                "scheduled_departure": base_time.isoformat(),
                "actual_departure": (base_time + timedelta(hours=10)).isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat(),
                "actual_arrival": (base_time + timedelta(hours=15)).isoformat()
            },
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 400.0,
                "booking_class": "economy"
            },
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 10.0,
                "reason": "Crew scheduling issues"
            }
        }

        response = client.post("/validate-appr", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["compensation_result"]["eligible_for_compensation"] == True
        assert data["compensation_result"]["compensation_amount"] == 1000.0
        assert len(data["compensation_result"]["care_obligations"]) >= 4  # 2hr, 3hr, 8hr thresholds

    def test_denied_boarding_domestic(self):
        """Test denied boarding on domestic flight - should get CAD $900."""
        base_time = datetime(2024, 3, 15, 8, 0, 0)
        request_data = {
            "flight_info": {
                "flight_number": "AC200",
                "departure_airport": "YYZ",
                "arrival_airport": "YVR",
                "scheduled_departure": base_time.isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat()
            },
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 500.0,
                "booking_class": "economy"
            },
            "disruption_event": {
                "disruption_type": "denied_boarding",
                "disruption_category": "within_carrier_control",
                "reason": "Oversold flight"
            }
        }

        response = client.post("/validate-appr", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["compensation_result"]["eligible_for_compensation"] == True
        assert data["compensation_result"]["compensation_amount"] == 900.0

    def test_cancellation_with_notice(self):
        """Test cancellation with 14+ days notice - no compensation."""
        base_time = datetime(2024, 3, 15, 8, 0, 0)
        request_data = {
            "flight_info": {
                "flight_number": "WS789",
                "departure_airport": "YYC",
                "arrival_airport": "YYZ",
                "scheduled_departure": base_time.isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=4)).isoformat()
            },
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 350.0,
                "booking_class": "economy"
            },
            "disruption_event": {
                "disruption_type": "cancellation",
                "disruption_category": "within_carrier_control",
                "cancellation_notice_days": 15,
                "reason": "Route optimization"
            }
        }

        response = client.post("/validate-appr", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["compensation_result"]["eligible_for_compensation"] == False
        assert "14+ days notice" in str(data["compensation_result"]["compliance_notes"])

    def test_non_canadian_departure_not_applicable(self):
        """Test flight departing from US - APPR not applicable."""
        base_time = datetime(2024, 3, 15, 8, 0, 0)
        request_data = {
            "flight_info": {
                "flight_number": "UA100",
                "departure_airport": "LAX",
                "arrival_airport": "YVR",
                "scheduled_departure": base_time.isoformat(),
                "actual_departure": (base_time + timedelta(hours=5)).isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=3)).isoformat(),
                "actual_arrival": (base_time + timedelta(hours=8)).isoformat()
            },
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 400.0,
                "booking_class": "economy"
            },
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 5.0,
                "reason": "Crew issue"
            }
        }

        response = client.post("/validate-appr", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["is_appr_applicable"] == False
        assert "non-Canadian airport" in data["appr_eligibility_reason"]
        assert data["compensation_result"]["eligible_for_compensation"] == False

    def test_minor_passenger_enhanced_care(self):
        """Test minor passenger gets enhanced care obligations."""
        base_time = datetime(2024, 3, 15, 8, 0, 0)
        request_data = {
            "flight_info": {
                "flight_number": "AC300",
                "departure_airport": "YYZ",
                "arrival_airport": "YUL",
                "scheduled_departure": base_time.isoformat(),
                "actual_departure": (base_time + timedelta(hours=5)).isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=2)).isoformat(),
                "actual_arrival": (base_time + timedelta(hours=7)).isoformat()
            },
            "passenger_info": {
                "passenger_type": "minor",
                "minor_age": 12,
                "ticket_price": 250.0,
                "booking_class": "economy"
            },
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 5.0,
                "reason": "Maintenance"
            }
        }

        response = client.post("/validate-appr", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["compensation_result"]["eligible_for_compensation"] == True
        assert data["compensation_result"]["compensation_amount"] == 400.0
        assert any("minor" in note.lower() for note in data["compensation_result"]["compliance_notes"])
        assert any("minor" in care.lower() for care in data["compensation_result"]["care_obligations"])


class TestJourneyValidation:
    """Test multi-flight journey validation (new functionality)."""

    def test_successful_two_leg_journey_no_disruptions(self):
        """Test successful 2-leg journey with no disruptions."""
        base_time = datetime(2024, 6, 15, 8, 0, 0)
        request_data = {
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 500.0,
                "booking_class": "economy"
            },
            "flight_legs": [
                {
                    "leg_number": 1,
                    "flight_info": {
                        "flight_number": "AC100",
                        "departure_airport": "YYZ",
                        "arrival_airport": "YVR",
                        "scheduled_departure": base_time.isoformat(),
                        "actual_departure": base_time.isoformat(),
                        "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat(),
                        "actual_arrival": (base_time + timedelta(hours=5)).isoformat()
                    },
                    "is_connection": False
                },
                {
                    "leg_number": 2,
                    "flight_info": {
                        "flight_number": "AC200",
                        "departure_airport": "YVR",
                        "arrival_airport": "YYC",
                        "scheduled_departure": (base_time + timedelta(hours=6, minutes=30)).isoformat(),
                        "actual_departure": (base_time + timedelta(hours=6, minutes=30)).isoformat(),
                        "scheduled_arrival": (base_time + timedelta(hours=8)).isoformat(),
                        "actual_arrival": (base_time + timedelta(hours=8)).isoformat()
                    },
                    "is_connection": True,
                    "minimum_connection_time_minutes": 60
                }
            ]
        }

        response = client.post("/validate-journey", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["is_appr_applicable"] == True
        assert data["origin_airport"] == "YYZ"
        assert data["final_destination"] == "YYC"
        assert data["total_legs"] == 2
        assert len(data["missed_connections"]) == 0
        assert data["journey_compensation_result"]["eligible_for_compensation"] == False
        assert data["journey_compensation_result"]["compensation_amount"] == 0.0
        assert len(data["leg_results"]) == 2

    def test_missed_connection_due_to_delay(self):
        """Test missed connection caused by first leg delay."""
        base_time = datetime(2024, 6, 15, 9, 0, 0)
        request_data = {
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
                        "delay_duration_hours": 4.75
                    }
                }
            ]
        }

        response = client.post("/validate-journey", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["is_appr_applicable"] == True
        assert data["origin_airport"] == "YUL"
        assert data["final_destination"] == "YVR"
        assert len(data["missed_connections"]) == 1
        assert 2 in data["missed_connections"]
        assert data["total_journey_delay_hours"] >= 4.0
        assert data["journey_compensation_result"]["eligible_for_compensation"] == True
        assert data["journey_compensation_result"]["compensation_amount"] == 400.0  # 3-6 hour delay

        # Check connection status
        leg2_result = data["leg_results"][1]
        assert leg2_result["connection_status"] == "missed_due_to_delay"
        assert len(leg2_result["connection_notes"]) > 0

    def test_cancelled_leg_long_journey_delay(self):
        """Test cancelled connection causing 12-hour journey delay."""
        base_time = datetime(2024, 6, 20, 14, 0, 0)
        request_data = {
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 450.0,
                "booking_class": "economy"
            },
            "flight_legs": [
                {
                    "leg_number": 1,
                    "flight_info": {
                        "flight_number": "WS400",
                        "departure_airport": "YYC",
                        "arrival_airport": "YYZ",
                        "scheduled_departure": base_time.isoformat(),
                        "actual_departure": base_time.isoformat(),
                        "scheduled_arrival": (base_time + timedelta(hours=4)).isoformat(),
                        "actual_arrival": (base_time + timedelta(hours=4)).isoformat()
                    },
                    "is_connection": False
                },
                {
                    "leg_number": 2,
                    "flight_info": {
                        "flight_number": "WS401",
                        "departure_airport": "YYZ",
                        "arrival_airport": "YHZ",
                        "scheduled_departure": (base_time + timedelta(hours=5, minutes=30)).isoformat(),
                        "actual_departure": (base_time + timedelta(hours=17, minutes=30)).isoformat(),
                        "scheduled_arrival": (base_time + timedelta(hours=7, minutes=30)).isoformat(),
                        "actual_arrival": (base_time + timedelta(hours=19, minutes=30)).isoformat()
                    },
                    "is_connection": True,
                    "minimum_connection_time_minutes": 60,
                    "disruption_event": {
                        "disruption_type": "cancellation",
                        "disruption_category": "within_carrier_control",
                        "delay_duration_hours": 12.0,
                        "cancellation_notice_days": 0,
                        "reason": "Aircraft unavailable"
                    }
                }
            ]
        }

        response = client.post("/validate-journey", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["is_appr_applicable"] == True
        assert data["total_journey_delay_hours"] == 12.0
        assert data["journey_compensation_result"]["eligible_for_compensation"] == True
        assert data["journey_compensation_result"]["compensation_amount"] == 1000.0  # 9+ hour delay
        assert len(data["journey_compensation_result"]["care_obligations"]) >= 4  # All care tiers

    def test_denied_boarding_on_connection(self):
        """Test denied boarding on second leg of journey."""
        base_time = datetime(2024, 7, 10, 10, 0, 0)
        request_data = {
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 550.0,
                "booking_class": "economy"
            },
            "flight_legs": [
                {
                    "leg_number": 1,
                    "flight_info": {
                        "flight_number": "WS600",
                        "departure_airport": "YYZ",
                        "arrival_airport": "YYC",
                        "scheduled_departure": base_time.isoformat(),
                        "actual_departure": base_time.isoformat(),
                        "scheduled_arrival": (base_time + timedelta(hours=4)).isoformat(),
                        "actual_arrival": (base_time + timedelta(hours=4)).isoformat()
                    },
                    "is_connection": False
                },
                {
                    "leg_number": 2,
                    "flight_info": {
                        "flight_number": "WS601",
                        "departure_airport": "YYC",
                        "arrival_airport": "YVR",
                        "scheduled_departure": (base_time + timedelta(hours=5, minutes=30)).isoformat(),
                        "actual_departure": (base_time + timedelta(hours=9)).isoformat(),
                        "scheduled_arrival": (base_time + timedelta(hours=7)).isoformat(),
                        "actual_arrival": (base_time + timedelta(hours=10, minutes=30)).isoformat()
                    },
                    "is_connection": True,
                    "minimum_connection_time_minutes": 60,
                    "disruption_event": {
                        "disruption_type": "denied_boarding",
                        "disruption_category": "within_carrier_control",
                        "reason": "Oversold flight"
                    }
                }
            ]
        }

        response = client.post("/validate-journey", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["is_appr_applicable"] == True
        assert data["journey_compensation_result"]["eligible_for_compensation"] == True
        assert data["journey_compensation_result"]["compensation_amount"] == 900.0  # Domestic denied boarding
        assert any("denied boarding" in note.lower() for note in data["journey_compensation_result"]["compliance_notes"])

    def test_journey_from_non_canadian_airport(self):
        """Test journey starting from non-Canadian airport - APPR not applicable."""
        base_time = datetime(2024, 7, 15, 12, 0, 0)
        request_data = {
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 400.0,
                "booking_class": "economy"
            },
            "flight_legs": [
                {
                    "leg_number": 1,
                    "flight_info": {
                        "flight_number": "AC700",
                        "departure_airport": "LAX",
                        "arrival_airport": "YVR",
                        "scheduled_departure": base_time.isoformat(),
                        "actual_departure": (base_time + timedelta(hours=3)).isoformat(),
                        "scheduled_arrival": (base_time + timedelta(hours=3)).isoformat(),
                        "actual_arrival": (base_time + timedelta(hours=6)).isoformat()
                    },
                    "is_connection": False,
                    "disruption_event": {
                        "disruption_type": "delay",
                        "disruption_category": "within_carrier_control",
                        "delay_duration_hours": 3.0
                    }
                },
                {
                    "leg_number": 2,
                    "flight_info": {
                        "flight_number": "AC701",
                        "departure_airport": "YVR",
                        "arrival_airport": "YYC",
                        "scheduled_departure": (base_time + timedelta(hours=4, minutes=30)).isoformat(),
                        "actual_departure": (base_time + timedelta(hours=7)).isoformat(),
                        "scheduled_arrival": (base_time + timedelta(hours=6)).isoformat(),
                        "actual_arrival": (base_time + timedelta(hours=8, minutes=30)).isoformat()
                    },
                    "is_connection": True
                }
            ]
        }

        response = client.post("/validate-journey", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["is_appr_applicable"] == False
        assert "non-Canadian airport" in data["appr_eligibility_reason"]
        assert data["journey_compensation_result"]["eligible_for_compensation"] == False


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_airport_code_single_flight(self):
        """Test single flight with invalid airport code."""
        base_time = datetime(2024, 3, 15, 8, 0, 0)
        request_data = {
            "flight_info": {
                "flight_number": "AC100",
                "departure_airport": "INVALID",  # Invalid - must be 3 letters
                "arrival_airport": "YVR",
                "scheduled_departure": base_time.isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat()
            },
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 350.0,
                "booking_class": "economy"
            },
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 4.0
            }
        }

        response = client.post("/validate-appr", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_journey_with_mismatched_connections(self):
        """Test journey where leg connections don't match."""
        base_time = datetime(2024, 6, 15, 8, 0, 0)
        request_data = {
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 500.0,
                "booking_class": "economy"
            },
            "flight_legs": [
                {
                    "leg_number": 1,
                    "flight_info": {
                        "flight_number": "AC100",
                        "departure_airport": "YYZ",
                        "arrival_airport": "YVR",  # Arrives at YVR
                        "scheduled_departure": base_time.isoformat(),
                        "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat()
                    },
                    "is_connection": False
                },
                {
                    "leg_number": 2,
                    "flight_info": {
                        "flight_number": "AC200",
                        "departure_airport": "YYC",  # Departs from YYC - MISMATCH!
                        "arrival_airport": "YUL",
                        "scheduled_departure": (base_time + timedelta(hours=6)).isoformat(),
                        "scheduled_arrival": (base_time + timedelta(hours=8)).isoformat()
                    },
                    "is_connection": True
                }
            ]
        }

        response = client.post("/validate-journey", json=request_data)
        assert response.status_code == 422  # Validation error
        assert "Connection mismatch" in response.json()["detail"][0]["msg"]

    def test_journey_with_single_leg(self):
        """Test journey with only 1 leg - should fail validation."""
        base_time = datetime(2024, 6, 15, 8, 0, 0)
        request_data = {
            "passenger_info": {
                "passenger_type": "regular",
                "ticket_price": 500.0,
                "booking_class": "economy"
            },
            "flight_legs": [
                {
                    "leg_number": 1,
                    "flight_info": {
                        "flight_number": "AC100",
                        "departure_airport": "YYZ",
                        "arrival_airport": "YVR",
                        "scheduled_departure": base_time.isoformat(),
                        "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat()
                    },
                    "is_connection": False
                }
            ]
        }

        response = client.post("/validate-journey", json=request_data)
        assert response.status_code == 422  # Validation error
        assert "at least 2 flight legs" in response.json()["detail"][0]["msg"]

    def test_check_airport_invalid_code_length(self):
        """Test airport check with invalid code length."""
        response = client.post("/check-airport?airport_code=TOOLONG")
        assert response.status_code == 400
        assert "must be exactly 3 characters" in response.json()["detail"]


class TestRegressionChecks:
    """Ensure existing behavior hasn't changed."""

    def test_compensation_tiers_unchanged(self):
        """Verify compensation tier amounts haven't changed."""
        base_time = datetime(2024, 3, 15, 8, 0, 0)

        # Test 3-6 hours
        response = client.post("/validate-appr", json={
            "flight_info": {
                "flight_number": "AC100",
                "departure_airport": "YYZ",
                "arrival_airport": "YVR",
                "scheduled_departure": base_time.isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat()
            },
            "passenger_info": {"passenger_type": "regular", "ticket_price": 350.0, "booking_class": "economy"},
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 4.0
            }
        })
        assert response.json()["compensation_result"]["compensation_amount"] == 400.0

        # Test 6-9 hours
        response = client.post("/validate-appr", json={
            "flight_info": {
                "flight_number": "AC100",
                "departure_airport": "YYZ",
                "arrival_airport": "YVR",
                "scheduled_departure": base_time.isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat()
            },
            "passenger_info": {"passenger_type": "regular", "ticket_price": 350.0, "booking_class": "economy"},
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 7.0
            }
        })
        assert response.json()["compensation_result"]["compensation_amount"] == 700.0

        # Test 9+ hours
        response = client.post("/validate-appr", json={
            "flight_info": {
                "flight_number": "AC100",
                "departure_airport": "YYZ",
                "arrival_airport": "YVR",
                "scheduled_departure": base_time.isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat()
            },
            "passenger_info": {"passenger_type": "regular", "ticket_price": 350.0, "booking_class": "economy"},
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 10.0
            }
        })
        assert response.json()["compensation_result"]["compensation_amount"] == 1000.0

    def test_care_obligation_thresholds_unchanged(self):
        """Verify care obligation thresholds are still correct."""
        base_time = datetime(2024, 3, 15, 8, 0, 0)

        # 2 hour delay - should have communication only
        response = client.post("/validate-appr", json={
            "flight_info": {
                "flight_number": "AC100",
                "departure_airport": "YYZ",
                "arrival_airport": "YVR",
                "scheduled_departure": base_time.isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat()
            },
            "passenger_info": {"passenger_type": "regular", "ticket_price": 350.0, "booking_class": "economy"},
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 2.0
            }
        })
        care_obs = response.json()["compensation_result"]["care_obligations"]
        assert len(care_obs) >= 1
        assert any("communication" in c.lower() for c in care_obs)

        # 4 hour delay - should have communication + food
        response = client.post("/validate-appr", json={
            "flight_info": {
                "flight_number": "AC100",
                "departure_airport": "YYZ",
                "arrival_airport": "YVR",
                "scheduled_departure": base_time.isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat()
            },
            "passenger_info": {"passenger_type": "regular", "ticket_price": 350.0, "booking_class": "economy"},
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 4.0
            }
        })
        care_obs = response.json()["compensation_result"]["care_obligations"]
        assert len(care_obs) >= 2
        assert any("food" in c.lower() for c in care_obs)

        # 9 hour delay - should have communication + food + accommodation
        response = client.post("/validate-appr", json={
            "flight_info": {
                "flight_number": "AC100",
                "departure_airport": "YYZ",
                "arrival_airport": "YVR",
                "scheduled_departure": base_time.isoformat(),
                "scheduled_arrival": (base_time + timedelta(hours=5)).isoformat()
            },
            "passenger_info": {"passenger_type": "regular", "ticket_price": 350.0, "booking_class": "economy"},
            "disruption_event": {
                "disruption_type": "delay",
                "disruption_category": "within_carrier_control",
                "delay_duration_hours": 9.0
            }
        })
        care_obs = response.json()["compensation_result"]["care_obligations"]
        assert len(care_obs) >= 4
        assert any("accommodation" in c.lower() for c in care_obs)


if __name__ == "__main__":
    print("="*80)
    print("RUNNING END-TO-END TEST SUITE")
    print("="*80)
    pytest.main([__file__, "-v", "--tb=short"])
