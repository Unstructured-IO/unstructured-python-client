from scripts.check_spec_drift import find_drift


def _spec(schemas: dict) -> dict:
    return {"components": {"schemas": schemas}}


def test_matching_spec_reports_no_drift():
    spec = _spec(
        {
            "JobStatus": {"type": "string", "enum": ["SCHEDULED", "REJECTED"]},
            "CreateWorkflow": {
                "properties": {
                    "name": {"type": "string"},
                    "schedule": {"anyOf": [{"type": "string", "enum": ["daily"]}, {"type": "null"}]},
                }
            },
        }
    )
    assert find_drift([spec]) == {}


def test_reports_missing_enum_values_and_properties():
    spec = _spec(
        {
            "JobStatus": {"type": "string", "enum": ["SCHEDULED", "PAUSED"]},
            "CreateWorkflow": {"properties": {"name": {}, "brand_new_field": {}}},
            "SomeSchemaTheSdkDoesNotModel": {"properties": {"x": {}}},
        }
    )
    assert find_drift([spec]) == {
        "CreateWorkflow": ["brand_new_field"],
        "JobStatus": ["PAUSED"],
    }


def test_reports_missing_values_of_an_inline_property_enum():
    spec = _spec(
        {
            "CreateWorkflow": {
                "properties": {
                    "schedule": {
                        "anyOf": [
                            {"type": "string", "enum": ["daily", "every 30 minutes"]},
                            {"type": "null"},
                        ]
                    }
                }
            }
        }
    )
    assert find_drift([spec]) == {"CreateWorkflow.schedule": ["every 30 minutes"]}
