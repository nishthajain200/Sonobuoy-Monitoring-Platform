"""
P-8I Sonobuoy Acoustic Analysis Workbench — Full Demo UI
Tabs: Dashboard | Data Ingestion | Waveform | FFT | LOFARgram |
      Harmonics & Discretes | Feature Extraction | Event Detection |
      LOFAR DB Correlation | Bearing View | Multi-Buoy Analysis | Export & Report
"""

import os
import json
import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy.signal import spectrogram as _spectrogram, find_peaks
from scipy.fft import fft as _fft, fftfreq as _fftfreq
import streamlit as st

from src.audio_reader import read_wav_file
from src.metadata_validator import validate_metadata
from src.waveform import generate_waveform
from src.fft_analyzer import generate_fft
from src.lofargram import generate_lofargram
from src.feature_extractor import extract_features
from src.event_detector import detect_events
from src.bearing_view import generate_bearing_view
from src.export_utils import export_csv, export_png_bytes, generate_html_report
from src.lofar_db import init_db, get_all_vessels, get_vessel_lines, add_vessel, CLASS_COLOURS
from src.lofar_correlator import correlate_frequencies
from src.harmonics_detector import detect_narrowband_discretes, detect_harmonics
from src.multi_buoy import analyze_multi_buoy

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="P-8I Sonobuoy Acoustic Analysis Workbench",
    page_icon="🔊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .hero-banner {
    background: linear-gradient(135deg,#071d36 0%,#0d3261 50%,#0a2040 100%);
    border-radius:12px; padding:22px 28px; margin-bottom:18px; color:#fff;
  }
  .hero-banner h2 { margin:0; font-size:1.5rem; letter-spacing:.5px; }
  .hero-banner p  { margin:4px 0 0; font-size:.85rem; opacity:.8; }
  .match-card-hi { border:2px solid #28a745; border-radius:8px; padding:12px; background:#f2fff5; margin:6px 0; }
  .match-card-md { border:2px solid #ffc107; border-radius:8px; padding:12px; background:#fffef0; margin:6px 0; }
  .match-card-lo { border:2px solid #dc3545; border-radius:8px; padding:12px; background:#fff5f5; margin:6px 0; }
  .step-row { display:flex; gap:8px; flex-wrap:wrap; margin:10px 0; }
  .step-box {
    background:#e8f0fe; border-radius:8px; padding:10px 14px;
    flex:1; min-width:110px; text-align:center; font-size:.8rem;
  }
  .step-num { font-size:1.3rem; font-weight:700; color:#1a5276; }
  [data-testid="stSidebar"] { background:#071d36 !important; }
  [data-testid="stSidebar"] * { color:#dce9f7 !important; }
  [data-testid="stSidebar"] .stButton button {
    background:#1a5276; color:#fff !important; border:none;
    border-radius:6px; width:100%;
  }
  [data-testid="stSidebar"] .stButton button:hover { background:#2471a3; }
</style>
""", unsafe_allow_html=True)

# ── Initialise LOFAR DB ────────────────────────────────────────────────────────
init_db()

# ── Session state defaults ─────────────────────────────────────────────────────
_DEFAULTS = dict(
    data=None, sample_rate=None, channels=None, metadata=None,
    waveform_stats=None, fft_stats=None, features_df=None,
    events_df=None, bearing_df=None,
    detected_peaks=None, harmonic_series=None,
    corr_results=None, multi_buoy_results=None,
)
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Plotly helper functions ────────────────────────────────────────────────────

def _mono(data):
    if data.ndim > 1:
        return np.mean(data, axis=1).astype(float)
    return data.astype(float)


def plotly_waveform(data, sample_rate):
    mono = _mono(data)
    max_pts = 60_000
    step = max(1, len(mono) // max_pts)
    t = np.arange(0, len(mono), step) / sample_rate
    y = mono[::step]
    fig = go.Figure(go.Scatter(
        x=t, y=y, mode='lines',
        line=dict(color='#41b3ff', width=0.8), name='Signal'
    ))
    fig.update_layout(
        title='Time-Domain Waveform',
        xaxis_title='Time (s)', yaxis_title='Amplitude',
        height=320, template='plotly_dark',
        margin=dict(l=55, r=20, t=40, b=40),
    )
    return fig


def plotly_fft(data, sample_rate, max_freq=4000, num_peaks=20):
    mono = _mono(data)
    N = len(mono)
    yf = _fft(mono)
    xf = _fftfreq(N, 1.0 / sample_rate)[:N // 2]
    mag = 2.0 / N * np.abs(yf[:N // 2])
    mag_db = 20.0 * np.log10(mag + 1e-12)

    mask = xf <= max_freq
    xf_l, mag_l, mag_db_l = xf[mask], mag[mask], mag_db[mask]

    peaks, _ = find_peaks(mag_db_l, distance=max(1, int(len(xf_l) / 400)), prominence=6.0)
    peak_freqs, peak_dbs = np.array([]), np.array([])
    if len(peaks) > 0:
        top = peaks[np.argsort(mag_l[peaks])[-num_peaks:]]
        peak_freqs = xf_l[top]
        peak_dbs   = mag_db_l[top]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xf_l, y=mag_db_l, mode='lines',
        line=dict(color='#00d4ff', width=1), name='Spectrum'
    ))
    if len(peak_freqs) > 0:
        fig.add_trace(go.Scatter(
            x=peak_freqs, y=peak_dbs + 2,
            mode='markers+text',
            marker=dict(color='#ff6b35', size=9, symbol='triangle-up'),
            text=[f"<b>{f:.1f}</b>" for f in peak_freqs],
            textposition='top center', textfont=dict(size=9, color='#ff6b35'),
            name='Peaks (Hz)',
        ))
    fig.update_layout(
        title='FFT Spectrum — Frequency Analysis',
        xaxis_title='Frequency (Hz)', yaxis_title='Magnitude (dB)',
        height=420, template='plotly_dark',
        margin=dict(l=55, r=20, t=40, b=40),
    )
    return fig, list(peak_freqs)


def plotly_lofargram(data, sample_rate, max_freq, window_size, overlap):
    mono = _mono(data)
    overlap = min(overlap, window_size - 1)
    f, t, Sxx = _spectrogram(mono, fs=sample_rate, nperseg=window_size, noverlap=overlap)
    Sxx_db = 10.0 * np.log10(Sxx + 1e-10)
    idx = f <= max_freq
    fig = go.Figure(go.Heatmap(
        z=Sxx_db[idx], x=t, y=f[idx],
        colorscale='Inferno', colorbar=dict(title='dB', len=0.85),
        zsmooth='best',
    ))
    fig.update_layout(
        title='LOFARgram — Waterfall Time-Frequency Display',
        xaxis_title='Time (s)', yaxis_title='Frequency (Hz)',
        height=500, template='plotly_dark',
        margin=dict(l=60, r=60, t=45, b=45),
    )
    return fig


def plotly_harmonics_spectrum(xf, mag_db, peaks_df, harmonic_series):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xf, y=mag_db, mode='lines',
        line=dict(color='#00d4ff', width=0.8), name='Spectrum', opacity=0.85
    ))
    if peaks_df is not None and not peaks_df.empty:
        fig.add_trace(go.Scatter(
            x=peaks_df['frequency_hz'], y=peaks_df['magnitude_db'] + 1.5,
            mode='markers', marker=dict(color='#ff6b35', size=8, symbol='triangle-up'),
            name='Detected Lines',
        ))
    colours = ['#f1c40f', '#2ecc71', '#e74c3c', '#9b59b6', '#1abc9c']
    for i, series in enumerate(harmonic_series or []):
        col = colours[i % len(colours)]
        for fhz in series['harmonic_frequencies_hz']:
            fig.add_vline(x=fhz, line_width=1.5, line_dash='dash', line_color=col, opacity=0.8)
        fig.add_trace(go.Scatter(
            x=[series['harmonic_frequencies_hz'][0]],
            y=[mag_db.max() * 0.95],
            mode='markers+text',
            marker=dict(color=col, size=12, symbol='diamond'),
            text=[f"f\u2080={series['fundamental_hz']} Hz"],
            textposition='top right', textfont=dict(color=col, size=9),
            name=f"Series {i+1} (f\u2080={series['fundamental_hz']} Hz)",
            showlegend=True,
        ))
    fig.update_layout(
        title='Spectrum with Detected Narrowband Lines & Harmonic Series',
        xaxis_title='Frequency (Hz)', yaxis_title='Magnitude (dB)',
        height=450, template='plotly_dark',
        margin=dict(l=55, r=20, t=45, b=40),
    )
    return fig


def plotly_event_timeline(events_df, data, sample_rate):
    mono = _mono(data)
    step = max(1, len(mono) // 40_000)
    t = np.arange(0, len(mono), step) / sample_rate
    y = mono[::step]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.4], vertical_spacing=0.05)
    fig.add_trace(go.Scatter(x=t, y=y, mode='lines',
                             line=dict(color='#41b3ff', width=0.7), name='Waveform'), row=1, col=1)

    if events_df is not None and not events_df.empty:
        for _, ev in events_df.iterrows():
            fig.add_vrect(
                x0=ev['start_time_sec'], x1=ev['end_time_sec'],
                fillcolor='rgba(255,107,53,0.25)', line_width=1, line_color='#ff6b35',
                row=1, col=1,
            )
        fig.add_trace(go.Scatter(
            x=events_df['start_time_sec'],
            y=events_df['confidence'],
            mode='markers+lines',
            marker=dict(color='#ff6b35', size=8), line=dict(color='#ff6b35'),
            name='Event Confidence',
        ), row=2, col=1)

    fig.update_layout(
        title='Event Detection Timeline', height=420, template='plotly_dark',
        margin=dict(l=55, r=20, t=45, b=40),
    )
    fig.update_xaxes(title_text='Time (s)', row=2, col=1)
    fig.update_yaxes(title_text='Amplitude', row=1, col=1)
    fig.update_yaxes(title_text='Confidence', row=2, col=1)
    return fig


def plotly_bearing(df):
    fig = go.Figure()
    if df is None or df.empty:
        return fig
    fig.add_trace(go.Scatterpolar(
        r=df['mid_time_sec'], theta=df['bearing_absolute_deg'],
        mode='markers',
        marker=dict(
            color=df['confidence'], colorscale='Plasma',
            size=9, cmin=0, cmax=1,
            colorbar=dict(title='Confidence', len=0.75),
        ),
        name='Bearing Estimates',
    ))
    fig.update_layout(
        polar=dict(angularaxis=dict(direction='clockwise', rotation=90)),
        title='Polar Bearing Display — North Up, Clockwise',
        height=500, template='plotly_dark',
    )
    return fig


def plotly_corr_matrix(matrix, labels):
    fig = go.Figure(go.Heatmap(
        z=matrix, x=labels, y=labels,
        colorscale='Blues', zmin=0, zmax=1,
        colorbar=dict(title='Corr'),
        text=np.round(matrix, 3),
        texttemplate='%{text}',
    ))
    fig.update_layout(
        title='Cross-Correlation Matrix', height=350,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:8px 0 4px'>
      <span style='font-size:2rem'>🔊</span>
      <div style='font-size:1rem;font-weight:700;letter-spacing:.5px;margin-top:4px'>
        P-8I SONOBUOY<br>ANALYSIS WORKBENCH
      </div>
      <div style='font-size:.72rem;opacity:.6;margin-top:2px'>DISC14 NAVY DEMO v2.0</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("**System Status**")
    data_ok  = st.session_state.data is not None
    meta_ok  = st.session_state.metadata is not None
    feat_ok  = st.session_state.features_df is not None
    evt_ok   = st.session_state.events_df is not None
    corr_ok  = st.session_state.corr_results is not None
    pks_ok   = bool(st.session_state.detected_peaks)

    for label, flag in [
        ("WAV File Loaded",    data_ok),
        ("Metadata Loaded",    meta_ok),
        ("Peaks Detected",     pks_ok),
        ("Features Extracted", feat_ok),
        ("Events Detected",    evt_ok),
        ("LOFAR Correlated",   corr_ok),
    ]:
        icon = "🟢" if flag else "⚪"
        st.markdown(f"{icon} {label}")

    st.markdown("---")
    st.markdown("**Quick Actions**")

    if st.button("⚙️  Generate Sample Data", use_container_width=True):
        try:
            from src.sample_generator import generate_sample_data
            generate_sample_data()
            st.success("Sample data written to `sample_data/`  \nUpload `vessel_merchant_mono.wav`")
        except Exception as exc:
            st.error(f"Error: {exc}")

    if st.button("🗑️  Clear Session", use_container_width=True):
        for k in _DEFAULTS:
            st.session_state[k] = None
        st.rerun()

    st.markdown("---")
    st.caption(
        "⚠️ POC — recorded acoustic analysis only.  \n"
        "Not for real-time sonobuoy operation, tactical tracking, or target classification."
    )

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
(tab_dash, tab_ingest, tab_wave, tab_fft,
 tab_lofar, tab_harm, tab_feat, tab_evt,
 tab_corr, tab_bearing, tab_multi, tab_export) = st.tabs([
    "🏠 Dashboard",
    "📂 Data Ingestion",
    "📈 Waveform",
    "📊 FFT Spectrum",
    "🌊 LOFARgram",
    "🎵 Harmonics & Discretes",
    "🔬 Feature Extraction",
    "⚡ Event Detection",
    "🗄️ LOFAR Correlation",
    "🧭 Bearing View",
    "🚢 Multi-Buoy Analysis",
    "📋 Export & Report",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
with tab_dash:
    st.markdown("""
    <div class='hero-banner'>
      <h2>🔊  P-8I Sonobuoy Acoustic Data Analysis Workbench</h2>
      <p>Automated DSP pipeline for recorded sonobuoy data —
         ingestion · waterfall · harmonics · LOFAR correlation · bearing · multi-buoy</p>
    </div>
    """, unsafe_allow_html=True)

    sr   = st.session_state.sample_rate
    data = st.session_state.data
    dur  = round(data.shape[0] / sr, 1) if data is not None else "—"
    n_ev = len(st.session_state.events_df) if evt_ok else "—"
    n_cr = len(st.session_state.corr_results) if corr_ok else "—"

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Sample Rate",  f"{sr} Hz" if sr else "—")
    c2.metric("Duration",     f"{dur} s" if data is not None else "—")
    c3.metric("Channels",     st.session_state.channels or "—")
    c4.metric("Events Found", n_ev)
    c5.metric("DB Matches",   n_cr)

    st.markdown("---")
    st.subheader("Analysis Workflow")
    st.markdown("""
    <div class='step-row'>
      <div class='step-box'><div class='step-num'>1</div>Data Ingestion<br><small>Upload WAV + metadata</small></div>
      <div class='step-box'><div class='step-num'>2</div>Waveform<br><small>Time-domain view</small></div>
      <div class='step-box'><div class='step-num'>3</div>FFT / LOFARgram<br><small>Frequency & waterfall</small></div>
      <div class='step-box'><div class='step-num'>4</div>Harmonics<br><small>Shaft · blade · machinery</small></div>
      <div class='step-box'><div class='step-num'>5</div>LOFAR Correlation<br><small>Match vs DB</small></div>
      <div class='step-box'><div class='step-num'>6</div>Bearing View<br><small>Direction of arrival</small></div>
      <div class='step-box'><div class='step-num'>7</div>Multi-Buoy<br><small>TDOA · triangulation</small></div>
      <div class='step-box'><div class='step-num'>8</div>Export<br><small>CSV · PNG · HTML</small></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("LOFAR Signature Database")
        vessels = get_all_vessels()
        for _, row in vessels.iterrows():
            col_hex = CLASS_COLOURS.get(row['vessel_class'], '#999')
            st.markdown(
                f"<span style='color:{col_hex};font-weight:700'>{row['vessel_class'][:3].upper()}</span>"
                f"&nbsp; {row['vessel_name']}&nbsp;&nbsp;"
                f"<small style='color:#888'>shaft={row['shaft_rate_hz']} Hz &nbsp;|&nbsp; blades={row['blade_count']}</small>",
                unsafe_allow_html=True
            )
    with col_r:
        st.subheader("Getting Started")
        st.markdown("""
1. **Sidebar → Generate Sample Data** — creates demo WAV files in `sample_data/`
2. Go to **📂 Data Ingestion** and upload `vessel_merchant_mono.wav`
3. Explore **Waveform → FFT → LOFARgram** tabs
4. Run **🎵 Harmonics & Discretes** to auto-detect frequency lines
5. Run **🗄️ LOFAR Correlation** to identify the vessel type
6. Upload the stereo file to try **🧭 Bearing View**
7. Upload multiple files in **🚢 Multi-Buoy Analysis**
""")

    if data is not None:
        st.success(
            f"✅ WAV file loaded — {data.shape[0]:,} samples · {dur} s "
            f"· {st.session_state.channels} ch · {sr} Hz"
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — DATA INGESTION
# ─────────────────────────────────────────────────────────────────────────────
with tab_ingest:
    st.header("📂 Data Ingestion")
    st.caption("Upload a recorded sonobuoy WAV file and optional metadata JSON.")

    col_wav, col_meta = st.columns(2)
    with col_wav:
        wav_file = st.file_uploader("Upload WAV file", type=["wav"], key="wav_uploader")
        if wav_file:
            try:
                data, sr, ch = read_wav_file(wav_file)
                st.session_state.data        = data
                st.session_state.sample_rate = sr
                st.session_state.channels    = ch
                # Reset downstream results on new file
                for k in ["features_df","events_df","bearing_df","detected_peaks",
                          "harmonic_series","corr_results","waveform_stats","fft_stats"]:
                    st.session_state[k] = None
                st.success("WAV loaded successfully.")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Sample Rate",   f"{sr} Hz")
                c2.metric("Channels",      ch)
                c3.metric("Duration",      f"{data.shape[0]/sr:.2f} s")
                c4.metric("Total Samples", f"{data.shape[0]:,}")
            except Exception as exc:
                st.error(f"Error loading WAV: {exc}")

    with col_meta:
        meta_file = st.file_uploader("Upload metadata.json (optional)", type=["json"], key="meta_uploader")
        if meta_file:
            try:
                metadata = json.load(meta_file)
                st.session_state.metadata = metadata
                st.success("Metadata loaded.")
                with st.expander("Metadata fields", expanded=True):
                    validate_metadata(metadata)
            except Exception as exc:
                st.error(f"Error loading metadata: {exc}")

    if st.session_state.data is not None:
        st.markdown("---")
        st.subheader("Signal Preview")
        try:
            st.plotly_chart(
                plotly_waveform(st.session_state.data, st.session_state.sample_rate),
                use_container_width=True
            )
        except Exception as exc:
            st.error(f"Preview error: {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — WAVEFORM
# ─────────────────────────────────────────────────────────────────────────────
with tab_wave:
    st.header("📈 Signal Waveform")
    if st.session_state.data is None:
        st.info("Upload a WAV file in the **📂 Data Ingestion** tab.")
    else:
        try:
            data = st.session_state.data
            sr   = st.session_state.sample_rate
            ch   = st.session_state.channels

            channel_options = ["All (mono mix)"] + [f"Channel {i+1}" for i in range(ch)]
            sel = st.selectbox("Channel", channel_options)

            if sel == "All (mono mix)" or ch == 1:
                display_data = data
            else:
                ch_idx = int(sel.split()[1]) - 1
                display_data = data[:, ch_idx]

            st.plotly_chart(plotly_waveform(display_data, sr), use_container_width=True)

            fig_mpl, stats = generate_waveform(data, sr)
            st.session_state.waveform_stats = stats

            st.subheader("Signal Statistics")
            stat_cols = st.columns(len(stats))
            for col, (k, v) in zip(stat_cols, stats.items()):
                col.metric(k.replace("_", " ").title(), v)

        except Exception as exc:
            st.error(f"Waveform error: {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — FFT SPECTRUM
# ─────────────────────────────────────────────────────────────────────────────
with tab_fft:
    st.header("📊 FFT Spectrum")
    if st.session_state.data is None:
        st.info("Upload a WAV file in the **📂 Data Ingestion** tab.")
    else:
        nyq = st.session_state.sample_rate // 2
        c1, c2 = st.columns(2)
        max_freq  = c1.slider("Max display frequency (Hz)", 50, nyq, min(2000, nyq), step=50)
        num_peaks = c2.slider("Peaks to annotate", 5, 40, 20)

        try:
            fig, peak_freqs = plotly_fft(
                st.session_state.data, st.session_state.sample_rate, max_freq, num_peaks
            )
            st.session_state.detected_peaks = sorted(peak_freqs)

            st.plotly_chart(fig, use_container_width=True)

            if peak_freqs:
                st.subheader(f"Top {len(peak_freqs)} Detected Peaks")
                peak_df = pd.DataFrame({"frequency_hz": sorted(peak_freqs, reverse=True)})
                st.dataframe(peak_df, use_container_width=True, height=200)
                st.caption(
                    f"💡 {len(peak_freqs)} peaks saved — "
                    "use **🗄️ LOFAR Correlation** to match against the database."
                )

            fig_mpl, fft_stats = generate_fft(st.session_state.data, st.session_state.sample_rate)
            st.session_state.fft_stats = fft_stats

        except Exception as exc:
            st.error(f"FFT error: {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — LOFARGRAM
# ─────────────────────────────────────────────────────────────────────────────
with tab_lofar:
    st.header("🌊 LOFARgram — Waterfall Display")
    if st.session_state.data is None:
        st.info("Upload a WAV file in the **📂 Data Ingestion** tab.")
    else:
        nyq = st.session_state.sample_rate // 2
        c1, c2, c3 = st.columns(3)
        max_freq    = c1.slider("Max Frequency (Hz)", 50, nyq, min(2000, nyq), step=50, key="lo_mf")
        window_size = c2.slider("Window Size (samples)", 128, 4096, 512, step=128, key="lo_ws")
        overlap_pct = c3.slider("Overlap (%)", 25, 95, 75, step=5, key="lo_ov")
        overlap     = int(window_size * overlap_pct / 100)

        try:
            fig = plotly_lofargram(
                st.session_state.data, st.session_state.sample_rate,
                max_freq, window_size, overlap
            )
            st.plotly_chart(fig, use_container_width=True)

            generate_lofargram(
                st.session_state.data, st.session_state.sample_rate,
                max_freq, window_size, overlap
            )
            st.caption(
                "💡 Vertical bright lines = narrowband tones (vessel machinery).  "
                "Horizontal bands = broadband events. Use scroll/pinch to zoom."
            )
        except Exception as exc:
            st.error(f"LOFARgram error: {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — HARMONICS & DISCRETES
# ─────────────────────────────────────────────────────────────────────────────
with tab_harm:
    st.header("🎵 Narrowband Discretes & Harmonic Series Detection")
    if st.session_state.data is None:
        st.info("Upload a WAV file in the **📂 Data Ingestion** tab.")
    else:
        nyq = st.session_state.sample_rate // 2
        c1, c2, c3 = st.columns(3)
        max_freq_h = c1.slider("Max Frequency (Hz)", 50, nyq, min(1000, nyq), step=50, key="hm_mf")
        thresh_db  = c2.slider("Threshold (dB above mean)", 5, 30, 12, key="hm_th")
        min_harm   = c3.slider("Min harmonics in series", 2, 6, 3, key="hm_mh")

        if st.button("🔍  Run Harmonics Detection", type="primary"):
            try:
                peaks_df, xf_l, mag_db_l = detect_narrowband_discretes(
                    st.session_state.data, st.session_state.sample_rate,
                    max_freq=max_freq_h, threshold_db_above_mean=thresh_db
                )
                h_series = []
                if not peaks_df.empty:
                    h_series = detect_harmonics(
                        peaks_df['frequency_hz'].tolist(), min_harmonics=min_harm
                    )
                st.session_state.harmonic_series = h_series
                if not peaks_df.empty:
                    st.session_state.detected_peaks = sorted(peaks_df['frequency_hz'].tolist())

                fig = plotly_harmonics_spectrum(xf_l, mag_db_l, peaks_df, h_series)
                st.plotly_chart(fig, use_container_width=True)

                col_left, col_right = st.columns(2)
                with col_left:
                    st.subheader(f"Detected Lines ({len(peaks_df)})")
                    if not peaks_df.empty:
                        st.dataframe(peaks_df, use_container_width=True, height=280)
                    else:
                        st.warning("No lines found. Try lowering the dB threshold.")

                with col_right:
                    st.subheader(f"Harmonic Series ({len(h_series)})")
                    if h_series:
                        for i, s in enumerate(h_series):
                            freqs_str = " · ".join(f"{f} Hz" for f in s['harmonic_frequencies_hz'])
                            st.markdown(
                                f"**Series {i+1}** &nbsp; f\u2080 = `{s['fundamental_hz']} Hz`"
                                f" &nbsp; ({s['harmonics_count']} harmonics)"
                                f" &nbsp; *{s['inferred_type']}*  \n"
                                f"<small>{freqs_str}</small>",
                                unsafe_allow_html=True
                            )
                    else:
                        st.info("No harmonic series found with current settings.")

                st.caption(
                    f"✅ {len(peaks_df)} lines, {len(h_series)} series detected. "
                    "Peaks saved — proceed to **🗄️ LOFAR Correlation**."
                )
            except Exception as exc:
                st.error(f"Detection error: {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — FEATURE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────
with tab_feat:
    st.header("🔬 Feature Extraction")
    if st.session_state.data is None:
        st.info("Upload a WAV file in the **📂 Data Ingestion** tab.")
    else:
        c1, c2 = st.columns(2)
        win_sec   = c1.slider("Window size (s)", 0.5, 5.0, 1.0, step=0.5)
        overlap_p = c2.slider("Overlap (%)",     0, 90, 50, step=10)

        if st.button("▶  Extract Features", type="primary"):
            try:
                df = extract_features(
                    st.session_state.data, st.session_state.sample_rate,
                    win_sec, overlap_p
                )
                st.session_state.features_df = df
            except Exception as exc:
                st.error(f"Feature extraction error: {exc}")

        if st.session_state.features_df is not None:
            df = st.session_state.features_df
            st.metric("Windows analysed", len(df))
            st.dataframe(df, use_container_width=True, height=300)

            feat_col = st.selectbox("Plot feature over time",
                                    ['rms', 'peak_amplitude', 'dominant_frequency_hz',
                                     'band_energy_20_200_hz', 'band_energy_200_1000_hz'])
            fig = px.line(df, x='start_time_sec', y=feat_col,
                          title=f'{feat_col} over time',
                          template='plotly_dark', height=300)
            st.plotly_chart(fig, use_container_width=True)

            csv_bytes = export_csv(df, "features.csv")
            st.download_button("⬇ Download Features CSV", csv_bytes, "features.csv", "text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 8 — EVENT DETECTION
# ─────────────────────────────────────────────────────────────────────────────
with tab_evt:
    st.header("⚡ Acoustic Event Detection")
    if st.session_state.data is None:
        st.info("Upload a WAV file in the **📂 Data Ingestion** tab.")
    else:
        c1, c2 = st.columns([2, 1])
        threshold = c1.slider("RMS threshold (0 = auto: mean + 1σ)", 0.0, 1.0, 0.0, step=0.005)
        c2.markdown("&nbsp;")
        run_evt = c2.button("▶  Detect Events", type="primary")

        if run_evt:
            try:
                df = detect_events(
                    st.session_state.data, st.session_state.sample_rate,
                    threshold if threshold > 0 else None
                )
                st.session_state.events_df = df
            except Exception as exc:
                st.error(f"Event detection error: {exc}")

        if st.session_state.events_df is not None:
            df = st.session_state.events_df
            st.metric("Events Detected", len(df))
            try:
                fig = plotly_event_timeline(df, st.session_state.data, st.session_state.sample_rate)
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass
            st.dataframe(df, use_container_width=True, height=250)
            csv_bytes = export_csv(df, "events.csv")
            st.download_button("⬇ Download Events CSV", csv_bytes, "events.csv", "text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 9 — LOFAR DB CORRELATION
# ─────────────────────────────────────────────────────────────────────────────
with tab_corr:
    st.header("🗄️ LOFAR Signature Database Correlation")

    col_db, col_corr = st.columns([1, 2])

    with col_db:
        st.subheader("Signature Database")
        vessels = get_all_vessels()
        for _, row in vessels.iterrows():
            col_hex = CLASS_COLOURS.get(row['vessel_class'], '#aaa')
            with st.expander(f"**{row['vessel_name']}**"):
                st.markdown(
                    f"<span style='color:{col_hex}'>●</span> **Class:** {row['vessel_class']}  \n"
                    f"**Shaft Rate:** {row['shaft_rate_hz']} Hz  \n"
                    f"**Blades:** {row['blade_count']}  \n"
                    f"*{row['description']}*",
                    unsafe_allow_html=True
                )
                lines = get_vessel_lines(row['vessel_id'])
                st.dataframe(
                    lines[['freq_hz', 'line_type', 'harmonic', 'relative_amplitude']],
                    use_container_width=True, height=150
                )

        with st.expander("➕ Add New Vessel Signature"):
            with st.form("add_vessel_form"):
                vid    = st.text_input("Vessel ID (e.g. VES-010)")
                vname  = st.text_input("Vessel Name")
                vcls   = st.selectbox("Class", ["Merchant","Warship","Submarine","Patrol","Biological","Other"])
                vshaft = st.number_input("Shaft Rate (Hz)", 0.0, 100.0, 5.0, 0.5)
                vblade = st.number_input("Blade Count", 0, 20, 4)
                vdesc  = st.text_area("Description")
                vlines_raw = st.text_area(
                    "Frequency Lines (freq_hz,type,harmonic,amplitude — one per line)",
                    "5.0,shaft,1,0.8\n20.0,blade,1,1.0\n120.0,machinery,1,0.6"
                )
                if st.form_submit_button("Add Vessel"):
                    if vid and vname:
                        try:
                            lines_data = []
                            for ln in vlines_raw.strip().split('\n'):
                                parts = ln.strip().split(',')
                                if len(parts) >= 4:
                                    lines_data.append({
                                        'freq_hz': float(parts[0]),
                                        'line_type': parts[1].strip(),
                                        'harmonic': int(parts[2]),
                                        'relative_amplitude': float(parts[3]),
                                    })
                            add_vessel(vid, vname, vcls, vshaft, int(vblade), vdesc, lines_data)
                            st.success(f"Vessel {vname} added.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Error: {exc}")
                    else:
                        st.warning("Vessel ID and Name are required.")

    with col_corr:
        st.subheader("Run Correlation")

        peaks_src = st.radio(
            "Frequency peaks source",
            ["From FFT / Harmonics analysis", "Enter manually"],
            horizontal=True
        )

        if peaks_src == "Enter manually":
            manual_input = st.text_input(
                "Enter frequencies (Hz), comma-separated",
                placeholder="5.0, 10.0, 20.0, 40.0, 120.0, 240.0"
            )
            if manual_input.strip():
                try:
                    st.session_state.detected_peaks = [
                        float(x.strip()) for x in manual_input.split(',') if x.strip()
                    ]
                except ValueError:
                    st.error("Invalid input — enter comma-separated numbers.")

        curr_peaks = st.session_state.detected_peaks or []
        if curr_peaks:
            st.caption(
                f"Using {len(curr_peaks)} peaks: "
                f"{', '.join(f'{f:.1f}' for f in sorted(curr_peaks)[:15])}"
                f"{'...' if len(curr_peaks) > 15 else ''}"
            )
        else:
            st.info("No peaks available. Run **📊 FFT Spectrum** or **🎵 Harmonics** first, "
                    "or enter frequencies manually.")

        c_tol, c_min = st.columns(2)
        tolerance = c_tol.slider("Match tolerance (Hz)", 0.5, 10.0, 2.0, 0.5)
        min_ratio = c_min.slider("Min match ratio",      0.1, 0.8,  0.25, 0.05)

        if st.button("🔗  Correlate Against LOFAR DB", type="primary",
                     disabled=not bool(curr_peaks)):
            try:
                results = correlate_frequencies(
                    curr_peaks, tolerance_hz=tolerance, min_match_ratio=min_ratio
                )
                st.session_state.corr_results = results
            except Exception as exc:
                st.error(f"Correlation error: {exc}")

        if st.session_state.corr_results is not None:
            results = st.session_state.corr_results
            st.markdown("---")
            st.subheader(f"Correlation Results — {len(results)} candidate(s)")

            if results.empty:
                st.warning("No matches found. Try lowering tolerance or min match ratio.")
            else:
                for i, row in results.iterrows():
                    score    = row['confidence_score']
                    card_cls = ('match-card-hi' if score >= 0.6
                                else 'match-card-md' if score >= 0.35
                                else 'match-card-lo')
                    col_hex  = CLASS_COLOURS.get(row['vessel_class'], '#aaa')
                    mf_str   = " · ".join(f"{f} Hz" for f in row['matched_frequencies_hz'])
                    st.markdown(f"""
                    <div class='{card_cls}'>
                      <b style='font-size:1.05rem'>#{i+1} — {row['vessel_name']}</b>
                      &nbsp;<span style='color:{col_hex};font-weight:700'>[{row['vessel_class']}]</span><br>
                      <small>{row['description']}</small><br><br>
                      <b>Confidence:</b> {score*100:.1f}% &nbsp;|&nbsp;
                      <b>Lines matched:</b> {row['matched_lines']}/{row['db_lines']}
                      ({row['match_ratio']*100:.0f}%) &nbsp;|&nbsp;
                      <b>Shaft:</b> {row['shaft_rate_hz']} Hz &nbsp;|&nbsp;
                      <b>Blades:</b> {row['blade_count']}<br>
                      <b>Matched frequencies:</b> <code>{mf_str}</code>
                    </div>
                    """, unsafe_allow_html=True)

                st.progress(float(results.iloc[0]['confidence_score']))
                st.caption(
                    f"Top match: **{results.iloc[0]['vessel_name']}** — "
                    f"{results.iloc[0]['confidence_score']*100:.1f}% confidence"
                )

                fig = px.bar(
                    results, x='vessel_name', y='confidence_score',
                    color='vessel_class',
                    color_discrete_map=CLASS_COLOURS,
                    title='Correlation Confidence by Vessel',
                    labels={'confidence_score': 'Confidence', 'vessel_name': 'Vessel'},
                    template='plotly_dark', height=320,
                )
                fig.update_layout(margin=dict(l=10, r=10, t=40, b=80))
                st.plotly_chart(fig, use_container_width=True)

                safe = results.drop(columns=['matched_frequencies_hz'], errors='ignore')
                csv_bytes = export_csv(safe, "lofar_correlation.csv")
                st.download_button("⬇ Correlation CSV", csv_bytes, "lofar_correlation.csv", "text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 10 — BEARING VIEW
# ─────────────────────────────────────────────────────────────────────────────
with tab_bearing:
    st.header("🧭 Polar Bearing View")
    if st.session_state.data is None:
        st.info("Upload a WAV file in the **📂 Data Ingestion** tab.")
    elif (st.session_state.channels or 1) < 2:
        st.warning(
            "Bearing estimation requires stereo (≥ 2 channel) data.  \n"
            "Generate sample data and upload `vessel_merchant_stereo.wav`."
        )
    else:
        c1, c2, c3 = st.columns(3)
        sensor_spacing = c1.slider("Sensor Spacing (m)", 0.1, 2.0, 0.75, 0.05)
        sound_speed    = c2.slider("Sound Speed (m/s)",  1000, 2000, 1500, 10)
        array_heading  = c3.slider("Array Heading (°)",  0, 359, 0, 5)

        c4, c5 = st.columns(2)
        bearing_window = c4.slider("Window (s)",    0.1, 2.0, 0.5, 0.1)
        rms_threshold  = c5.slider("RMS Threshold", 0.0, 1.0, 0.02, 0.01)

        if st.button("🧭  Compute Bearing", type="primary"):
            try:
                fig_mpl, df = generate_bearing_view(
                    st.session_state.data, st.session_state.sample_rate,
                    sensor_spacing, sound_speed, array_heading,
                    bearing_window, rms_threshold
                )
                st.session_state.bearing_df = df
            except Exception as exc:
                st.error(f"Bearing error: {exc}")

        if st.session_state.bearing_df is not None:
            df = st.session_state.bearing_df
            if df.empty:
                st.warning("No estimates above threshold. Try lowering the RMS threshold.")
            else:
                col_plot, col_stats = st.columns([1, 1])
                with col_plot:
                    st.plotly_chart(plotly_bearing(df), use_container_width=True)
                with col_stats:
                    st.subheader("Bearing Summary")
                    st.metric("Mean Bearing", f"{df['bearing_absolute_deg'].mean():.1f}°")
                    st.metric("Std Dev",       f"{df['bearing_absolute_deg'].std():.1f}°")
                    st.metric("Estimates",     len(df))
                    st.dataframe(
                        df[['mid_time_sec', 'bearing_absolute_deg', 'confidence']],
                        use_container_width=True, height=280
                    )
                csv_bytes = export_csv(df, "bearing.csv")
                st.download_button("⬇ Bearing CSV", csv_bytes, "bearing.csv", "text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 11 — MULTI-BUOY ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
with tab_multi:
    st.header("🚢 Multi-Buoy Analysis")
    st.caption(
        "Upload recordings from 2–4 sonobuoys to compute TDOA, common frequencies, "
        "and cross-correlation.  "
        "Try `vessel_merchant_mono.wav` + `multi_vessel_scenario.wav`."
    )

    multi_files = st.file_uploader(
        "Upload 2–4 WAV files (one per buoy)",
        type=["wav"], accept_multiple_files=True, key="multi_wav"
    )

    if multi_files and len(multi_files) >= 2:
        labels_input = st.text_input(
            "Buoy labels (comma-separated)",
            value=", ".join(f"Buoy-{i+1}" for i in range(len(multi_files)))
        )
        labels = [l.strip() for l in labels_input.split(",")][:len(multi_files)]

        if st.button("🚢  Run Multi-Buoy Analysis", type="primary"):
            try:
                buoy_list = []
                for f in multi_files:
                    d, sr_, ch_ = read_wav_file(f)
                    buoy_list.append((d, sr_))
                results = analyze_multi_buoy(buoy_list, labels)
                st.session_state.multi_buoy_results = results
            except Exception as exc:
                st.error(f"Multi-buoy error: {exc}")
    elif multi_files:
        st.warning("Upload at least 2 WAV files for multi-buoy analysis.")

    if st.session_state.multi_buoy_results is not None:
        res = st.session_state.multi_buoy_results
        if "error" in res:
            st.error(res["error"])
        else:
            st.subheader("TDOA Results")
            st.dataframe(res['tdoa_df'], use_container_width=True)

            col_left, col_right = st.columns(2)
            with col_left:
                st.subheader("Cross-Correlation Matrix")
                st.plotly_chart(
                    plotly_corr_matrix(res['correlation_matrix'], res['labels']),
                    use_container_width=True
                )
            with col_right:
                st.subheader("Common Frequencies Across All Buoys")
                common = res['common_frequencies_hz']
                if common:
                    fig_cf = go.Figure(go.Bar(
                        x=common, y=[1.0] * len(common),
                        marker_color='#00d4ff',
                        hovertemplate='%{x:.1f} Hz<extra></extra>',
                    ))
                    fig_cf.update_layout(
                        title=f"{len(common)} common frequency lines",
                        xaxis_title='Frequency (Hz)',
                        yaxis=dict(showticklabels=False),
                        height=260, template='plotly_dark',
                        margin=dict(l=40, r=10, t=40, b=40),
                    )
                    st.plotly_chart(fig_cf, use_container_width=True)
                    st.caption("These frequencies appear in all buoys — likely same emitter.")
                else:
                    st.info("No common frequencies found across all buoys.")

            csv_bytes = export_csv(res['tdoa_df'], "tdoa_results.csv")
            st.download_button("⬇ TDOA CSV", csv_bytes, "tdoa_results.csv", "text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 12 — EXPORT & REPORT
# ─────────────────────────────────────────────────────────────────────────────
with tab_export:
    st.header("📋 Export & Report")
    if st.session_state.data is None:
        st.info("Upload a WAV file in the **📂 Data Ingestion** tab.")
    else:
        st.subheader("Plot Downloads (PNG)")
        ec1, ec2, ec3, ec4 = st.columns(4)
        for col, fname, label in [
            (ec1, "outputs/waveform.png",  "Waveform"),
            (ec2, "outputs/fft.png",       "FFT Spectrum"),
            (ec3, "outputs/lofargram.png", "LOFARgram"),
            (ec4, "outputs/bearing.png",   "Bearing View"),
        ]:
            b = export_png_bytes(fname)
            if b:
                col.download_button(f"⬇ {label}", b, os.path.basename(fname), "image/png")
            else:
                col.caption(f"{label} — visit its tab to generate.")

        st.subheader("Data Table Downloads (CSV)")
        dc1, dc2, dc3, dc4 = st.columns(4)
        for col, key, fname, label in [
            (dc1, "features_df",  "features.csv",         "Features"),
            (dc2, "events_df",    "events.csv",            "Events"),
            (dc3, "bearing_df",   "bearing.csv",           "Bearing"),
            (dc4, "corr_results", "lofar_correlation.csv", "LOFAR Corr"),
        ]:
            df_val = st.session_state.get(key)
            if df_val is not None and not (hasattr(df_val, 'empty') and df_val.empty):
                try:
                    safe = df_val.astype(str)
                    b = export_csv(safe, fname)
                    col.download_button(f"⬇ {label} CSV", b, fname, "text/csv")
                except Exception:
                    col.caption(f"{label} — export error.")
            else:
                col.caption(f"{label} — not yet generated.")

        st.subheader("HTML Summary Report")
        if st.button("📄  Generate HTML Report", type="primary"):
            try:
                report_bytes = generate_html_report(st.session_state)
                st.download_button(
                    "⬇ Download HTML Report", report_bytes,
                    "sonobuoy_analysis_report.html", "text/html"
                )
            except Exception as exc:
                st.error(f"Report error: {exc}")

        st.subheader("Output Files on Disk")
        if os.path.exists("outputs"):
            files = [f for f in os.listdir("outputs") if os.path.isfile(os.path.join("outputs", f))]
            st.code("outputs/ — " + (", ".join(files) if files else "empty"))
