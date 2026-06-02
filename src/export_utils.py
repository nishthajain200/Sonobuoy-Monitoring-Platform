import pandas as pd
import io
import os


def export_csv(df, filename):
    """
    Export dataframe to CSV in outputs folder and return CSV bytes for download.
    """
    os.makedirs("outputs", exist_ok=True)
    path = os.path.join("outputs", filename)
    df.to_csv(path, index=False)
    return df.to_csv(index=False).encode("utf-8")


def export_png_bytes(path):
    """
    Read a saved PNG from disk and return bytes for download.
    Returns None if file does not exist.
    """
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None


def generate_html_report(session_state):
    """
    Generate an HTML summary report from session state data.
    """
    data = session_state.get("data")
    sample_rate = session_state.get("sample_rate", 0)
    channels = session_state.get("channels", 1)
    metadata = session_state.get("metadata")
    waveform_stats = session_state.get("waveform_stats", {})
    fft_stats = session_state.get("fft_stats", {})
    events_df = session_state.get("events_df")
    bearing_df = session_state.get("bearing_df")

    duration = round(data.shape[0] / sample_rate, 2) if data is not None else "N/A"
    n_events = len(events_df) if events_df is not None else "N/A"
    bearing_available = bearing_df is not None and not bearing_df.empty

    css = """
    <style>
      body { font-family: Arial, sans-serif; max-width: 900px; margin: auto; padding: 20px; }
      h1 { color: #1a3c5e; }
      h2 { color: #2e6da4; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
      table { border-collapse: collapse; width: 100%; margin-bottom: 16px; }
      th, td { border: 1px solid #ccc; padding: 6px 12px; text-align: left; }
      th { background: #e8f0f7; }
      .warn { color: #b36b00; }
    </style>
    """

    def kv_table(rows):
        return "<table>" + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows) + "</table>"

    html = f"<html><head><meta charset='utf-8'>{css}</head><body>"
    html += "<h1>Sonobuoy Acoustic Data Analysis Report</h1>"

    html += "<h2>File Summary</h2>"
    html += kv_table([
        ("Sample Rate", f"{sample_rate} Hz"),
        ("Channels", channels),
        ("Duration", f"{duration} s"),
        ("Total Samples", data.shape[0] if data is not None else "N/A"),
    ])

    if waveform_stats:
        html += "<h2>Signal Statistics</h2>"
        html += kv_table([(k, v) for k, v in waveform_stats.items()])

    if fft_stats:
        html += "<h2>FFT Analysis</h2>"
        html += kv_table([
            ("Dominant Frequency (Hz)", fft_stats.get("dominant_frequency_hz", "N/A")),
            ("Top 5 Frequencies (Hz)", ", ".join(str(f) for f in fft_stats.get("top_5_frequencies_hz", []))),
        ])

    if metadata:
        html += "<h2>Metadata</h2>"
        html += kv_table(metadata.items())

    html += "<h2>Event Detection</h2>"
    html += kv_table([("Detected Events", n_events)])

    html += "<h2>Bearing View</h2>"
    html += kv_table([("Available", "Yes" if bearing_available else "No (mono or no signal)")])

    html += "<p style='color:gray;font-size:0.85em'>This POC is for recorded acoustic signal analysis and DSP visualization only.</p>"
    html += "</body></html>"
    return html.encode("utf-8")