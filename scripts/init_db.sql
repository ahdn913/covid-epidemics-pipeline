CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS marts_core;
CREATE SCHEMA IF NOT EXISTS marts_epidemiology;
CREATE SCHEMA IF NOT EXISTS marts_geospatial;
CREATE DATABASE airflow;
\c airflow
CREATE ROLE airflow_user WITH LOGIN PASSWORD 'airflow_password';
GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow_user;
\c covid_epidemics
GRANT USAGE ON SCHEMA staging TO airflow_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA staging TO airflow_user;
CREATE TABLE IF NOT EXISTS staging.who_covid_raw (
    date_reported DATE,
    country_code VARCHAR(10),  <--- MUDAR AQUI PARA 10
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
