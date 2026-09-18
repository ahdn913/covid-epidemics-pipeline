import os, sys, pickle
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
