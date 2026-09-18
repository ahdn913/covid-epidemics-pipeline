import sys, os
import streamlit as st
import matplotlib.pyplot as plt
import io
import pandas as pd
from matplotlib.ticker import MaxNLocator

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ml', 'src')))
from sir_model import fit_sir_to_country

st.title("Modelagem Matematica (SIR) e Previsao")
st.markdown("SIR Adaptativo (Filtro de Particulas) e Previsao.")

st.sidebar.markdown("### Tamanho dos Graficos")
img_width = st.sidebar.slider("Largura na Tela", 300, 1200, 700, step=50, key='sir_img_width')

def fig_to_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=400, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

country = st.selectbox("Selecione o Pais (Codigo ISO)", ['BRA', 'USA', 'IND', 'GBR', 'DEU'])

if st.button("Calibrar, Analisar e Prever"):
    with st.spinner("Rodando SIR Adaptativo (pode levar alguns segundos)..."):
        result = fit_sir_to_country(country, N=10000000) 
        
    if result:
        st.success("Analise concluida!")
        
        st.subheader("1. Casos Diarios vs Curva SIR Teorica")
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.plot(result['t_data'], result['I_data'], 'ro', markersize=2, alpha=0.2, label='Dados Reais (Bruto)')
        ax1.plot(result['t_data'], result['I_smooth'], 'r-', alpha=0.6, label='Dados Reais (Media 3 dias)')
        i_sim_smooth = pd.Series(result['I_sim']).rolling(window=7, min_periods=1, center=True).mean().fillna(1).values
        ax1.plot(result['t_sim'], i_sim_smooth, 'b-', linewidth=2, marker='', label='SIR Teorico (Renovacao)')
        ax1.set_xlabel('Dias')
        ax1.set_ylabel('Novos Casos')
        ax1.legend()
        ax1.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        ax1.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        st.image(fig_to_png(fig1), width=img_width)
        
        st.subheader("2. Casos Acumulados (Treino 500 dias + Previsao 20 dias)")
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(result['cum_t'], result['cum_data'], 'k-', label='Acumulado Real')
        ax2.plot(result['t_sim'], result['cum_teo'], 'b-', alpha=0.6, linewidth=2, label='Modelagem Teorica (Passado)')
        ax2.axvline(x=result['train_days'], color='gray', linestyle='--', label='Inicio Previsao (t=500)')
        ax2.plot(result['forecast_t'], result['forecast_data'], 'r--', linewidth=2, label='Previsao (20 dias)')
        err = result['forecast_err']
        ax2.fill_between(result['forecast_t'], result['forecast_data'] - err, result['forecast_data'] + err, color='red', alpha=0.2, label='IC 95%')
        ax2.set_xlabel('Dias')
        ax2.set_ylabel('Casos Acumulados')
        ax2.set_xlim(0, result['train_days'] + 20)
        ax2.legend()
        ax2.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        ax2.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        st.image(fig_to_png(fig2), width=img_width)
        
        st.subheader("3. Parametros Dependentes do Tempo (Metodo EpiEstim)")
        fig3, ax3 = plt.subplots(figsize=(10, 4))
        ax3.plot(result['t_dep'], result['R_t'], 'g-', label='$R_t$')
        ax3.fill_between(result['t_dep'], result['R_t'] - result['err_R_t'], result['R_t'] + result['err_R_t'], color='green', alpha=0.2, label='IC 95%')
        ax3.axhline(1.0, color='r', linestyle='--', label='$R_t = 1$')
        ax3.set_xlabel('Dias')
        ax3.set_ylabel('$R_t$')
        ax3.legend()
        ax3.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        ax3.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        st.image(fig_to_png(fig3), width=img_width)
        
        col1, col2 = st.columns(2)
        with col1:
            fig4, ax4 = plt.subplots(figsize=(5, 3))
            ax4.plot(result['t_dep'], result['beta_t'], 'b-')
            ax4.fill_between(result['t_dep'], result['beta_t'] - result['err_beta_t'], result['beta_t'] + result['err_beta_t'], color='blue', alpha=0.2)
            ax4.set_title('$\\beta_t$ (Transmissao)')
            ax4.set_xlabel('Dias')
            ax4.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
            ax4.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
            st.image(fig_to_png(fig4), width=int(img_width/2))
            
        with col2:
            fig5, ax5 = plt.subplots(figsize=(5, 3))
            ax5.plot(result['t_dep'], result['gamma_t'], 'm-')
            ax5.set_title('$\\gamma_t$ (Recuperacao - Fixo 0.14)')
            ax5.set_xlabel('Dias')
            ax5.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
            ax5.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
            st.image(fig_to_png(fig5), width=int(img_width/2))
            
        # NOVOS GRAFICOS: SIR ADAPTATIVO
        st.subheader("4. SIR Adaptativo - Novos Casos")
        fig6, ax6 = plt.subplots(figsize=(10, 4))
        ax6.plot(result['t_data'], result['I_smooth'], 'r-', alpha=0.6, label='Dados Reais')
        if len(result['raw_cloud_t']) > 0:
            ax6.scatter(result['raw_cloud_t'], result['raw_cloud_I'], c='dimgray', alpha=0.3, s=5, label='Nuvem Adaptativa (10%)')
            ax6.plot(result['mean_cloud_t'], result['mean_cloud_I'], 'b-', linewidth=2, label='Media da Nuvem')
        ax6.set_xlabel('Dias')
        ax6.set_ylabel('Novos Casos')
        ax6.legend()
        ax6.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        ax6.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        st.image(fig_to_png(fig6), width=img_width)
        
        st.subheader("5. SIR Adaptativo - Casos Acumulados")
        fig7, ax7 = plt.subplots(figsize=(10, 4))
        ax7.plot(result['cum_t'], result['cum_data'], 'k-', label='Acumulado Real')
        if len(result['raw_cloud_t']) > 0:
            ax7.scatter(result['raw_cloud_t'], result['raw_cloud_Cum'], c='dimgray', alpha=0.3, s=5, label='Nuvem Adaptativa (10%)')
            ax7.plot(result['mean_cloud_t'], result['mean_cloud_Cum'], 'b-', linewidth=2, label='Media da Nuvem')
        ax7.set_xlabel('Dias')
        ax7.set_ylabel('Casos Acumulados')
        ax7.legend()
        ax7.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        ax7.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        st.image(fig_to_png(fig7), width=img_width)
        
        if len(result['mean_cloud_t']) > 0:
            st.subheader("6. Parametros estimados pelo SIR Adaptativo (Limitado a 500 dias)")
            mask_500 = result['mean_cloud_t'] <= 500
            t_lim = result['mean_cloud_t'][mask_500]
            rt_lim = result['mean_cloud_Rt'][mask_500]
            b_lim = result['mean_cloud_b'][mask_500]
            g_lim = result['mean_cloud_g'][mask_500]
            
            fig8, axes8 = plt.subplots(3, 1, figsize=(10, 8))
            
            axes8[0].plot(t_lim, rt_lim, 'g-')
            axes8[0].axhline(1.0, color='r', linestyle='--')
            axes8[0].set_ylabel('$R_t$')
            axes8[0].set_xlim(0, 500)
            
            axes8[1].plot(t_lim, b_lim, 'b-')
            axes8[1].set_ylabel('$\\beta_t$')
            axes8[1].set_xlim(0, 500)
            
            axes8[2].plot(t_lim, g_lim, 'm-')
            axes8[2].set_ylabel('$\\gamma_t$')
            axes8[2].set_xlabel('Dias')
            axes8[2].set_xlim(0, 500)
            
            for ax in axes8:
                ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
                ax.grid(True)
                
            st.image(fig_to_png(fig8), width=img_width)
    else:
        st.error("Nao foi possivel calibrar para este pais.")