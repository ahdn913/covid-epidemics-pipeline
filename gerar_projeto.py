import os

base = os.getcwd()

arquivos = {
    ".gitignore": """__pycache__/
*.py[cod]
.env
venv/
logs/
target/
*.pkl
*.h5
*.csv
""",

    ".env.example": """POSTGRES_USER=covid_epidemics_user
POSTGRES_PASSWORD=change_me_in_production
POSTGRES_DB=covid_epidemics
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__FERNET_KEY=placeholder
AIRFLOW__WEBSERVER__SECRET_KEY=placeholder
WHO_DATA_URL=https://covid19.who.int/WHO-COVID-19-global-data.csv
ML_MODEL_PATH=./ml/models/
""",

    "requirements.txt": """requests
pandas
numpy
psycopg2-binary
SQLAlchemy>=1.4.28,<2.0
dbt-core==1.7.4
dbt-postgres==1.7.4
scikit-learn
prophet
xgboost
streamlit
plotly
folium
streamlit-folium
fastapi
uvicorn
pydantic
python-dotenv
pytest
pytest-cov
geopandas
shapely
cryptography
""",

    "Makefile": """.PHONY: help start stop clean ps logs dbt-run

help:
\t@echo "Comandos: start stop clean ps logs dbt-run"

start:
\tdocker-compose up -d
\t@echo "Airflow: http://localhost:8080 (admin/admin)"
\t@echo "Dashboard: http://localhost:8501"
\t@echo "API: http://localhost:8000/docs"

stop:
\tdocker-compose down

clean:
\tdocker-compose down -v --rmi all

ps:
\tdocker-compose ps

logs:
\tdocker-compose logs -f

dbt-run:
\tcd transform/dbt_models && dbt run --profiles-dir . --target dev
""",

    "README.md": """# Covid Epidemics
Pipeline ETL de dados de COVID-19 da OMS com Airflow, dbt, PostgreSQL, ML e Dashboard.

## Como executar
cp .env.example .env
make start

Airflow: http://localhost:8080 (admin/admin)
Dashboard: http://localhost:8501
API: http://localhost:8000/docs
""",

    "scripts/init_db.sql": """CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS marts_core;
CREATE SCHEMA IF NOT EXISTS marts_epidemiology;
CREATE SCHEMA IF NOT EXISTS marts_geospatial;
CREATE DATABASE airflow;
\\c airflow
CREATE ROLE airflow_user WITH LOGIN PASSWORD 'airflow_password';
GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow_user;
\\c covid_epidemics
GRANT USAGE ON SCHEMA staging TO airflow_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA staging TO airflow_user;
CREATE TABLE IF NOT EXISTS staging.who_covid_raw (
    date_reported DATE,
    country_code VARCHAR(3),
    country VARCHAR(100),
    who_region VARCHAR(10),
    new_cases BIGINT,
    cumulative_cases BIGINT,
    new_deaths BIGINT,
    cumulative_deaths BIGINT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_id VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS idx_staging_date ON staging.who_covid_raw(date_reported);
CREATE INDEX IF NOT EXISTS idx_staging_country ON staging.who_covid_raw(country_code);
CREATE TABLE IF NOT EXISTS staging.etl_audit (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(50),
    dag_run_id VARCHAR(100),
    task_id VARCHAR(100),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20),
    records_extracted INTEGER,
    records_loaded INTEGER,
    error_message TEXT
);
""",

    "docker/Dockerfile.airflow": """FROM apache/airflow:2.8.1-python3.10
USER root
RUN apt-get update && apt-get install -y build-essential libpq-dev gdal-bin libgdal-dev && rm -rf /var/lib/apt/lists/*
USER airflow
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
""",

    "docker/Dockerfile.dashboard": """FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential libpq-dev gdal-bin libgdal-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY . /app
EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
""",

    "docker/Dockerfile.api": """FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY . /app
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",

    "docker-compose.yml": """version: '3.8'
services:
  postgres:
    image: postgis/postgis:15-3.4
    container_name: ce_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports: ["5432:5432"]
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks: [covid_net]

  airflow-init:
    build: { context: ., dockerfile: docker/Dockerfile.airflow }
    container_name: ce_airflow_init
    depends_on:
      postgres: { condition: service_healthy }
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__CORE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/airflow
      AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW__CORE__FERNET_KEY}
      AIRFLOW__WEBSERVER__SECRET_KEY: ${AIRFLOW__WEBSERVER__SECRET_KEY}
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./extract:/opt/airflow/extract
      - ./transform:/opt/airflow/transform
      - ./ml:/opt/airflow/ml
      - ./scripts:/opt/airflow/scripts
    entrypoint: /bin/bash
    command: ["-c", "airflow db migrate && airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@covid.com || true"]
    restart: on-failure
    networks: [covid_net]

  airflow-webserver:
    build: { context: ., dockerfile: docker/Dockerfile.airflow }
    container_name: ce_airflow_webserver
    depends_on:
      airflow-init: { condition: service_completed_successfully }
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__CORE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/airflow
      AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW__CORE__FERNET_KEY}
      AIRFLOW__WEBSERVER__SECRET_KEY: ${AIRFLOW__WEBSERVER__SECRET_KEY}
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./extract:/opt/airflow/extract
      - ./transform:/opt/airflow/transform
      - ./ml:/opt/airflow/ml
      - ./scripts:/opt/airflow/scripts
    ports: ["8080:8080"]
    command: webserver
    restart: always
    networks: [covid_net]

  airflow-scheduler:
    build: { context: ., dockerfile: docker/Dockerfile.airflow }
    container_name: ce_airflow_scheduler
    depends_on:
      airflow-init: { condition: service_completed_successfully }
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__CORE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/airflow
      AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW__CORE__FERNET_KEY}
      AIRFLOW__WEBSERVER__SECRET_KEY: ${AIRFLOW__WEBSERVER__SECRET_KEY}
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./extract:/opt/airflow/extract
      - ./transform:/opt/airflow/transform
      - ./ml:/opt/airflow/ml
      - ./scripts:/opt/airflow/scripts
    command: scheduler
    restart: always
    networks: [covid_net]

  dashboard:
    build: { context: ., dockerfile: docker/Dockerfile.dashboard }
    container_name: ce_dashboard
    depends_on:
      postgres: { condition: service_healthy }
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
    volumes:
      - ./dashboard:/app/dashboard
      - ./ml:/app/ml
      - ./api:/app/api
    ports: ["8501:8501"]
    command: streamlit run dashboard/app.py --server.port=8501 --server.address=0.0.0.0
    restart: always
    networks: [covid_net]

  api:
    build: { context: ., dockerfile: docker/Dockerfile.api }
    container_name: ce_api
    depends_on:
      postgres: { condition: service_healthy }
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
    volumes:
      - ./api:/app/api
      - ./ml:/app/ml
    ports: ["8000:8000"]
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
    restart: always
    networks: [covid_net]

volumes:
  postgres_data:
networks:
  covid_net:
    driver: bridge
""",

    "extract/__init__.py": "",
    "ml/src/__init__.py": "",
    "api/__init__.py": "",

    "extract/who_covid_extractor.py": '''import os, sys, logging, hashlib, requests, pandas as pd
from datetime import datetime
from io import StringIO
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_engine():
    u = os.getenv('POSTGRES_USER', 'covid_epidemics_user')
    p = os.getenv('POSTGRES_PASSWORD', 'change_me_in_production')
    h = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    d = os.getenv('POSTGRES_DB', 'covid_epidemics')
    return create_engine(f"postgresql+psycopg2://{u}:{p}@{h}:{port}/{d}")

def generate_batch_id():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    h = hashlib.md5(ts.encode()).hexdigest()[:8]
    return f"batch_{ts}_{h}"

def extract_who_data():
    url = os.getenv('WHO_DATA_URL', 'https://covid19.who.int/WHO-COVID-19-global-data.csv')
    logger.info(f"Baixando: {url}")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text))
    df.columns = [c.strip().lower() for c in df.columns]
    logger.info(f"Extraido: {len(df)} registros")
    return df

def load_to_staging(df, engine, batch_id):
    df = df.copy()
    df['loaded_at'] = datetime.now()
    df['batch_id'] = batch_id
    for c in ['new_cases','cumulative_cases','new_deaths','cumulative_deaths']:
        if c in df.columns:
            df[c] = df[c].fillna(0).astype('int64')
    if 'date_reported' in df.columns:
        df['date_reported'] = pd.to_datetime(df['date_reported']).dt.date
    df.to_sql('who_covid_raw', schema='staging', con=engine, if_exists='append', index=False, method='multi', chunksize=10000)
    return len(df)

def run_extraction(dag_run_id='manual', task_id='extract'):
    batch_id = generate_batch_id()
    start = datetime.now()
    engine = get_db_engine()
    rec_ext = 0
    rec_load = 0
    status = 'success'
    err = None
    try:
        df = extract_who_data()
        rec_ext = len(df)
        if df.empty:
            raise ValueError("DataFrame vazio")
        rec_load = load_to_staging(df, engine, batch_id)
    except Exception as e:
        status = 'failed'
        err = str(e)
        logger.error(f"Erro: {e}")
    end = datetime.now()
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO staging.etl_audit (batch_id,dag_run_id,task_id,start_time,end_time,status,records_extracted,records_loaded,error_message) VALUES (:b,:d,:t,:s,:e,:st,:re,:rl,:err)"),
            {'b':batch_id,'d':dag_run_id,'t':task_id,'s':start,'e':end,'st':status,'re':rec_ext,'rl':rec_load,'err':err})
        conn.commit()
    return {'batch_id':batch_id,'status':status,'records_extracted':rec_ext,'records_loaded':rec_load}

if __name__ == '__main__':
    r = run_extraction()
    print(f"Status: {r['status']}, Extraidos: {r['records_extracted']}")
''',

    "airflow/dags/dag_covid_etl.py": '''from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'covid_epidemics',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}
dag = DAG('covid_etl_pipeline', default_args=default_args, description='ETL COVID-19 OMS', schedule_interval='0 6 * * *', catchup=False, tags=['etl','covid'])

def extract_data(**ctx):
    import sys
    sys.path.insert(0, '/opt/airflow')
    from extract.who_covid_extractor import run_extraction
    r = run_extraction(dag_run_id=ctx['dag_run'].run_id, task_id='extract_data')
    if r['status'] != 'success':
        raise Exception(f"Falhou: {r.get('error','?')}")

t1 = PythonOperator(task_id='extract_data', python_callable=extract_data, dag=dag)
t2 = BashOperator(task_id='dbt_run', bash_command='cd /opt/airflow/transform/dbt_models && dbt run --profiles-dir . --target dev || echo "dbt pendente"', dag=dag)
t1 >> t2
''',

    "dashboard/app.py": '''import os, pandas as pd, streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv
load_dotenv()
st.set_page_config(page_title="Covid Epidemics", page_icon="🦠", layout="wide")

@st.cache_resource
def get_engine():
    u=os.getenv('POSTGRES_USER','covid_epidemics_user')
    p=os.getenv('POSTGRES_PASSWORD','change_me_in_production')
    h=os.getenv('POSTGRES_HOST','localhost')
    port=os.getenv('POSTGRES_PORT','5432')
    d=os.getenv('POSTGRES_DB','covid_epidemics')
    return create_engine(f"postgresql+psycopg2://{u}:{p}@{h}:{port}/{d}")

st.title("🦠 Covid Epidemics Dashboard")
st.markdown("Monitoramento de dados de COVID-19 da OMS")

try:
    df = pd.read_sql("SELECT * FROM staging.who_covid_raw LIMIT 10", get_engine())
    st.dataframe(df)
    st.success(f"{len(df)} registros carregados")
except Exception as e:
    st.warning(f"Aguardando dados. Execute o pipeline no Airflow. Erro: {e}")
''',

    "api/main.py": '''import os
from fastapi import FastAPI
from sqlalchemy import create_engine
from dotenv import load_dotenv
import pandas as pd
load_dotenv()
app = FastAPI(title="Covid Epidemics API")
url = f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST','localhost')}:{os.getenv('POSTGRES_PORT','5432')}/{os.getenv('POSTGRES_DB')}"
engine = create_engine(url)

@app.get("/")
async def root():
    return {"service": "Covid Epidemics API", "status": "online"}

@app.get("/api/v1/countries")
async def countries():
    df = pd.read_sql("SELECT DISTINCT country_code, country FROM staging.who_covid_raw ORDER BY country", engine)
    return df.to_dict('records')
''',

    "ml/ai_agent/agent.py": '''import os
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()

class EpidemiologyAgent:
    def __init__(self):
        u=os.getenv('POSTGRES_USER','covid_epidemics_user')
        p=os.getenv('POSTGRES_PASSWORD','change_me_in_production')
        h=os.getenv('POSTGRES_HOST','localhost')
        port=os.getenv('POSTGRES_PORT','5432')
        d=os.getenv('POSTGRES_DB','covid_epidemics')
        self.engine=create_engine(f"postgresql+psycopg2://{u}:{p}@{h}:{port}/{d}")

    def generate_report(self, days=7):
        with self.engine.connect() as conn:
            r = conn.execute(text(f"SELECT COUNT(DISTINCT country_code), SUM(new_cases), SUM(new_deaths) FROM staging.who_covid_raw WHERE date_reported >= CURRENT_DATE - INTERVAL '{days} days'")).fetchone()
        report = f"Relatorio COVID-19 - {datetime.now().strftime('%d/%m/%Y')}\\n"
        report += f"Paises: {r[0]}\\nNovos casos: {r[1]}\\nNovas mortes: {r[2]}\\n"
        return report

if __name__ == '__main__':
    agent = EpidemiologyAgent()
    print(agent.generate_report())
''',

    "ml/src/data_loader.py": '''import os, pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
load_dotenv()

def get_db_engine():
    u=os.getenv('POSTGRES_USER','covid_epidemics_user')
    p=os.getenv('POSTGRES_PASSWORD','change_me_in_production')
    h=os.getenv('POSTGRES_HOST','localhost')
    port=os.getenv('POSTGRES_PORT','5432')
    d=os.getenv('POSTGRES_DB','covid_epidemics')
    return create_engine(f"postgresql+psycopg2://{u}:{p}@{h}:{port}/{d}")

def load_covid_data(country_code=None, start_date='2020-01-03'):
    q = f"SELECT * FROM staging.who_covid_raw WHERE date_reported >= '{start_date}'"
    if country_code:
        q += f" AND country_code = '{country_code}'"
    return pd.read_sql(q, get_db_engine())
''',

    "ml/src/train_prophet.py": '''import os, sys, pickle
from prophet import Prophet
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.src.data_loader import load_covid_data

def train_all_models():
    df = load_covid_data()
    totals = df.groupby('country_code')['cumulative_cases'].max()
    countries = totals[totals > 1000].index.tolist()[:10]
    for c in countries:
        try:
            cdf = df[df['country_code']==c][['date_reported','new_cases']].rename(columns={'date_reported':'ds','new_cases':'y'})
            m = Prophet(weekly_seasonality=True, yearly_seasonality=True)
            m.fit(cdf)
            d = os.path.join(os.getenv('ML_MODEL_PATH','./ml/models/'),'prophet')
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d,f'prophet_{c}.pkl'),'wb') as f:
                pickle.dump(m, f)
            print(f"Modelo {c} treinado")
        except Exception as e:
            print(f"Erro {c}: {e}")

if __name__ == '__main__':
    train_all_models()
''',

    "ml/src/train_lstm.py": '''import os, sys, pickle, numpy as np
from sklearn.ensemble import GradientBoostingRegressor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.src.data_loader import load_covid_data

def train_all_models():
    df = load_covid_data()
    totals = df.groupby('country_code')['cumulative_cases'].max()
    countries = totals.nlargest(10).index.tolist()
    for c in countries:
        try:
            cdf = df[df['country_code']==c].sort_values('date_reported')
            v = cdf['new_cases'].values
            X, y = [], []
            for i in range(len(v)-21):
                X.append(v[i:i+14])
                y.append(v[i+14])
            X, y = np.array(X), np.array(y)
            m = GradientBoostingRegressor(n_estimators=100, max_depth=5)
            m.fit(X, y)
            d = os.path.join(os.getenv('ML_MODEL_PATH','./ml/models/'),'lstm')
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d,f'gb_{c}.pkl'),'wb') as f:
                pickle.dump(m, f)
            print(f"Modelo {c} treinado")
        except Exception as e:
            print(f"Erro {c}: {e}")

if __name__ == '__main__':
    train_all_models()
''',

    "ml/src/train_classifier.py": '''import os, sys, pickle, numpy as np, pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.src.data_loader import load_covid_data

def train_model():
    df = load_covid_data()
    df = df.sort_values(['country_code','date_reported'])
    df['lag1'] = df.groupby('country_code')['new_cases'].shift(1)
    df['lag7'] = df.groupby('country_code')['new_cases'].shift(7)
    df['ma7'] = df.groupby('country_code')['new_cases'].rolling(7).mean().reset_index(0,drop=True)
    df = df.dropna()
    df['outbreak'] = (df['new_cases'] > df['ma7']*1.5) & (df['ma7']>10)
    X = df[['lag1','lag7','ma7']]
    y = df['outbreak'].astype(int)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    m = xgb.XGBClassifier(n_estimators=100, max_depth=5)
    m.fit(X_tr, y_tr)
    d = os.path.join(os.getenv('ML_MODEL_PATH','./ml/models/'),'classifier')
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d,'outbreak.pkl'),'wb') as f:
        pickle.dump(m, f)
    print(classification_report(y_te, m.predict(X_te)))

if __name__ == '__main__':
    train_model()
''',

    "transform/dbt_models/dbt_project.yml": """name: 'covid_epidemics'
version: '1.0.0'
config-version: 2
profile: 'covid_epidemics'
model-paths: ["."]
target-path: "target"
models:
  covid_epidemics:
    staging: { +schema: staging, +materialized: view }
    intermediate: { +schema: intermediate, +materialized: table }
    marts:
      core: { +schema: marts_core, +materialized: table }
      epidemiology: { +schema: marts_epidemiology, +materialized: table }
""",

    "transform/dbt_models/profiles.yml": """covid_epidemics:
  target: dev
  outputs:
    dev:
      type: postgres
      host: "{{ env_var('POSTGRES_HOST', 'localhost') }}"
      user: "{{ env_var('POSTGRES_USER', 'covid_epidemics_user') }}"
      password: "{{ env_var('POSTGRES_PASSWORD', 'change_me_in_production') }}"
      port: "{{ env_var('POSTGRES_PORT', 5432) | int }}"
      dbname: "{{ env_var('POSTGRES_DB', 'covid_epidemics') }}"
      schema: public
      threads: 4
""",

    "transform/dbt_models/staging/sources.yml": """version: 2
sources:
  - name: staging
    schema: staging
    tables:
      - name: who_covid_raw
        columns:
          - name: date_reported
            tests: [not_null]
          - name: country_code
            tests: [not_null]
""",

    "transform/dbt_models/staging/stg_who_covid.sql": """{{ config(materialized='view', schema='staging') }}
SELECT
    md5(COALESCE(CAST(date_reported AS TEXT),'') || '_' || COALESCE(country_code,'')) AS covid_record_key,
    CAST(date_reported AS DATE) AS date_reported,
    UPPER(TRIM(country_code)) AS country_code,
    TRIM(country) AS country_name_raw,
    UPPER(TRIM(who_region)) AS who_region,
    COALESCE(new_cases,0) AS new_cases,
    COALESCE(cumulative_cases,0) AS cumulative_cases,
    COALESCE(new_deaths,0) AS new_deaths,
    COALESCE(cumulative_deaths,0) AS cumulative_deaths
FROM {{ source('staging','who_covid_raw') }}
""",

    "transform/dbt_models/intermediate/int_covid_cleaned.sql": """{{ config(materialized='table', schema='intermediate') }}
WITH dedup AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY date_reported, country_code ORDER BY loaded_at DESC) AS rn
    FROM {{ ref('stg_who_covid') }}
)
SELECT
    covid_record_key, date_reported, country_code,
    CASE country_name_raw
        WHEN 'United States of America' THEN 'United States'
        WHEN 'Russian Federation' THEN 'Russia'
        ELSE country_name_raw
    END AS country_name,
    who_region,
    CASE WHEN new_cases < 0 THEN 0 ELSE new_cases END AS new_cases,
    CASE WHEN cumulative_cases < 0 THEN 0 ELSE cumulative_cases END AS cumulative_cases,
    CASE WHEN new_deaths < 0 THEN 0 ELSE new_deaths END AS new_deaths,
    CASE WHEN cumulative_deaths < 0 THEN 0 ELSE cumulative_deaths END AS cumulative_deaths,
    ROUND(AVG(new_cases) OVER (PARTITION BY country_code ORDER BY date_reported ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS new_cases_7day_avg,
    ROUND(AVG(new_deaths) OVER (PARTITION BY country_code ORDER BY date_reported ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS new_deaths_7day_avg,
    CASE WHEN cumulative_cases > 0 THEN ROUND(cumulative_deaths::FLOAT / cumulative_cases::FLOAT * 100, 4) ELSE 0 END AS case_fatality_rate
FROM dedup WHERE rn = 1
""",

    "transform/dbt_models/marts/core/dim_country.sql": """{{ config(materialized='table', schema='marts_core') }}
SELECT DISTINCT
    md5(country_code) AS country_key,
    country_code,
    country_name,
    who_region,
    CASE who_region
        WHEN 'AFRO' THEN 'Africa'
        WHEN 'AMRO' THEN 'Americas'
        WHEN 'SEARO' THEN 'Asia'
        WHEN 'EURO' THEN 'Europe'
        WHEN 'EMRO' THEN 'Eastern Mediterranean'
        WHEN 'WPRO' THEN 'Western Pacific'
        ELSE 'Other'
    END AS continent
FROM {{ ref('int_covid_cleaned') }}
WHERE country_code IS NOT NULL
""",

    "transform/dbt_models/marts/core/fact_covid_daily.sql": """{{ config(materialized='table', schema='marts_core') }}
SELECT
    md5(COALESCE(CAST(c.date_reported AS TEXT),'') || '_' || COALESCE(c.country_code,'')) AS fact_key,
    TO_CHAR(c.date_reported, 'YYYYMMDD')::INTEGER AS date_key,
    md5(c.country_code) AS country_key,
    c.date_reported, c.country_code,
    c.new_cases, c.cumulative_cases, c.new_deaths, c.cumulative_deaths,
    c.case_fatality_rate, c.new_cases_7day_avg, c.new_deaths_7day_avg,
    GREATEST(c.cumulative_cases - c.cumulative_deaths, 0) AS estimated_active_cases,
    CASE WHEN c.new_cases > c.new_cases_7day_avg * 1.5 AND c.new_cases_7day_avg > 10 THEN TRUE ELSE FALSE END AS is_outbreak_day
FROM {{ ref('int_covid_cleaned') }} c
""",

    "transform/dbt_models/marts/epidemiology/mart_cases_by_country.sql": """{{ config(materialized='table', schema='marts_epidemiology') }}
SELECT
    d.country_code, d.country_name, d.who_region, d.continent,
    MAX(f.cumulative_cases) AS total_cases,
    MAX(f.cumulative_deaths) AS total_deaths,
    MAX(f.new_cases) AS peak_daily_cases,
    ROUND(AVG(f.new_cases),2) AS avg_daily_cases,
    CASE WHEN MAX(f.cumulative_cases) > 0 THEN ROUND(MAX(f.cumulative_deaths)::FLOAT / MAX(f.cumulative_cases)::FLOAT * 100, 4) ELSE 0 END AS overall_cfr,
    MIN(f.date_reported) AS first_case_date,
    MAX(f.date_reported) AS last_report_date,
    SUM(CASE WHEN f.is_outbreak_day THEN 1 ELSE 0 END) AS outbreak_days_count
FROM {{ ref('fact_covid_daily') }} f
JOIN {{ ref('dim_country') }} d ON md5(f.country_code) = d.country_key
GROUP BY d.country_code, d.country_name, d.who_region, d.continent
ORDER BY MAX(f.cumulative_cases) DESC
""",

    "tests/unit/test_extractor.py": """import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_batch_id():
    from extract.who_covid_extractor import generate_batch_id
    b = generate_batch_id()
    assert b.startswith('batch_')
""",
}

for caminho, conteudo in arquivos.items():
    caminho_completo = os.path.join(base, caminho)
    os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)
    with open(caminho_completo, 'w') as f:
        f.write(conteudo)
    print(f"Criado: {caminho}")

print("\\nTodos os arquivos foram criados!")