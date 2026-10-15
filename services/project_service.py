"""Project persistence and client/project isolation.

Use a controlled base directory and validate project identifiers before file access.
Do not treat folder names as a security boundary for shared installations.
"""

def create_project_metadata(project_id: str, client_name: str, meter_model: str) -> dict:
    return {
        "project_id": project_id,
        "client_name": client_name,
        "meter_model": meter_model,
        "schema_version": 1,
    }
