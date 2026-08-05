import json
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent

st.set_page_config(page_title="Kybermart CV Demo", page_icon="📦", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 2.5rem; padding-bottom: 4rem; max-width: 1180px; }
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(1100px 500px at 12% -8%, #1a2f5c33, transparent 60%),
        radial-gradient(900px 500px at 100% 0%, #0d3a3a33, transparent 55%),
        #0a0e17;
}
footer, #MainMenu { display:none !important; }

/* ── type scale ─────────────────────────────────────────────────────── */
.eyebrow { font-size:0.72rem; font-weight:700; color:#5eead4; letter-spacing:0.16em; text-transform:uppercase; margin-bottom:0.7rem; }
.hero-title { font-size:2.9rem; font-weight:800; color:#f8fafc; line-height:1.08; margin-bottom:0.9rem; letter-spacing:-0.02em; }
.hero-sub { font-size:1.08rem; color:#94a3b8; margin-bottom:1.6rem; font-weight:400; line-height:1.55; max-width:46ch; }
.section-label { font-size:0.72rem; font-weight:700; color:#5eead4; letter-spacing:0.16em; text-transform:uppercase; margin-bottom:0.6rem; }
.section-title { font-size:1.8rem; font-weight:800; color:#f1f5f9; margin-bottom:2rem; letter-spacing:-0.01em; }

/* ── badges ──────────────────────────────────────────────────────────── */
.badge-row { display:flex; flex-wrap:wrap; gap:0.45rem; margin-bottom:0.5rem; }
.badge {
    display:inline-flex; align-items:center; background:linear-gradient(135deg,#134e4a55,#0f172a);
    color:#5eead4; border:1px solid #134e4a; border-radius:8px;
    padding:0.32rem 0.7rem; font-size:0.74rem; font-weight:600; letter-spacing:0.02em;
}

/* ── hero video frame ───────────────────────────────────────────────── */
.video-frame {
    border-radius:16px; padding:6px;
    background:linear-gradient(140deg,#2dd4bf55,#1e293b 45%,#0f172a);
    box-shadow:0 20px 60px -20px #000a, 0 0 0 1px #1e293b;
}
.video-frame video, .video-frame > div { border-radius:12px !important; overflow:hidden; }
[data-testid="stVideo"] { border-radius:12px; overflow:hidden; }

/* ── inline stat chips ──────────────────────────────────────────────── */
.chip-row { display:flex; gap:0.7rem; flex-wrap:wrap; margin-top:0.4rem; }
.chip { background:#0f172acc; border:1px solid #1e293b; border-radius:10px; padding:0.65rem 1rem; min-width:118px; }
.chip-num { font-size:1.35rem; font-weight:800; color:#5eead4; line-height:1.1; }
.chip-label { font-size:0.72rem; color:#64748b; margin-top:0.15rem; line-height:1.3; }

/* ── feature cards ──────────────────────────────────────────────────── */
.feature-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; }
.feature-card {
    position:relative; background:#0f172a; border:1px solid #1e293b; border-radius:14px;
    padding:1.3rem 1.2rem 1.4rem; overflow:hidden;
}
.feature-card::before {
    content:""; position:absolute; top:0; left:0; right:0; height:3px;
    background:linear-gradient(90deg,#2dd4bf,#3b82f6);
}
.feature-icon {
    width:38px; height:38px; border-radius:10px; background:#134e4a44; border:1px solid #134e4a;
    display:flex; align-items:center; justify-content:center; font-size:1.1rem; margin-bottom:0.8rem;
}
.feature-title { font-weight:700; color:#e2e8f0; margin-bottom:0.4rem; font-size:0.98rem; }
.feature-desc { font-size:0.83rem; color:#64748b; line-height:1.55; }

/* ── pipeline stepper ───────────────────────────────────────────────── */
.stepper { display:flex; align-items:flex-start; gap:0; margin-top:0.5rem; }
.step { flex:1; position:relative; padding-right:1rem; }
.step-line { position:absolute; top:15px; left:calc(50% + 16px); right:calc(-50% + 16px); height:2px; background:#1e293b; }
.step:last-child .step-line { display:none; }
.step-dot {
    width:30px; height:30px; border-radius:50%; background:#0f172a; border:2px solid #2dd4bf;
    color:#5eead4; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.85rem;
    margin-bottom:0.7rem; position:relative; z-index:1;
}
.step-title { font-weight:700; color:#e2e8f0; font-size:0.88rem; margin-bottom:0.3rem; }
.step-desc { font-size:0.78rem; color:#64748b; line-height:1.5; }

/* ── caveat ──────────────────────────────────────────────────────────── */
.note-card {
    display:flex; gap:0.9rem; background:#12141c; border:1px solid #292b36; border-left:3px solid #d97706;
    border-radius:10px; padding:1.1rem 1.3rem; color:#cbd5e1; font-size:0.85rem; line-height:1.6;
}
.note-card b { color:#f1f5f9; }
.note-icon { font-size:1.1rem; flex-shrink:0; }

.divider { height:1px; background:linear-gradient(90deg,#1e293b,transparent); margin:3rem 0 2.2rem; }

@media (max-width: 900px) {
  .feature-grid { grid-template-columns:repeat(2,1fr); }
  .stepper { flex-direction:column; gap:1.2rem; }
  .step-line { display:none; }
}
</style>
""", unsafe_allow_html=True)

try:
    stats = json.loads((APP_DIR / "output" / "kybermart_stats.json").read_text())
except FileNotFoundError:
    stats = {}

# ── HERO ──────────────────────────────────────────────────────────────────────
left, right = st.columns([0.52, 0.48], gap="large")

with left:
    st.markdown(f"""
    <div style="padding-top:0.5rem">
      <div class="eyebrow">Computer Vision · Warehouse &amp; Logistics</div>
      <div class="hero-title">Kybermart<br/>Vision Demo</div>
      <div class="hero-sub">Automated box detection, tracking, counting &amp; dimensioning off a dock camera — built as a plug-in module for a logistics monitoring stack.</div>
      <div class="badge-row">
        <span class="badge">YOLO26x · custom-trained</span>
        <span class="badge">ByteTrack</span>
        <span class="badge">Roboflow</span>
        <span class="badge">Microservice-ready</span>
      </div>
      <div class="chip-row">
        <div class="chip"><div class="chip-num">{stats.get("peak_concurrent_boxes", "—")}</div><div class="chip-label">Peak boxes in one frame</div></div>
        <div class="chip"><div class="chip-num">{stats.get('line_in_count', 0)} / {stats.get('line_out_count', 0)}</div><div class="chip-label">Line-crossing in / out</div></div>
        <div class="chip"><div class="chip-num">32</div><div class="chip-label">Labeled frames to fine-tune</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.markdown('<div class="video-frame">', unsafe_allow_html=True)
    try:
        video_bytes = (APP_DIR / "output" / "kybermart_demo_web.mp4").read_bytes()
        st.video(video_bytes, autoplay=True, loop=True, muted=True)
    except FileNotFoundError:
        st.info("Demo video not found — run run_kybermart.py first.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── CAPABILITIES ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="section-label">What it does</div>
<div class="section-title">Full dock-camera intelligence</div>
""", unsafe_allow_html=True)

features = [
    ("📦", "Detection & Tracking", "Detects every visible box, pallet, forklift, and worker per frame. Tracking links detections across frames — no manual counting."),
    ("🔢", "In/Out Counting", "A configurable line zone counts boxes crossing a dock door or conveyor point — the same primitive used for automated shipment reconciliation against a manifest."),
    ("📏", "Dimension Estimate", "Approximate box width x height in real-world units, calibrated off a reference object in frame. Production would swap this for a depth camera for freight-grade accuracy."),
    ("🔌", "Microservice-Ready", "Runs as a stateless per-frame inference call — drops into a microservices architecture as its own service, publishing to whatever queue or API the rest of the stack expects."),
]
feature_html = '<div class="feature-grid">' + "".join(
    f'<div class="feature-card"><div class="feature-icon">{icon}</div><div class="feature-title">{title}</div><div class="feature-desc">{desc}</div></div>'
    for icon, title, desc in features
) + '</div>'
st.markdown(feature_html, unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── PIPELINE ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="section-label">How it works</div>
<div class="section-title">Pipeline</div>
""", unsafe_allow_html=True)

steps = [
    ("1", "Frame capture", "Camera feed (dock door, conveyor, aisle) read frame by frame."),
    ("2", "Detection", "Each frame is run against the box/pallet/forklift/worker model."),
    ("3", "Tracking", "Detections are linked across frames into object trajectories."),
    ("4", "Counting & measurement", "A line zone counts crossings; box dimensions are estimated."),
    ("5", "Output", "Annotated video plus structured stats, ready for a downstream service."),
]
stepper_html = '<div class="stepper">' + "".join(
    f'<div class="step"><div class="step-line"></div><div class="step-dot">{num}</div>'
    f'<div class="step-title">{title}</div><div class="step-desc">{desc}</div></div>'
    for num, title, desc in steps
) + '</div>'
st.markdown(stepper_html, unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── CAVEAT ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="note-card">
  <div class="note-icon">⚠️</div>
  <div>
    <b>Proof of concept, not a finished product.</b> The box detector is a custom YOLO26x model fine-tuned on a small
    hand-labeled sample from this one AI-generated clip — not real Kybermart camera footage. Forklift/worker detection
    still comes from a public pretrained model. Per-box identity isn't tracked reliably in this dense a pile (that's why
    there's no "total unique boxes ever seen" stat — it's not a number worth trusting yet). Detection accuracy, the
    counting line, and dimension calibration would all need real warehouse footage and more labeled data before this
    goes anywhere near production.
  </div>
</div>
""", unsafe_allow_html=True)
