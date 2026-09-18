import os, sys, pickle, numpy as np
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
