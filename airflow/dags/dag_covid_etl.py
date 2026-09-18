from datetime import datetime, timedelta
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
