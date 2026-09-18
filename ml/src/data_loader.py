import os, pandas as pd
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
