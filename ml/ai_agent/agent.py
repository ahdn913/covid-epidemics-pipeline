import os
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
        report = f"Relatorio COVID-19 - {datetime.now().strftime('%d/%m/%Y')}\n"
        report += f"Paises: {r[0]}\nNovos casos: {r[1]}\nNovas mortes: {r[2]}\n"
        return report

if __name__ == '__main__':
    agent = EpidemiologyAgent()
    print(agent.generate_report())
