import os, sys, pickle, numpy as np, pandas as pd
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
