# COVID-19 Epidemiological Analysis Pipeline
> End-to-end data engineering and machine learning pipeline for COVID-19 data from the WHO.

![Python](https://img.shields.io/badge/python-3.10-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![Airflow](https://img.shields.io/badge/Airflow-2.8-red)
![dbt](https://img.shields.io/badge/dbt-1.7-orange)
![Docker](https://img.shields.io/badge/Docker-20.10-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Description

This project implements a **complete data pipeline** for ingesting, cleaning, transforming, and analyzing COVID-19 data published by the World Health Organization (WHO). It goes from raw CSV ingestion to interactive dashboards and machine learning forecasts.

The pipeline is built with the **modern data stack**: Airflow for orchestration, dbt for transformation, PostgreSQL + PostGIS for storage and geospatial analysis, and Streamlit for visualization. Machine learning models (Prophet, LSTM) generate short-term forecasts of cases and deaths.

**Use case**: A market-ready platform for health managers, hospitals, insurers, and pharmaceutical companies to monitor and forecast epidemic trends.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   WHO CSV   │────▶│   Airflow   │────▶│   PostgreSQL    │────▶│      dbt        │
│  (source)   │     │  (ETL/ELT)  │     │   + PostGIS     │     │  (transform)    │
└─────────────┘     └─────────────┘     └─────────────────┘     └─────────────────┘
                          │                                            │
                          ▼                                            ▼
                   ┌─────────────┐                             ┌─────────────────┐
                   │   MinIO     │                             │   Data Marts    │
                   │ (data lake) │                             │  (star schema)  │
                   └─────────────┘                             └─────────────────┘
                                                                          │
                          ┌───────────────────────────────────────────────┤
                          │                                               │
                          ▼                                               ▼
                   ┌─────────────┐                                  ┌─────────────┐
                   │  ML / AI    │                                  │  BI /       │
                   │  Prophet,   │                                  │  Streamlit, │
                   │  LSTM,      │                                  │  Tableau    │
                   │  LangChain  │                                  │             │
                   └─────────────┘                                  └─────────────┘
```

## Repository Structure

```
covid_epidemics/
├── airflow/dags/          # Airflow DAGs (ETL, ML training)
├── etl/src/               # Extract, transform, load scripts
├── dbt/models/            # dbt models (staging, marts, analysis)
├── ml/                    # Prophet, LSTM training scripts
├── ai_agent/              # LangChain agent for auto-reports
├── dashboards/            # Streamlit app
├── api/                   # FastAPI endpoints
├── sql/                   # DDL and advanced SQL queries
├── docker-compose.yml     # Full stack orchestration
└── docs/                  # Architecture, BI connections, product
```

## Requirements

- **Docker** ≥ 20.10
- **Docker Compose** ≥ 2.0
- **Python** ≥ 3.10 (optional, for local development)
- **OS**: Linux (Ubuntu) or WSL2

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ahdn913/covid_epidemics.git
cd covid_epidemics
```

2. Copy the environment file:
```bash
cp .env.example .env
```

3. Start the full stack:
```bash
docker-compose up -d --build
```

4. Access the services:

| Service | URL | Credentials |
|---|---|---|
| Airflow | http://localhost:8080 | `airflow` / `airflow` |
| Streamlit | http://localhost:8501 | — |
| FastAPI | http://localhost:8000/docs | — |
| MinIO | http://localhost:9001 | `minioadmin` / `minioadmin` |

5. Enable the DAG `epiwatch_etl` in Airflow and trigger it.

## Pipeline Steps

1. **Extract**: download WHO CSV to MinIO.
2. **Transform**: clean missing values, normalize country names, remove outliers.
3. **Load**: ingest into PostgreSQL (`raw_covid_cases`).
4. **dbt run**: build staging views and marts (star schema).
5. **dbt test**: validate data quality.
6. **ML training**: Prophet and LSTM models per country.
7. **Dashboard**: Streamlit app with KPIs, time series, and maps.

## Tech Stack

| Layer | Tools |
|---|---|
| **Language** | Python 3.10, SQL |
| **Orchestration** | Apache Airflow |
| **Transformation** | dbt |
| **Storage** | PostgreSQL 15, PostGIS, MinIO (S3-compatible) |
| **Machine Learning** | Prophet, TensorFlow/Keras (LSTM), Scikit-learn |
| **Visualization** | Streamlit, Plotly |
| **API** | FastAPI |
| **AI Agent** | LangChain, OpenAI |
| **DevOps** | Docker, Docker Compose, GitHub Actions |
| **Data Format** | CSV, HDF5 |

## Machine Learning

- **Prophet**: time-series forecasting with yearly/weekly seasonality.
- **LSTM**: deep learning for short-term prediction.
- **Evaluation**: MAE, RMSE, MAPE.

To train a model manually:
```bash
docker exec -it epiwatch_airflow_scheduler bash
python /opt/airflow/ml/train_prophet.py Brazil
```

## Geospatial Analysis

PostGIS extension enables spatial queries for incidence maps. Example:
```sql
SELECT country, ST_AsText(geometry), SUM(new_cases) AS total
FROM raw_covid_cases r
JOIN dim_country c ON r.country = c.country_name
GROUP BY country, geometry
ORDER BY total DESC;
```

## Advanced SQL

The `sql/advanced_queries.sql` file contains:
- 7-day moving averages with window functions.
- Country rankings with CTEs and `RANK()`.
- Daily growth rates with `LAG()`.
- Table partitioning by year.

## Testing

Run unit tests for the ETL:
```bash
cd etl
pytest tests/
```

## References

- WHO COVID-19 Dashboard: https://covid19.who.int/
- dbt Documentation: https://docs.getdbt.com/
- Airflow Documentation: https://airflow.apache.org/
- Prophet: https://facebook.github.io/prophet/

## License

MIT License — see `LICENSE` file for details.

## Contact

**Adriano Neves**
[GitHub](https://github.com/ahdn913) · [LinkedIn](https://www.linkedin.com/in/adriano-henrique-neves/) · [ORCID](https://orcid.org/0000-0002-8734-4660)
