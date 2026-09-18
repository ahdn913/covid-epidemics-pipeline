import os, pandas as pd, streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Covid Epidemics", page_icon="🦠", layout="wide")

# String de conexão fixa (sem depender de .env)
url = "postgresql+psycopg2://adriano:3141@postgres:5432/covid_epidemics"

@st.cache_resource
def get_engine():
    return create_engine(url)

st.title("🦠 Covid Epidemics Dashboard")
st.markdown("Monitoramento de dados de COVID-19 da OMS")

try:
    with get_engine().connect() as conn:
        result = conn.execute(text("SELECT * FROM staging.who_covid_raw LIMIT 10"))
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    
    st.dataframe(df)
    st.success(f"{len(df)} registros carregados")
except Exception as e:
    st.warning(f"Aguardando dados. Execute o pipeline no Airflow. Erro: {e}")