import streamlit as st
from groq import Groq
import json
import re
import requests
from bs4 import BeautifulSoup
import urllib.parse

st.set_page_config(page_title="Clinical Notes Extractor", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    .main .block-container { padding: 2rem 3rem; max-width: 100%; }
    .app-header { padding: 1.5rem 0 0.5rem 0; margin-bottom: 0.5rem; }
    .app-header h1 { font-size: 1.75rem; font-weight: 700; color: #1a1a2e; margin: 0; }
    .app-header p { color: #6b7280; font-size: 0.95rem; margin: 0.25rem 0 0 0; }
    .stTextArea textarea {
        font-size: 0.95rem; line-height: 1.6; border-radius: 10px;
        border: 1.5px solid #374151; padding: 1rem; font-family: 'Georgia', serif;
        background: #1e1e2e; color: #e5e7eb; caret-color: #e5e7eb;
    }
    div[data-testid="stButton"] button {
        background: linear-gradient(135deg, #6366f1, #4f46e5);
        color: white; border: none; border-radius: 8px;
        padding: 0.6rem 2.5rem; font-size: 1rem; font-weight: 600; width: 100%;
    }
    .section-title { font-size: 1.1rem; font-weight: 700; color: #1a1a2e; margin: 1.5rem 0 1rem 0; padding-bottom: 0.4rem; border-bottom: 2px solid #e5e7eb; }
    .cpg-section-title { font-size: 1.1rem; font-weight: 700; color: #0f4c81; margin: 1.5rem 0 1rem 0; padding-bottom: 0.4rem; border-bottom: 2px solid #bfdbfe; }
    .feature-card { background: white; border-radius: 12px; padding: 1rem 1.2rem; border: 1.5px solid #e5e7eb; margin-bottom: 0.75rem; }
    .card-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.3rem; }
    .card-value { font-size: 1rem; font-weight: 600; color: #111827; line-height: 1.4; }
    .card-note { font-size: 0.8rem; color: #9ca3af; margin-top: 0.2rem; }
    .label-blue{color:#3b82f6} .label-pink{color:#ec4899} .label-green{color:#10b981}
    .label-orange{color:#f59e0b} .label-red{color:#ef4444} .label-purple{color:#8b5cf6}
    .label-teal{color:#14b8a6} .label-indigo{color:#6366f1}
    .card-blue{border-left:4px solid #3b82f6;background:#eff6ff}
    .card-pink{border-left:4px solid #ec4899;background:#fdf2f8}
    .card-green{border-left:4px solid #10b981;background:#ecfdf5}
    .card-orange{border-left:4px solid #f59e0b;background:#fffbeb}
    .card-red{border-left:4px solid #ef4444;background:#fef2f2}
    .card-purple{border-left:4px solid #8b5cf6;background:#f5f3ff}
    .card-teal{border-left:4px solid #14b8a6;background:#f0fdfa}
    .card-indigo{border-left:4px solid #6366f1;background:#eef2ff}
    .badge{display:inline-block;padding:0.15rem 0.6rem;border-radius:999px;font-size:0.75rem;font-weight:600}
    .badge-red{background:#fee2e2;color:#991b1b} .badge-yellow{background:#fef9c3;color:#854d0e}
    .badge-green{background:#dcfce7;color:#166534} .badge-gray{background:#f3f4f6;color:#374151}
    .cpg-card { background:#f0f7ff; border:1.5px solid #bfdbfe; border-left:5px solid #2563eb; border-radius:12px; padding:1rem 1.2rem; margin-bottom:0.85rem; }
    .cpg-card-title { font-size:0.95rem; font-weight:700; color:#1e3a5f; margin-bottom:0.35rem; }
    .cpg-card-org { font-size:0.75rem; font-weight:600; color:#2563eb; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.5rem; }
    .cpg-card-link { font-size:0.8rem; margin-top:0.5rem; }
    .cpg-card-link a { color:#1d4ed8; text-decoration:underline; }
    .cpg-source-badge { display:inline-block; font-size:0.7rem; padding:2px 8px; border-radius:999px; background:#dbeafe; color:#1e40af; font-weight:600; margin-right:6px; }
    .cpg-scraped-badge { display:inline-block; font-size:0.7rem; padding:2px 8px; border-radius:999px; background:#dcfce7; color:#166534; font-weight:600; }
    .cpg-llm-badge { display:inline-block; font-size:0.7rem; padding:2px 8px; border-radius:999px; background:#fef9c3; color:#854d0e; font-weight:600; }
    .summary-box { background:#f0f9ff; border:1.5px solid #bae6fd; border-radius:12px; padding:1rem 1.25rem; margin-top:1.5rem; font-size:0.9rem; color:#0c4a6e; line-height:1.7; }
    .agent-status { font-size:0.82rem; color:#6b7280; padding:3px 0; font-style:italic; }
</style>
""", unsafe_allow_html=True)

# ── SAMPLE NOTES ─────────────────────────────────────────────────────────────

SAMPLE_NOTES = {
    "Cardiac Case": """Patient: John Miller, 67-year-old male.
Chief Complaint: Chest pain and shortness of breath on exertion for 3 weeks.
History: Known hypertensive (Amlodipine 10mg), Type 2 DM (Metformin 1000mg BD), smoker 30 pack-years, quit 5 years ago.
Examination: BP 155/95 mmHg, HR 88 bpm irregular, BMI 31.2. JVP elevated. Bilateral crackles at lung bases.
ECG: Atrial fibrillation with ventricular rate 88 bpm. ST depression V4-V6.
Echo: EF 38%, moderate mitral regurgitation, hypokinesia of lateral wall.
Labs: Troponin I 0.08 ng/mL (elevated), BNP 780 pg/mL, HbA1c 8.9%, eGFR 62 mL/min.
Diagnosis: Acute decompensated heart failure secondary to ischemic cardiomyopathy. NSTEMI with underlying AF.
Plan: Admit CCU. Furosemide 40mg IV, Bisoprolol 2.5mg, Rivaroxaban, cardiology consult for angiography.""",

    "Oncology Case": """Name: Fatima Al-Hassan, 54F. 3-month history of left breast lump and axillary pain.
PMH: No prior malignancy. Mother had breast cancer at 62. BRCA testing pending.
O/E: 2.5cm firm irregular mass left upper outer quadrant. 2 palpable left axillary nodes.
Imaging: Mammogram BIRADS-5. MRI: 2.8cm spiculated mass, suspicious axillary adenopathy.
Biopsy: Invasive ductal carcinoma, Grade 3, ER+/PR+/HER2-, Ki-67 28%. Stage IIB (T2 N1 M0).
Plan: MDT review. Neoadjuvant chemo (AC-T), lumpectomy + sentinel node biopsy. Radiation + Tamoxifen.""",

    "Pediatric Case": """Patient: Yusuf Ibrahim, 8-year-old male. 4-day high fever, sore throat, difficulty swallowing.
HPI: Fever 39.8C, odynophagia, muffled voice, neck stiffness, drooling.
Examination: T 39.6C, HR 124, RR 24, SpO2 96%. Bilateral tonsillar enlargement with exudate, uvula deviation right, trismus.
Labs: WBC 18,400 (neutrophils 84%), CRP 187 mg/L.
Imaging: Neck US: 3.1cm peritonsillar fluid collection right.
Diagnosis: Right peritonsillar abscess with early airway compromise.
Management: ENT consult. IV Amoxicillin-Clavulanate + Dexamethasone 0.15mg/kg. Needle aspiration. Monitor airway.""",
}

# ── AGENT 1: CLINICAL FEATURE EXTRACTOR ─────────────────────────────────────

EXTRACTION_PROMPT = """You are a clinical NLP specialist. Extract structured clinical features from the medical note.
Return ONLY valid JSON — no markdown, no explanation, no backticks.

{
  "patient": {"name":null,"age":null,"gender":null,"bmi":null,"weight":null},
  "vitals": {"blood_pressure":null,"heart_rate":null,"temperature":null,"spo2":null,"respiratory_rate":null},
  "diagnoses": [],
  "symptoms": [],
  "medications": [],
  "allergies": [],
  "lab_results": {},
  "imaging": [],
  "risk_factors": [],
  "plan": [],
  "severity": "critical | high | moderate | low",
  "specialty": "e.g. Cardiology",
  "summary": "2-3 sentence summary"
}
Use null for missing, [] for empty lists. severity: critical=life-threatening, high=serious, moderate=significant, low=routine."""


def extract_features(note_text: str, api_key: str) -> dict:
    client = Groq(api_key=api_key)
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": f"Extract clinical features:\n\n{note_text}"}
        ],
        temperature=0.1, max_tokens=2048,
    )
    raw = r.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*|^```\s*|\s*```$', '', raw)
    return json.loads(raw)


# ── AGENT 2: NCCIH SCRAPER TOOL ──────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

NCCIH_CPG_URL = "https://www.nccih.nih.gov/health/providers/clinicalpractice"


def scrape_nccih(query: str) -> dict:
    """Scrape the NCCIH clinical practice guidelines page and filter by query relevance."""
    results = []
    base = "https://www.nccih.nih.gov"
    q_words = set(query.lower().split())

    try:
        r = requests.get(NCCIH_CPG_URL, headers=HEADERS, timeout=12)
        if r.ok:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                if len(text) < 15:
                    continue
                text_lower = text.lower()
                # Include if query words match OR it's a guideline/recommendation link
                if q_words & set(text_lower.split()) or any(k in text_lower for k in ["guideline", "recommendation", "practice", "clinical"]):
                    href = a["href"]
                    full_url = href if href.startswith("http") else base + href
                    results.append({"title": text, "url": full_url, "source": "NCCIH"})
    except Exception as e:
        return {"source": "NCCIH", "url_checked": NCCIH_CPG_URL, "results": [], "error": str(e), "query": query}

    # Deduplicate by URL
    seen = set()
    unique = []
    for item in results:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)

    return {
        "source": "NCCIH",
        "url_checked": NCCIH_CPG_URL,
        "results": unique[:6],
        "query": query,
        "total_found": len(unique),
    }


TOOL_FUNCTIONS = {
    "scrape_nccih": scrape_nccih,
}

CPG_TOOLS = [
    {"type": "function", "function": {
        "name": "scrape_nccih",
        "description": (
            "Scrapes the NCCIH (National Center for Complementary and Integrative Health) "
            "clinical practice guidelines page at https://www.nccih.nih.gov/health/providers/clinicalpractice "
            "and returns matching guideline links for the given medical condition."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Medical condition or diagnosis to search for, e.g. 'heart failure', 'breast cancer'"
                }
            },
            "required": ["query"]
        }
    }},
]

CPG_AGENT_SYSTEM = """You are a clinical guidelines research agent. Your ONLY source is NCCIH.

Steps:
1. Call scrape_nccih once with the primary diagnosis as the query.
2. Use the returned links. If results are sparse, supplement with your medical knowledge about NCCIH-published or other authoritative guidelines (ACC/AHA, NICE, WHO).
3. Output ONLY this JSON — no markdown, no preamble:

{
  "guidelines": [
    {
      "title": "Full guideline title",
      "organization": "Issuing organization",
      "key_recommendations": ["2-3 concise actionable recommendations"],
      "url": "Direct URL",
      "source_type": "scraped | knowledge",
      "year": "Year or estimated",
      "relevance": "Why this applies to the patient"
    }
  ],
  "search_summary": "One sentence describing what was found."
}

Rules:
- source_type = "scraped" if URL came from the tool result, "knowledge" if from your training data.
- Include 3-5 total guidelines. Prefer scraped results; fill gaps with knowledge entries.
- Fallback URL for knowledge entries: https://www.nccih.nih.gov/health/providers/clinicalpractice"""


def run_cpg_agent(diagnoses: list, specialty: str, api_key: str, status_box) -> dict:
    client = Groq(api_key=api_key)
    diag_str = ", ".join(diagnoses[:3]) if diagnoses else "unspecified"

    messages = [
        {"role": "system", "content": CPG_AGENT_SYSTEM},
        {"role": "user", "content": (
            f"Find CPGs for: Diagnoses: {diag_str} | Specialty: {specialty or 'General Medicine'}. "
            "Call scrape_nccih then output final JSON."
        )}
    ]

    # Max 3 rounds — tool call + synthesis is all we need
    for _ in range(3):
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=CPG_TOOLS,
            tool_choice="auto",
            temperature=0.2,
            max_tokens=1800,
        )
        msg = resp.choices[0].message

        asst_msg = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            asst_msg["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        messages.append(asst_msg)

        # No tool calls → agent is done
        if not msg.tool_calls:
            raw = (msg.content or "").strip()
            raw = re.sub(r'^```json\s*|^```\s*|\s*```$', '', raw)
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                raw = match.group(0)
            try:
                return json.loads(raw)
            except Exception:
                break

        # Execute the single NCCIH tool
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except Exception:
                fn_args = {}

            status_box.markdown(
                f'<div class="agent-status">🔍 Scraping <b>NCCIH</b> for "{fn_args.get("query", "")}"...</div>',
                unsafe_allow_html=True
            )

            fn = TOOL_FUNCTIONS.get(fn_name)
            result = fn(**fn_args) if fn else {"error": f"Unknown tool: {fn_name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result)
            })

    # Fallback: ask model to synthesize with what it has
    status_box.markdown('<div class="agent-status">🤖 Synthesizing guidelines...</div>', unsafe_allow_html=True)
    final = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages + [{"role": "user", "content": "Output ONLY the final JSON with guidelines array. No markdown."}],
        temperature=0.1,
        max_tokens=1500,
    )
    raw = final.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*|^```\s*|\s*```$', '', raw)
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        raw = match.group(0)
    try:
        return json.loads(raw)
    except Exception:
        return {"guidelines": [], "search_summary": "Could not parse CPG response."}


# ── RENDER HELPERS ────────────────────────────────────────────────────────────

def severity_badge(s):
    m = {
        "critical": ("badge-red", "🔴 Critical"),
        "high": ("badge-red", "🟠 High"),
        "moderate": ("badge-yellow", "🟡 Moderate"),
        "low": ("badge-green", "🟢 Low"),
    }
    cls, lbl = m.get((s or "").lower(), ("badge-gray", s or "Unknown"))
    return f'<span class="badge {cls}">{lbl}</span>'


def render_card(label, value, color, note=""):
    if value is None or value == "" or value == [] or value == {}:
        return ""
    if isinstance(value, list):
        display = "<br>".join(f"• {v}" for v in value)
    elif isinstance(value, dict):
        display = "<br>".join(f"<b>{k}:</b> {v}" for k, v in value.items() if v)
    else:
        display = str(value)
    note_html = f'<div class="card-note">{note}</div>' if note else ""
    return (f'<div class="feature-card card-{color}">'
            f'<div class="card-label label-{color}">{label}</div>'
            f'<div class="card-value">{display}</div>'
            f'{note_html}</div>')


def render_cpg_section(cpg_data: dict):
    guidelines = cpg_data.get("guidelines", [])
    summary = cpg_data.get("search_summary", "")

    st.markdown('<div class="cpg-section-title">📚 Clinical Practice Guidelines — NCCIH</div>', unsafe_allow_html=True)
    if summary:
        st.markdown(
            f'<div style="font-size:0.82rem;color:#6b7280;margin-bottom:0.8rem;font-style:italic">'
            f'Source: <b>NCCIH</b> (nccih.nih.gov/health/providers/clinicalpractice)&nbsp;|&nbsp;{summary}</div>',
            unsafe_allow_html=True
        )
    if not guidelines:
        st.info("No guidelines retrieved. Verify network access to nccih.nih.gov.")
        return

    for g in guidelines:
        title = g.get("title", "Unnamed Guideline")
        org = g.get("organization", "")
        recs = g.get("key_recommendations", [])
        url = g.get("url", "")
        year = g.get("year", "")
        relevance = g.get("relevance", "")
        stype = g.get("source_type", "knowledge")

        src_badge = (
            '<span class="cpg-scraped-badge">✓ Live Retrieved</span>'
            if stype == "scraped"
            else '<span class="cpg-llm-badge">✦ AI Knowledge</span>'
        )
        year_html = f'&nbsp;·&nbsp;<span style="font-size:0.75rem;color:#64748b">{year}</span>' if year else ""
        recs_html = (
            "<ul style='margin:0.4rem 0 0 1rem;padding:0'>"
            + "".join(f"<li style='font-size:0.85rem;color:#1e40af;margin-bottom:0.25rem'>{r}</li>" for r in recs)
            + "</ul>"
        ) if recs else ""
        rel_html = f'<div style="font-size:0.78rem;color:#64748b;margin-top:0.4rem"><i>Relevance: {relevance}</i></div>' if relevance else ""
        link_html = f'<div class="cpg-card-link">🔗 <a href="{url}" target="_blank">{url[:90]}{"..." if len(url) > 90 else ""}</a></div>' if url else ""

        st.markdown(f"""<div class="cpg-card">
            <div class="cpg-card-org"><span class="cpg-source-badge">{org}</span>{src_badge}{year_html}</div>
            <div class="cpg-card-title">{title}</div>
            {recs_html}{rel_html}{link_html}
        </div>""", unsafe_allow_html=True)


def render_results(data: dict):
    p = data.get("patient", {})
    v = data.get("vitals", {})

    st.markdown('<div class="section-title">Patient Overview</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    for col, lbl, val, color in [
        (c1, "👤 Patient", p.get("name"), "blue"),
        (c2, "🎂 Age", p.get("age"), "purple"),
        (c3, "⚕ Gender", p.get("gender"), "pink"),
        (c4, "🏥 Specialty", data.get("specialty"), "indigo"),
    ]:
        with col:
            if val:
                st.markdown(render_card(lbl, val, color), unsafe_allow_html=True)

    s1, s2, _, _ = st.columns(4)
    with s1:
        if data.get("severity"):
            st.markdown(
                f'<div class="feature-card card-red"><div class="card-label label-red">⚠ Severity</div>'
                f'<div class="card-value">{severity_badge(data["severity"])}</div></div>',
                unsafe_allow_html=True
            )
    with s2:
        bmi = p.get("bmi") or p.get("weight")
        if bmi:
            st.markdown(render_card("📊 BMI/Weight", bmi, "teal"), unsafe_allow_html=True)

    st.markdown('<div class="section-title">Vital Signs</div>', unsafe_allow_html=True)
    vcols = st.columns(5)
    for (lbl, val, color), col in zip([
        ("🩸 Blood Pressure", v.get("blood_pressure"), "red"),
        ("💓 Heart Rate", v.get("heart_rate"), "pink"),
        ("🌡 Temperature", v.get("temperature"), "orange"),
        ("💨 SpO₂", v.get("spo2"), "blue"),
        ("🫁 Resp. Rate", v.get("respiratory_rate"), "teal"),
    ], vcols):
        with col:
            if val:
                st.markdown(render_card(lbl, val, color), unsafe_allow_html=True)

    st.markdown('<div class="section-title">Clinical Findings</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown(render_card("🩺 Diagnoses", data.get("diagnoses", []), "red"), unsafe_allow_html=True)
        st.markdown(render_card("🤒 Symptoms", data.get("symptoms", []), "orange"), unsafe_allow_html=True)
    with f2:
        st.markdown(render_card("💊 Medications", data.get("medications", []), "green"), unsafe_allow_html=True)
        st.markdown(render_card("⚠ Risk Factors", data.get("risk_factors", []), "purple"), unsafe_allow_html=True)
    with f3:
        st.markdown(render_card("🔬 Lab Results", data.get("lab_results", {}), "blue"), unsafe_allow_html=True)
        st.markdown(render_card("🖼 Imaging", data.get("imaging", []), "teal"), unsafe_allow_html=True)

    if data.get("plan"):
        st.markdown('<div class="section-title">Management Plan</div>', unsafe_allow_html=True)
        st.markdown(render_card("📋 Plan", data["plan"], "indigo"), unsafe_allow_html=True)

    if data.get("summary"):
        st.markdown(f'<div class="summary-box"><b>Clinical Summary:</b> {data["summary"]}</div>', unsafe_allow_html=True)


# ── LAYOUT ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="app-header">
    <h1>🏥 Clinical Notes Extractor + CPG Agent</h1>
    <p>Agent 1 extracts clinical features · Agent 2 searches NCCIH for practice guidelines</p>
</div>
""", unsafe_allow_html=True)

API_KEY = "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"

st.markdown("**Try a sample note:**")
s_cols = st.columns(len(SAMPLE_NOTES))
for i, (label, note_text) in enumerate(SAMPLE_NOTES.items()):
    with s_cols[i]:
        if st.button(f"📋 {label}", use_container_width=True):
            st.session_state["note_input"] = note_text
            st.rerun()

note = st.text_area(
    label="Clinical Note",
    value=st.session_state.get("note_input", ""),
    height=220,
    placeholder="Paste clinical notes here — patient demographics, symptoms, vitals, labs, diagnosis, medications, plan...",
    label_visibility="collapsed",
)

_, btn_col, _ = st.columns([3, 2, 3])
with btn_col:
    submitted = st.button("⚡ Extract + Find Guidelines", use_container_width=True)

if submitted:
    if not note.strip():
        st.warning("Please paste a clinical note first.")
    else:
        st.markdown("---")

        # Agent 1 — Feature Extraction
        with st.spinner("🧠 Agent 1 — Extracting clinical features..."):
            try:
                clinical_data = extract_features(note, API_KEY)
            except Exception as e:
                st.error(f"Feature extraction failed: {e}")
                st.stop()

        # Agent 2 — NCCIH CPG Search
        diagnoses = clinical_data.get("diagnoses", [])
        specialty = clinical_data.get("specialty", "General Medicine")

        with st.container():
            st.markdown("**🔎 Agent 2 — Searching NCCIH Clinical Practice Guidelines...**")
            status_box = st.empty()
            try:
                cpg_data = run_cpg_agent(diagnoses, specialty, API_KEY, status_box)
                status_box.empty()
            except Exception as e:
                status_box.empty()
                cpg_data = {"guidelines": [], "search_summary": f"CPG search error: {e}"}

        # Render CPG first, then clinical features
        render_cpg_section(cpg_data)
        st.markdown("---")
        render_results(clinical_data)
