import streamlit as st

def validate_metadata(metadata):
    """
    Validate metadata fields and display warnings for missing ones.
    """
    required_fields = [
        "recording_id", "buoy_id", "channel", "sample_rate_hz",
        "bit_depth", "start_time_utc", "sensor_type"
    ]
    missing = []
    for field in required_fields:
        if field not in metadata:
            missing.append(field)
        else:
            st.write(f"{field}: {metadata[field]}")
    if missing:
        st.warning(f"Missing fields: {', '.join(missing)}")
    else:
        st.success("All required metadata fields present.")