"""
ONE-TIME SETUP SCRIPT
Your UAE emission factors into Qdrant as vector embeddings.
Run this once. After this, your app.py queries Qdrant instead of a dictionary.
"""

import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from openai import OpenAI

# ─── CONNECT ──────────────────────────────────────────────────────────────
qdrant = QdrantClient(
    url=st.secrets["QDRANT_URL"],
    api_key=st.secrets["QDRANT_API_KEY"],
)

openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

COLLECTION_NAME = "uae_emission_factors"

# ─── YOUR UAE EMISSION FACTORS DATABASE ──────────────────────────────────
# Each entry has rich descriptive text so semantic search can match
# loosely worded queries like "Dubai electricity" or "MWh grid power"
EMISSION_FACTORS_DATA = [
    {
        "source": "DEWA",
        "description": "Dubai Electricity and Water Authority grid electricity, Dubai emirate power supply, DEWA electricity consumption, Dubai utility power",
        "factor": 0.400,
        "unit": "kg CO2/kWh",
        "scope": "Scope 2",
    },
    {
        "source": "EWEC",
        "description": "Emirates Water and Electricity Company grid electricity, Abu Dhabi power supply, EWEC electricity, federal UAE grid power",
        "factor": 0.380,
        "unit": "kg CO2/kWh",
        "scope": "Scope 2",
    },
    {
        "source": "ADDC",
        "description": "Abu Dhabi Distribution Company grid electricity, ADDC power supply, Abu Dhabi emirate electricity distribution",
        "factor": 0.390,
        "unit": "kg CO2/kWh",
        "scope": "Scope 2",
    },
    {
        "source": "SEWA",
        "description": "Sharjah Electricity and Water Authority grid electricity, SEWA power supply, Sharjah emirate electricity",
        "factor": 0.395,
        "unit": "kg CO2/kWh",
        "scope": "Scope 2",
    },
    {
        "source": "Diesel",
        "description": "diesel fuel combustion, backup generator diesel, site diesel consumption, diesel litres burned, generator fuel",
        "factor": 2.680,
        "unit": "kg CO2/litre",
        "scope": "Scope 1",
    },
    {
        "source": "Gas",
        "description": "natural gas combustion, LPG gas, site gas consumption, gas litres burned, cooking gas, heating gas",
        "factor": 2.040,
        "unit": "kg CO2/litre",
        "scope": "Scope 1",
    },
    {
        "source": "Petrol",
        "description": "petrol fuel, gasoline combustion, vehicle fleet petrol, company car fuel consumption",
        "factor": 2.310,
        "unit": "kg CO2/litre",
        "scope": "Scope 1",
    },
    {
        "source": "Water",
        "description": "desalinated water consumption, water usage, municipal water supply, water treatment emissions",
        "factor": 0.344,
        "unit": "kg CO2/m3",
        "scope": "Scope 3",
    },
]


def get_embedding(text: str) -> list:
    """Convert text into a vector using OpenAI's embedding model"""
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def setup_collection():
    """Create the Qdrant collection if it doesn't exist"""
    collections = qdrant.get_collections().collections
    existing_names = [c.name for c in collections]

    if COLLECTION_NAME in existing_names:
        print(f"Collection '{COLLECTION_NAME}' already exists. Deleting and recreating...")
        qdrant.delete_collection(COLLECTION_NAME)

    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )
    print(f"Collection '{COLLECTION_NAME}' created.")


def load_emission_factors():
    """Embed and upload every emission factor into Qdrant"""
    points = []

    for i, item in enumerate(EMISSION_FACTORS_DATA):
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
        print(f"Embedded: {item['source']}")

    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"\n✓ Uploaded {len(points)} emission factors to Qdrant.")


if __name__ == "__main__":
    setup_collection()
    load_emission_factors()
    print("\n✓ Qdrant setup complete. Your vector database is ready.")
