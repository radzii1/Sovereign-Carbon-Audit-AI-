from typing import TypedDict

class AgentState(TypedDict):
    raw_data: str
    is_approved: bool
    result: str
    error_log: str

print("✓ AgentState schema loaded")
print("✓ Flagship project initialized")
from langgraph.graph import StateGraph

graph = StateGraph(AgentState)

def intake_agent(state: AgentState) -> AgentState:
    print("→ Intake Agent running...")
    state["raw_data"] = "DEWA electricity: 500 MWh"
    return state

def auditor_agent(state: AgentState) -> AgentState:
    print("→ Auditor Agent running...")
    state["result"] = "Carbon calculated: 500 x 0.4 = 200 tonnes CO2"
    return state

graph.add_node("intake", intake_agent)
graph.add_node("auditor", auditor_agent)
graph.add_edge("intake", "auditor")
graph.set_entry_point("intake")

app = graph.compile()
app.invoke({"raw_data": "", "is_approved": False, "result": "", "error_log": ""})

from typing import TypedDict
from langgraph.graph import StateGraph
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key="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")

class AgentState(TypedDict):
    raw_data: str
    is_approved: bool
    result: str
    error_log: str

def intake_agent(state: AgentState) -> AgentState:
    print("→ Intake Agent: Reading incoming data...")
    state["raw_data"] = "DEWA electricity consumption: 500 MWh"
    return state

def auditor_agent(state: AgentState) -> AgentState:
    print("→ Auditor Agent: Sending to LLM for carbon calculation...")
    
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[
            {
                "role": "system",
                "content": """You are a certified carbon auditor for UAE enterprises.
You MUST only use the emission factors provided below. Do not use any other values.

CONTEXT — UAE EMISSION FACTORS:
- DEWA grid electricity: 0.4 kg CO2 per kWh
- EWEC grid electricity: 0.38 kg CO2 per kWh
- Diesel combustion: 2.68 kg CO2 per litre

Calculate the carbon emissions and return ONLY this format:
CALCULATION: [show the math]
RESULT: [final number] tonnes CO2
STANDARD: [GHG Protocol Scope 2]"""
            },
            {
                "role": "user",
                "content": f"Calculate carbon emissions for: {state['raw_data']}"
            }
        ]
    )
    
    state["result"] = response.choices[0].message.content
    state["is_approved"] = False
    print(f"\n   LLM OUTPUT:\n{state['result']}\n")
    return state

def human_gate(state: AgentState) -> str:
    print("\n" + "="*50)
    print("HUMAN APPROVAL REQUIRED")
    print("="*50)
    print(f"Auditor Result:\n{state['result']}")
    print("="*50)
    
    # Temporarily set to True to test compliance agent
    approved = True
    
    if approved:
        print("✓ Approved — proceeding to compliance report")
        return "approved"
    else:
        print("✗ Rejected — pipeline stopped")
        return "rejected"

def compliance_agent(state: AgentState) -> AgentState:
    print("→ Compliance Agent: Generating official report...")
    print(f"   FINAL REPORT: {state['result']}")
    return state

graph = StateGraph(AgentState)
graph.add_node("intake", intake_agent)
graph.add_node("auditor", auditor_agent)
graph.add_node("compliance", compliance_agent)

graph.set_entry_point("intake")
graph.add_edge("intake", "auditor")
graph.add_conditional_edges("auditor", human_gate, {
    "approved": "compliance",
    "rejected": "__end__"
})

app = graph.compile()

print("\n--- RUNNING PIPELINE ---\n")
app.invoke({
    "raw_data": "",
    "is_approved": False,
    "result": "",
    "error_log": ""
})
from typing import TypedDict
from langgraph.graph import StateGraph
from openai import OpenAI
import os

client = OpenAI(api_key="sk-your-actual-key-here")

class AgentState(TypedDict):
    raw_data: str
    is_approved: bool
    result: str
    error_log: str

def intake_agent(state: AgentState) -> AgentState:
    print("→ Intake Agent: Reading incoming data...")
    state["raw_data"] = "DEWA electricity consumption: 500 MWh"
    return state

def auditor_agent(state: AgentState) -> AgentState:
    print("→ Auditor Agent: Sending to LLM for carbon calculation...")
    
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[
            {
                "role": "system",
                "content": """You are a certified carbon auditor for UAE enterprises.
You MUST only use the emission factors provided below. Do not use any other values.

CONTEXT — UAE EMISSION FACTORS:
- DEWA grid electricity: 0.4 kg CO2 per kWh
- EWEC grid electricity: 0.38 kg CO2 per kWh
- Diesel combustion: 2.68 kg CO2 per litre

Calculate the carbon emissions and return ONLY this format:
CALCULATION: [show the math]
RESULT: [final number] tonnes CO2
STANDARD: [GHG Protocol Scope 2]"""
            },
            {
                "role": "user",
                "content": f"Calculate carbon emissions for: {state['raw_data']}"
            }
        ]
    )
    
    state["result"] = response.choices[0].message.content
    state["is_approved"] = False
    print(f"\n   LLM OUTPUT:\n{state['result']}\n")
    return state

def human_gate(state: AgentState) -> str:
    print("\n" + "="*50)
    print("HUMAN APPROVAL REQUIRED")
    print("="*50)
    print(f"Auditor Result: {state['result']}")
    print("="*50)
    
    decision = input("Type 'approve' to proceed or 'reject' to stop: ").strip().lower()
    
    if decision == "approve":
        state["is_approved"] = True
        print("✓ Approved — proceeding to compliance report")
        return "approved"
    else:
        state["is_approved"] = False
        print("✗ Rejected — pipeline stopped")
        return "rejected"

def compliance_agent(state: AgentState) -> AgentState:
    print("\n" + "="*50)
    print("→ Compliance Agent: Generating official report...")
    print("="*50)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[
            {
                "role": "system",
                "content": """You are a UAE enterprise compliance officer.
Generate a formal one-paragraph carbon audit report based on the calculation provided.
Mention GHG Protocol Scope 2, the emission factor used, and recommend one carbon reduction action."""
            },
            {
                "role": "user",
                "content": f"Generate compliance report for: {state['result']}"
            }
        ]
    )
    
    final_report = response.choices[0].message.content
    print(f"\nFINAL COMPLIANCE REPORT:\n{final_report}")
    print("="*50)
    return state

graph = StateGraph(AgentState)
graph.add_node("intake", intake_agent)
graph.add_node("auditor", auditor_agent)
graph.add_node("compliance", compliance_agent)