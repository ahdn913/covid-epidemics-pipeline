import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from scipy.integrate import odeint
import random

DB_URL = "postgresql+psycopg2://adriano:3141@postgres:5432/covid_epidemics"

def deriv(y, t, N, beta, gamma):
    S, I, R = y
    dSdt = -beta * S * I / N
    dIdt = beta * S * I / N - gamma * I
    dRdt = gamma * I
    return dSdt, dIdt, dRdt

def fit_sir_to_country(country_code, N=None):
    # Populacoes reais (em pessoas)
    populations = {
        'BRA': 214000000,
        'USA': 331000000,
        'IND': 1380000000,
        'GBR': 67000000,
        'DEU': 83000000
    }
    
    # Usa a populacao real do pais, se existir. Senao, usa um fallback.
    N = populations.get(country_code, 10000000)
    
    engine = create_engine(DB_URL)
    query = text("""
        SELECT date_reported, SUM(new_cases) as new_cases, MAX(cumulative_cases) as cumulative_cases
        FROM staging.who_covid_raw
        WHERE country_code = :country AND cumulative_cases > 0
        GROUP BY date_reported
        ORDER BY date_reported
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'country': country_code})
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    
    if df.empty:
        return None

    t_data = np.arange(1, len(df) + 1)
    I_data = df['new_cases'].values.astype(float)
    cum_data = df['cumulative_cases'].values.astype(float)
    
    if len(t_data) < 30:
        return None

    gamma = 0.14  # ~7 dias
    T_g = 5       # Tempo de Geracao
    window = 7    # Janela de soma (EpiEstim)
    
    # 1. Calculo do R_t (EpiEstim)
    R_t_raw = np.ones(len(I_data))
    for t in range(window + T_g, len(I_data)):
        recent_sum = np.sum(I_data[t-window+1 : t+1])
        past_sum = np.sum(I_data[t-window-T_g+1 : t-T_g+1])
        if past_sum > 0:
            R_t_raw[t] = recent_sum / past_sum
        else:
            R_t_raw[t] = 1.0
            
    R_t_plot = pd.Series(R_t_raw).rolling(window=5, min_periods=1, center=True).mean().fillna(1).values
    R_t_plot = np.clip(R_t_plot, 0.1, 5.0)
    beta_t_plot = R_t_plot * gamma
    
    err_R_t = 0.15 * R_t_plot
    err_beta_t = 0.15 * beta_t_plot

    t_dep = t_data[window+T_g:]
    R_t_out = R_t_plot[window+T_g:]
    beta_t_out = beta_t_plot[window+T_g:]
    err_R_t_out = err_R_t[window+T_g:]
    err_beta_t_out = err_beta_t[window+T_g:]

    # 2. Simulacao Teorica (Renovacao Exata)
    I_teo = np.zeros(len(t_data))
    for t in range(len(t_data)):
        if t < T_g:
            I_teo[t] = I_data[t]
        else:
            idx = t - T_g
            rt = np.clip(R_t_raw[idx], 0.1, 5.0)
            I_teo[t] = rt * I_data[t - T_g]
            
    I_sim = pd.Series(I_teo).rolling(window=3, min_periods=1, center=True).mean().fillna(1).values
    cum_teo = np.cumsum(I_sim)
    cum_teo = np.minimum(cum_teo, N)

    # 3. Previsao 20 dias (Treino 500 dias)
    train_days = min(500, len(t_data))
    t_train = t_data[:train_days]
    y_train = cum_data[:train_days]
    
    t_fit = t_train[-30:]
    y_fit = y_train[-30:]
    y_fit_log = np.log(y_fit + 1)
    coeffs = np.polyfit(t_fit, y_fit_log, 2)
    p = np.poly1d(coeffs)
    
    t_forecast = np.arange(train_days, train_days + 20)
    cum_forecast = np.exp(p(t_forecast))
    anchor_diff = y_train[-1] - cum_forecast[0]
    cum_forecast = cum_forecast + anchor_diff
    
    residuals = y_fit - np.exp(p(t_fit))
    err = 1.96 * np.std(residuals)

    cum_smooth = pd.Series(cum_data).rolling(window=7, min_periods=1).mean().values

    # 4. SIR Adaptativo (Filtro de Particulas)
    I0_grid = max(np.sum(I_data[:7]), 50)
    S0_grid = N - I0_grid
    R0_grid = 0
    
    states = [(S0_grid, I0_grid, R0_grid)]
    
    cloud_t, cloud_I, cloud_Cum, cloud_b, cloud_g, cloud_rt = [], [], [], [], [], []
    
    I_smooth_grid = pd.Series(I_data).rolling(3).mean().fillna(1).values
    cum_smooth_grid = pd.Series(cum_data).rolling(7).mean().fillna(1).values
    
    betas = np.linspace(0.02, 0.75, 20)
    gammas = np.linspace(0.005, 0.55, 20)
    
    for t in range(len(I_data)):
        if I_smooth_grid[t] < 10: 
            continue
            
        next_states = []
        for S_prev, I_prev, R_prev in states:
            for b in betas:
                for g in gammas:
                    # Passo SIR (Euler 1 dia)
                    new_inf = b * S_prev * I_prev / N
                    new_rec = g * I_prev
                    
                    S_t = S_prev - new_inf
                    I_t = I_prev + new_inf - new_rec
                    R_t = R_prev + new_rec
                    
                    # Margem de erro 10% + tolerancia absoluta de 20 casos
                    if abs(new_inf - I_smooth_grid[t]) <= max(0.10 * I_smooth_grid[t], 20):
                        next_states.append((S_t, I_t, R_t))
                        cloud_t.append(t)
                        cloud_I.append(new_inf)
                        cloud_Cum.append(N - S_t)
                        cloud_b.append(b)
                        cloud_g.append(g)
                        cloud_rt.append(b/g)
                        
        if not next_states:
            # Mecanismo de Revival Corrigido
            S_t = max(0, N - cum_smooth_grid[t])
            past_7 = I_data[max(0, t-6):t+1]
            I_t = max(np.sum(past_7), 50)
            R_t = cum_smooth_grid[t] - I_t
            if R_t < 0: R_t = 0
            next_states.append((S_t, I_t, R_t))
        else:
            if len(next_states) > 200:
                next_states = random.sample(next_states, 200)
                
        states = next_states
                
    df_cloud = pd.DataFrame({'t': cloud_t, 'I': cloud_I, 'Cum': cloud_Cum, 'b': cloud_b, 'g': cloud_g, 'Rt': cloud_rt})
    mean_cloud = df_cloud.groupby('t').mean().reset_index()

    return {
        'country': country_code,
        't_data': t_data, 'I_data': I_data, 'I_smooth': pd.Series(I_data).rolling(3).mean().fillna(1).values,
        't_sim': t_data, 'I_sim': I_sim, 'cum_teo': cum_teo, 
        'cum_t': t_data, 'cum_data': cum_smooth, 
        'train_days': train_days,
        'forecast_t': t_forecast, 'forecast_data': cum_forecast, 'forecast_err': err,
        't_dep': t_dep, 'beta_t': beta_t_out, 'err_beta_t': err_beta_t_out,
        'gamma_t': np.full(len(beta_t_out), gamma), 
        'R_t': R_t_out, 'err_R_t': err_R_t_out,
        'raw_cloud_t': cloud_t, 'raw_cloud_I': cloud_I, 'raw_cloud_Cum': cloud_Cum,
        'mean_cloud_t': mean_cloud['t'].values if not mean_cloud.empty else [],
        'mean_cloud_I': mean_cloud['I'].values if not mean_cloud.empty else [],
        'mean_cloud_Cum': mean_cloud['Cum'].values if not mean_cloud.empty else [],
        'mean_cloud_Rt': mean_cloud['Rt'].values if not mean_cloud.empty else [],
        'mean_cloud_b': mean_cloud['b'].values if not mean_cloud.empty else [],
        'mean_cloud_g': mean_cloud['g'].values if not mean_cloud.empty else []
    }