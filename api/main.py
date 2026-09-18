import os
from fastapi import FastAPI
from sqlalchemy import create_engine, text

app = FastAPI(title="Covid Epidemics API")

# String de conexão fixa (sem depender de .env)
url = "postgresql+psycopg2://adriano:3141@postgres:5432/covid_epidemics"
engine = create_engine(url)

@app.get("/")
async def root():
    return {"service": "Covid Epidemics API", "status": "online"}

@app.get("/api/v1/countries")
async def countries():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT country_code, country FROM staging.who_covid_raw ORDER BY country"))
        rows = result.fetchall()
        return [{"country_code": row[0], "country": row[1]} for row in rows]