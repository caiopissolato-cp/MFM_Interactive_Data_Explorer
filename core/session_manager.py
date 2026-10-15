"""Session-state helpers.

Keep transient UI state here. Persistent project settings belong in project_service.py.
"""

def initialize_session(st):
    defaults = {
        "active_project_id": None,
        "custom_calcs": [],
        "value_filters": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, list) else value
