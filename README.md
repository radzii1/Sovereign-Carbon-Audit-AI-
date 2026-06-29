# 🌿 Sovereign Carbon Audit AI
### UAE Enterprise ESG Reporting System — GHG Protocol Aligned

A production-grade multi-agent AI pipeline for automated carbon emissions auditing across UAE enterprise sites. Built with LangGraph, GPT-4o, and Streamlit.


##  Architecture

##  Agent Design

| Agent | Role | Technology |
|-------|------|------------|
| Intake Agent | Parses and validates incoming consumption data | LangGraph Node |
| Auditor Agent | Calculates carbon emissions using UAE emission factors | GPT-4o · Temperature 0.0 |
| Critic Agent | Reviews calculations for accuracy and grounds results | GPT-4o · Self-correction loop |
| Human Gate | Senior director approval before report generation | LangGraph Conditional Edge |
| Compliance Agent | Generates official GHG Protocol aligned report | GPT-4o · Context Anchoring |

##  Key Engineering Decisions

**TypedDict State Schema** — Enforces strict state contract across all agents. Prevents state drift where rogue agents append unverified variables to the execution context.

**Temperature 0.0** — All LLM calls use deterministic temperature. Carbon calculations submitted to regulators must return identical results for identical inputs. Creativity is a defect in compliance systems.

**Context Anchoring** — Emission factors are injected directly into the system prompt with hard prohibitive instructions. The LLM operates as a closed-book calculator using only verified UAE emission factors — not training data.

**Human-in-the-Loop** — A conditional edge pauses the pipeline before compliance report generation. No AI output touches a regulatory document without senior director sign-off.

**Self-Correction Loop** — The Critic Agent reviews every calculation before it reaches the human gate. Failed calculations loop back to the Auditor with error logs. Maximum 3 retries before escalation.

## 🇦🇪 UAE Emission Factors Database

| Source | Factor | Unit | GHG Scope |
|--------|--------|------|-----------|
| DEWA | 0.400 | kg CO2/kWh | Scope 2 |
| EWEC | 0.380 | kg CO2/kWh | Scope 2 |
| Diesel | 2.680 | kg CO2/litre | Scope 1 |

##  Features

- Multi-site CSV upload and batch processing
- Real-time audit progress tracking
- Scope 1 and Scope 2 emissions classification
- GHG Protocol Corporate Standard alignment
- UAE Net Zero 2050 recommendations
- Professional PDF report generation
- Human approval gate with audit trail

##  Tech Stack

- **Orchestration** — LangGraph (StateGraph, TypedDict, Conditional Edges)
- **LLM** — OpenAI GPT-4o (Temperature 0.0)
- **Frontend** — Streamlit
- **PDF Generation** — ReportLab
- **Data Processing** — Pandas
- **Environment** — Python 3.13, python-dotenv

##  Run Locally

```bash
# Clone the repository
git clone https://github.com/radzii1/sovereign-carbon-audit-AI.git

# Install dependencies
pip install langgraph langchain-openai streamlit reportlab pandas python-dotenv openai

# Add your OpenAI API key
echo OPENAI_API_KEY=your-key-here > .env

# Run the app
python -m streamlit run app.py
```

##  Sample Data Format

```csv
site,source,consumption,unit
DAMAC Heights,DEWA,500,MWh
DAMAC Hills,Diesel,2000,litres
```

##  Designed For

Enterprise ESG reporting in regulated UAE environments — ADNOC, DAMAC, G42, government entities — where every carbon calculation must be deterministic, auditable, and human-approved before publication.

---

*Built by Radhika Arya — AI Solutions Engineer · Dubai, UAE*

Enterprise ESG reporting in regulated UAE environments — ADNOC, DAMAC, G42, government entities — where every carbon calculation must be deterministic, auditable, and human-approved before publication.

---

*Built by Radhika Arya — AI Solutions Engineer · Dubai, UAE*  
*[LinkedIn](https://linkedin.com/in/radhikaarya10) · [GitHub](https://github.com/radzii1)*
