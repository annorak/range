"""JSON Schema export is JSON-Schema-shaped and covers the model tree."""

from rangelab.spec import export_json_schema


def test_export_is_json_schema_shaped() -> None:
    schema = export_json_schema()
    assert schema["title"] == "Scenario"
    assert "apiVersion" in schema["properties"]
    # nested models land in $defs
    assert {"Host", "Subnet", "FileArtifact"} <= set(schema["$defs"])
