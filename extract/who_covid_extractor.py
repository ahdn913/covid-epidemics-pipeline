import os, sys, logging, hashlib, requests, pandas as pd
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
    h = os.getenv('POSTGRES_HOST', 'postgres')
    port = os.getenv('POSTGRES_PORT', '5432')
    d = os.getenv('POSTGRES_DB', 'covid_epidemics')
    return create_engine(f"postgresql+psycopg2://{u}:{p}@{h}:{port}/{d}")

def generate_batch_id():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    h = hashlib.md5(ts.encode()).hexdigest()[:8]
    return f"batch_{ts}_{h}"

def extract_who_data():
    # Usando a base de dados publica da Our World in Data (nao bloqueia robos)
    url = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv"
    logger.info(f"Baixando: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, timeout=120, headers=headers)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text), on_bad_lines='skip')
    
    # Mapear as colunas da OWID para o formato que nosso banco espera
    df = df.rename(columns={
        'date': 'date_reported',
        'iso_code': 'country_code',
        'location': 'country',
        'new_cases': 'new_cases',
        'total_cases': 'cumulative_cases',
        'new_deaths': 'new_deaths',
        'total_deaths': 'cumulative_deaths'
    })
    
    # Selecionar apenas as colunas que precisamos
    cols = ['date_reported', 'country_code', 'country', 'new_cases', 'cumulative_cases', 'new_deaths', 'cumulative_deaths']
    df = df[cols]
    
    # A OWID nao tem a coluna who_region, vamos colocar vazio
    df['who_region'] = ''
    
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
        err = str(e)[:500]
        logger.error(f"Erro: {e}")
    end = datetime.now()
    
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO staging.etl_audit (batch_id,dag_run_id,task_id,start_time,end_time,status,records_extracted,records_loaded,error_message) VALUES (:b,:d,:t,:s,:e,:st,:re,:rl,:err)"),
            {'b':batch_id,'d':dag_run_id,'t':task_id,'s':start,'e':end,'st':status,'re':rec_ext,'rl':rec_load,'err':err})
    
    return {'batch_id':batch_id,'status':status,'records_extracted':rec_ext,'records_loaded':rec_load}

if __name__ == '__main__':
    r = run_extraction()
    print(f"Status: {r['status']}, Extraidos: {r['records_extracted']}")