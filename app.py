import streamlit as st
import pandas as pd
from openai import OpenAI
from typing import TypedDict

client = OpenAI(api_key="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")

st.set_page_config(
    page_title="Sovereign Carbon Audit AI", 
    page_icon="🌿", 
    layout="wide"
)

# ─── EMISSION FACTORS DATABASE ───────────────────────────────────────────────
# This is your mock vector database for now
# Later this will be replaced by Qdrant with semantic search
EMISSION_FACTORS = {
    "DEWA": {"factor": 0.4, "unit": "kg CO2/kWh", "scope": "Scope 2"},
    "EWEC": {"factor": 0.38, "unit": "kg CO2/kWh", "scope": "Scope 2"},
    "Diesel": {"factor": 2.68, "unit": "kg CO2/litre", "scope": "Scope 1"},
}

class AgentState(TypedDict):
    raw_data: str
    is_approved: bool
    result: str
    error_log: str

# ─── AGENTS ──────────────────────────────────────────────────────────────────

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
RESULT: [number only, no units]
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


def run_compliance_report(results: list) -> str:
    total = sum(r["result_tonnes"] for r in results)
    summary = "\n".join([
        f"- {r['site']} ({r['source']}): {r['result_tonnes']} tonnes CO2"
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

Total: {total:.2f} tonnes CO2"""
            }
        ]
    )
    return response.choices[0].message.content

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import HRFlowable
import io
from datetime import datetime

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

    # ── Title
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1B4F72'),
        spaceAfter=4
    )
    sub_style = ParagraphStyle(
        'Sub',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#555555'),
        spaceAfter=2
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        leading=16,
        spaceAfter=8
    )
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#1B4F72'),
        spaceBefore=16,
        spaceAfter=6
    )

    elements.append(Paragraph("🌿 Sovereign Carbon Audit Report", title_style))
    elements.append(Paragraph("UAE Enterprise ESG Reporting System — GHG Protocol Aligned", sub_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}", sub_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1B4F72'), spaceAfter=12))

    # ── Metrics
    total = sum(r["result_tonnes"] for r in results)
    scope1 = sum(r["result_tonnes"] for r in results if r["scope"] == "Scope 1")
    scope2 = sum(r["result_tonnes"] for r in results if r["scope"] == "Scope 2")

    elements.append(Paragraph("Carbon Summary", section_style))

    summary_data = [
        ["Metric", "Value"],
        ["Total Carbon Footprint", f"{total:,.2f} tonnes CO2"],
        ["Scope 1 (Direct - Diesel)", f"{scope1:,.2f} tonnes CO2"],
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

    # ── Site Breakdown
    elements.append(Paragraph("Emissions Breakdown by Site", section_style))

    site_data = [["Site", "Source", "Consumption", "Unit", "CO2 (tonnes)", "Scope", "Status"]]
    for r in results:
        site_data.append([
            r["site"],
            r["source"],
            f"{r['consumption']:,}",
            r["unit"],
            f"{r['result_tonnes']:,.0f}",
            r["scope"],
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

    # ── Compliance Report
    elements.append(Paragraph("Official Compliance Report", section_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CCCCCC'), spaceAfter=8))

    for para in compliance_text.split('\n'):
        if para.strip():
            clean = para.replace('**', '').replace('*', '')
            if para.startswith('**') or para.startswith('#'):
                elements.append(Paragraph(clean, section_style))
            else:
                elements.append(Paragraph(clean, body_style))

    # ── Footer
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

# STEP 1 — Upload
st.markdown("### Step 1 — Upload Consumption Data")
st.caption("Upload a CSV with columns: site, source, consumption, unit")

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
            status.text(f"Auditing {row['site']}...")
            result = run_auditor(
                site=row["site"],
                source=row["source"],
                consumption=row["consumption"],
                unit=row["unit"]
            )
            results.append(result)
            progress.progress((i + 1) / len(df))
        
        st.session_state.audit_results = results
        status.text("✓ All sites audited")

# STEP 2 — Results Table
if st.session_state.audit_results:
    st.divider()
    st.markdown("### Step 2 — Audit Results by Site")
    
    results_df = pd.DataFrame(st.session_state.audit_results)
    
    col1, col2, col3 = st.columns(3)
    total = sum(r["result_tonnes"] for r in st.session_state.audit_results)
    scope1 = sum(r["result_tonnes"] for r in st.session_state.audit_results if r["scope"] == "Scope 1")
    scope2 = sum(r["result_tonnes"] for r in st.session_state.audit_results if r["scope"] == "Scope 2")
    
    col1.metric("Total CO2", f"{total:.2f} tonnes")
    col2.metric("Scope 1 (Diesel)", f"{scope1:.2f} tonnes")
    col3.metric("Scope 2 (Electricity)", f"{scope2:.2f} tonnes")
    
    st.dataframe(
        results_df[["site", "source", "consumption", "unit", "result_tonnes", "scope"]],
        use_container_width=True
    )
    
    # STEP 3 — Approval Gate
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
            st.error("❌ Pipeline rejected by director. No report generated.")
            st.rerun()

# STEP 4 — Final Report
if st.session_state.final_report:
    st.divider()
    st.markdown("### Step 4 — Official Compliance Report")
    st.success("✓ Approved and signed off by senior director")
    st.markdown(st.session_state.final_report)

    # Generate PDF
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
