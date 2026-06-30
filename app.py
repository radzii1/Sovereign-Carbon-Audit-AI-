import streamlit as st
import pandas as pd
from openai import OpenAI
from typing import TypedDict
import os
from langsmith.wrappers import wrap_openai
from langsmith import traceable
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import HRFlowable
import io
from datetime import datetime

# ─── LANGSMITH + OPENAI SETUP ────────────────────────────────────────────────
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGSMITH_API_KEY"]
os.environ["LANGCHAIN_PROJECT"] = "sovereign-carbon-audit-ai"

client = wrap_openai(OpenAI(api_key=st.secrets["OPENAI_API_KEY"]))

st.set_page_config(
    page_title="Sovereign Carbon Audit AI",
    page_icon="🌿",
    layout="wide"
)

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
 
qdrant = QdrantClient(
    url=st.secrets["QDRANT_URL"],
    api_key=st.secrets["QDRANT_API_KEY"],
)
 
QDRANT_COLLECTION = "uae_emission_factors"
 
EMISSION_FACTORS_SEED_DATA = [
    {"source": "DEWA", "description": "Dubai Electricity and Water Authority grid electricity, Dubai emirate power supply, DEWA electricity consumption, Dubai utility power", "factor": 0.400, "unit": "kg CO2/kWh", "scope": "Scope 2"},
    {"source": "EWEC", "description": "Emirates Water and Electricity Company grid electricity, Abu Dhabi power supply, EWEC electricity, federal UAE grid power", "factor": 0.380, "unit": "kg CO2/kWh", "scope": "Scope 2"},
    {"source": "ADDC", "description": "Abu Dhabi Distribution Company grid electricity, ADDC power supply, Abu Dhabi emirate electricity distribution", "factor": 0.390, "unit": "kg CO2/kWh", "scope": "Scope 2"},
    {"source": "SEWA", "description": "Sharjah Electricity and Water Authority grid electricity, SEWA power supply, Sharjah emirate electricity", "factor": 0.395, "unit": "kg CO2/kWh", "scope": "Scope 2"},
    {"source": "Diesel", "description": "diesel fuel combustion, backup generator diesel, site diesel consumption, diesel litres burned, generator fuel", "factor": 2.680, "unit": "kg CO2/litre", "scope": "Scope 1"},
    {"source": "Gas", "description": "natural gas combustion, LPG gas, site gas consumption, gas litres burned, cooking gas, heating gas", "factor": 2.040, "unit": "kg CO2/litre", "scope": "Scope 1"},
    {"source": "Petrol", "description": "petrol fuel, gasoline combustion, vehicle fleet petrol, company car fuel consumption", "factor": 2.310, "unit": "kg CO2/litre", "scope": "Scope 1"},
    {"source": "Water", "description": "desalinated water consumption, water usage, municipal water supply, water treatment emissions", "factor": 0.344, "unit": "kg CO2/m3", "scope": "Scope 3"},
]
 
 
def get_embedding(text: str) -> list:
    """Converts text into a vector using OpenAI's embedding model"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding
 
 
def setup_qdrant_collection():
    """One-time setup: creates collection and uploads all emission factors as vectors"""
    collections = qdrant.get_collections().collections
    existing_names = [c.name for c in collections]
 
    if QDRANT_COLLECTION in existing_names:
        qdrant.delete_collection(QDRANT_COLLECTION)
 
    qdrant.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )
 
    points = []
    for i, item in enumerate(EMISSION_FACTORS_SEED_DATA):
        vector = get_embedding(item["description"])
        points.append(
            PointStruct(
                id=i,
                vector=vector,
                payload={
                    "source": item["source"],
                    "description": item["description"],
                    "factor": item["factor"],
                    "unit": item["unit"],
                    "scope": item["scope"],
                }
            )
        )
 
    qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points)
    return len(points)
 
 
@traceable(name="Qdrant Retrieval")
def retrieve_emission_factor(source_query: str) -> dict:
    """
    Semantic search — finds the closest matching emission factor
    even if the input wording doesn't exactly match (e.g. 'Dubai electricity' -> DEWA)
    """
    query_vector = get_embedding(source_query)
 
    results = qdrant.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=1,
    ).points
 
    if not results:
        return None
 
    match = results[0]
    return {
        "source": match.payload["source"],
        "factor": match.payload["factor"],
        "unit": match.payload["unit"],
        "scope": match.payload["scope"],
        "confidence": round(match.score, 3),
    }

# ─── EMISSION FACTORS DATABASE ───────────────────────────────────────────────
# Mock vector database — will be replaced by Qdrant with semantic search
EMISSION_FACTORS = {
    "DEWA":   {"factor": 0.400, "unit": "kg CO2/kWh",    "scope": "Scope 2"},
    "EWEC":   {"factor": 0.380, "unit": "kg CO2/kWh",    "scope": "Scope 2"},
    "ADDC":   {"factor": 0.390, "unit": "kg CO2/kWh",    "scope": "Scope 2"},
    "SEWA":   {"factor": 0.395, "unit": "kg CO2/kWh",    "scope": "Scope 2"},
    "Diesel": {"factor": 2.680, "unit": "kg CO2/litre",  "scope": "Scope 1"},
    "Gas":    {"factor": 2.040, "unit": "kg CO2/litre",  "scope": "Scope 1"},
}

class AgentState(TypedDict):
    raw_data: str
    is_approved: bool
    result: str
    error_log: str

# ─── AGENTS ──────────────────────────────────────────────────────────────────

@traceable(name="Auditor Agent")
def run_auditor(site: str, source: str, consumption: float, unit: str) -> dict:
    factor_info = EMISSION_FACTORS.get(source, None)

    if not factor_info:
        return {
            "site": site,
            "source": source,
            "consumption": consumption,
            "unit": unit,
            "calculation": "ERROR: Unknown source",
            "result_tonnes": 0,
            "scope": "Unknown",
            "status": "error"
        }

    context = f"""
    Source: {source}
    Emission Factor: {factor_info['factor']} {factor_info['unit']}
    Scope: {factor_info['scope']}
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[
            {
                "role": "system",
                "content": f"""You are a certified carbon auditor for UAE enterprises.
You MUST only use the emission factor provided in the CONTEXT below.

CONTEXT:
{context}

Return ONLY this exact format, nothing else:
CALCULATION: [show the math step by step]
RESULT: [final answer in tonnes CO2 only, convert kg to tonnes by dividing by 1000]
SCOPE: {factor_info['scope']}"""
            },
            {
                "role": "user",
                "content": f"Calculate carbon emissions for {site}: {consumption} {unit} from {source}"
            }
        ]
    )

    output = response.choices[0].message.content
    lines = output.strip().split("\n")

    calculation = ""
    result_tonnes = 0.0

    for line in lines:
        if line.startswith("CALCULATION:"):
            calculation = line.replace("CALCULATION:", "").strip()
        elif line.startswith("RESULT:"):
            try:
                raw = line.replace("RESULT:", "").strip()
                raw = raw.replace(",", "").split()[0]
                result_tonnes = float(raw)
            except:
                result_tonnes = 0.0

    return {
        "site": site,
        "source": source,
        "consumption": consumption,
        "unit": unit,
        "calculation": calculation,
        "result_tonnes": result_tonnes,
        "scope": factor_info['scope'],
        "status": "calculated"
    }


@traceable(name="Critic Agent")
def run_critic(site: str, source: str, consumption: float,
               unit: str, result_tonnes: float) -> dict:

    factor_info = EMISSION_FACTORS.get(source, None)

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[
            {
                "role": "system",
                "content": """You are a senior carbon audit reviewer.
Your job is to verify if a carbon calculation is correct.
Check:
1. Was the correct emission factor used?
2. Is the arithmetic correct?
3. Is the GHG Protocol scope correct?

Return ONLY this exact format:
VERDICT: pass or fail
REASON: [one sentence explanation]
CORRECTED_RESULT: [number in tonnes, or same as input if correct]"""
            },
            {
                "role": "user",
                "content": f"""Verify this calculation:
Site: {site}
Source: {source}
Consumption: {consumption} {unit}
Emission Factor: {factor_info['factor']} {factor_info['unit']}
Calculated Result: {result_tonnes} tonnes CO2

Is this correct?"""
            }
        ]
    )

    output = response.choices[0].message.content
    lines = output.strip().split("\n")

    verdict = "pass"
    reason = ""
    corrected = result_tonnes

    for line in lines:
        if line.startswith("VERDICT:"):
            verdict = line.replace("VERDICT:", "").strip().lower()
        elif line.startswith("REASON:"):
            reason = line.replace("REASON:", "").strip()
        elif line.startswith("CORRECTED_RESULT:"):
            try:
                corrected = float(line.replace("CORRECTED_RESULT:", "").strip().replace(",", ""))
            except:
                corrected = result_tonnes

    return {
        "verdict": verdict,
        "reason": reason,
        "corrected_result": corrected
    }


@traceable(name="Compliance Agent")
def run_compliance_report(results: list) -> str:
    total = sum(r["result_tonnes"] for r in results)
    summary = "\n".join([
        f"- {r['site']} ({r['source']}): {r['result_tonnes']:,.0f} tonnes CO2"
        for r in results
    ])

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[
            {
                "role": "system",
                "content": """You are a UAE enterprise ESG compliance officer.
Generate a formal carbon audit report with these sections:
1. Executive Summary
2. Emissions Breakdown by Site
3. Total Carbon Footprint
4. GHG Protocol Classification
5. Recommended Carbon Reduction Actions

Be specific, professional, and reference UAE sustainability goals (UAE Net Zero 2050)."""
            },
            {
                "role": "user",
                "content": f"""Generate a compliance report for these results:

{summary}

Total: {total:,.2f} tonnes CO2"""
            }
        ]
    )
    return response.choices[0].message.content


def generate_pdf(results: list, compliance_text: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20,
                                  textColor=colors.HexColor('#1B4F72'), spaceAfter=4)
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10,
                                textColor=colors.HexColor('#555555'), spaceAfter=2)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10,
                                 leading=16, spaceAfter=8)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=13,
                                    textColor=colors.HexColor('#1B4F72'), spaceBefore=16, spaceAfter=6)

    elements.append(Paragraph("🌿 Sovereign Carbon Audit Report", title_style))
    elements.append(Paragraph("UAE Enterprise ESG Reporting System — GHG Protocol Aligned", sub_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}", sub_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1B4F72'), spaceAfter=12))

    total = sum(r["result_tonnes"] for r in results)
    scope1 = sum(r["result_tonnes"] for r in results if r["scope"] == "Scope 1")
    scope2 = sum(r["result_tonnes"] for r in results if r["scope"] == "Scope 2")

    elements.append(Paragraph("Carbon Summary", section_style))
    summary_data = [
        ["Metric", "Value"],
        ["Total Carbon Footprint", f"{total:,.2f} tonnes CO2"],
        ["Scope 1 (Direct - Diesel/Gas)", f"{scope1:,.2f} tonnes CO2"],
        ["Scope 2 (Indirect - Electricity)", f"{scope2:,.2f} tonnes CO2"],
        ["Sites Audited", str(len(results))],
        ["Reporting Standard", "GHG Protocol Corporate Standard"],
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1B4F72')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#EBF5FB'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(summary_table)

    elements.append(Paragraph("Emissions Breakdown by Site", section_style))
    site_data = [["Site", "Source", "Consumption", "Unit", "CO2 (tonnes)", "Scope", "Status"]]
    for r in results:
        site_data.append([
            r["site"], r["source"], f"{r['consumption']:,}",
            r["unit"], f"{r['result_tonnes']:,.0f}", r["scope"],
            r.get("status", "verified").upper()
        ])
    site_table = Table(site_data, colWidths=[1.3*inch, 0.8*inch, 0.9*inch, 0.5*inch, 1*inch, 0.7*inch, 0.8*inch])
    site_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1B4F72')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#EBF5FB'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (2,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(site_table)

    elements.append(Paragraph("Official Compliance Report", section_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CCCCCC'), spaceAfter=8))

    for para in compliance_text.split('\n'):
        if para.strip():
            clean = para.replace('**', '').replace('*', '')
            if para.startswith('**') or para.startswith('#'):
                elements.append(Paragraph(clean, section_style))
            else:
                elements.append(Paragraph(clean, body_style))

    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CCCCCC'), spaceAfter=6))
    elements.append(Paragraph(
        "This report was generated by Sovereign Carbon Audit AI — UAE Enterprise ESG Reporting System. "
        "All calculations follow GHG Protocol Corporate Accounting and Reporting Standard.",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#888888'))
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "audit_results" not in st.session_state:
    st.session_state.audit_results = None
if "final_report" not in st.session_state:
    st.session_state.final_report = None

# ─── UI ───────────────────────────────────────────────────────────────────────
st.title("🌿 Sovereign Carbon Audit AI")
st.caption("UAE Enterprise ESG Reporting System — GHG Protocol Aligned")
st.divider()

st.markdown("### Step 1 — Upload Consumption Data")
st.caption("Upload a CSV with columns: site, source, consumption, unit")
st.caption("Supported sources: DEWA, EWEC, ADDC, SEWA, Diesel, Gas")

uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip().str.lower()
    st.success(f"✓ File uploaded — {len(df)} sites detected")
    st.dataframe(df, use_container_width=True)

    if st.button("🔍 Run Audit on All Sites", type="primary"):
        st.session_state.final_report = None
        results = []

        progress = st.progress(0)
        status = st.empty()

        for i, row in df.iterrows():
            site = str(row.iloc[0]).strip()
            source = str(row.iloc[1]).strip()
            consumption = float(row.iloc[2])
            unit = str(row.iloc[3]).strip()

            status.text(f"Auditor Agent → {site}...")
            result = run_auditor(
                site=site, source=source,
                consumption=consumption, unit=unit
            )

            status.text(f"Critic Agent reviewing → {site}...")
            critic = run_critic(
                site=site, source=source,
                consumption=consumption, unit=unit,
                result_tonnes=result["result_tonnes"]
            )

            if critic["verdict"] == "fail":
                result["result_tonnes"] = critic["corrected_result"]
                result["error_log"] = critic["reason"]
                result["status"] = "corrected"
            else:
                result["error_log"] = ""
                result["status"] = "verified"

            results.append(result)
            progress.progress((i + 1) / len(df))

        st.session_state.audit_results = results
        status.text("✓ All sites audited and verified")

if st.session_state.audit_results:
    st.divider()
    st.markdown("### Step 2 — Audit Results by Site")

    results_df = pd.DataFrame(st.session_state.audit_results)

    col1, col2, col3 = st.columns(3)
    total = sum(r["result_tonnes"] for r in st.session_state.audit_results)
    scope1 = sum(r["result_tonnes"] for r in st.session_state.audit_results if r["scope"] == "Scope 1")
    scope2 = sum(r["result_tonnes"] for r in st.session_state.audit_results if r["scope"] == "Scope 2")

    col1.metric("Total CO2", f"{total:,.2f} tonnes")
    col2.metric("Scope 1 (Diesel/Gas)", f"{scope1:,.2f} tonnes")
    col3.metric("Scope 2 (Electricity)", f"{scope2:,.2f} tonnes")

    st.dataframe(
        results_df[["site", "source", "consumption", "unit", "result_tonnes", "scope", "status"]],
        use_container_width=True
    )

    st.divider()
    st.markdown("### Step 3 — Human Approval Gate")
    st.warning("⚠️ A senior director must review and approve before the compliance report is generated.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Approve & Generate Report", type="primary"):
            with st.spinner("Compliance Agent generating official report..."):
                st.session_state.final_report = run_compliance_report(
                    st.session_state.audit_results
                )
    with col2:
        if st.button("❌ Reject"):
            st.session_state.audit_results = None
            st.session_state.final_report = None
            st.error("❌ Pipeline rejected. No report generated.")
            st.rerun()

if st.session_state.final_report:
    st.divider()
    st.markdown("### Step 4 — Official Compliance Report")
    st.success("✓ Approved and signed off by senior director")
    st.markdown(st.session_state.final_report)

    pdf_bytes = generate_pdf(
        st.session_state.audit_results,
        st.session_state.final_report
    )

    st.download_button(
        label="📄 Download Official PDF Report",
        data=pdf_bytes,
        file_name=f"carbon_audit_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf"
    )
    st.balloons()
