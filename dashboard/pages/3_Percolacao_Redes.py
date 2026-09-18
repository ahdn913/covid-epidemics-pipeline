import sys, os
import streamlit as st
import matplotlib.pyplot as plt
import io

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ml', 'src')))
from percolation_model import plot_percolation_curves, plot_giant_component_size, plot_sir_threshold, plot_network_snapshot

st.title("Percolacao em Redes Complexas")
st.markdown("Simulacao da propagacao epidemica sob a otica da teoria de percolacao.")

st.sidebar.markdown("### Parametros Gerais")
num_nodes = st.sidebar.slider("Numero de Nos na Rede", 100, 2500, 400, step=50, key='perc_num_nodes')
beta = st.sidebar.slider("Taxa de Infeccao (Beta)", 0.0, 1.0, 0.5, 0.05, key='perc_beta')
gamma = st.sidebar.slider("Taxa de Recuperacao (Gamma)", 0.0, 1.0, 0.1, 0.05, key='perc_gamma')
removal_frac = st.sidebar.slider("Fracao de Conexoes Cortadas (Isolamento)", 0.0, 1.0, 0.3, 0.05, key='perc_removal')

st.sidebar.markdown("### Tamanho dos Graficos")
img_width = st.sidebar.slider("Largura na Tela", 300, 1200, 600, step=50, key='perc_img_width')

T = beta / (beta + gamma) if (beta + gamma) > 0 else 0
R0 = beta / gamma if gamma > 0 else float('inf')

st.markdown(f"""
**Parametros Atuais:**
- **Transmissibilidade ($T$):** {T:.4f}
- **Numero de reproducao basico ($R_0$):** {R0:.2f}
""")

tab1, tab2, tab3, tab4 = st.tabs(["Classicas", "Esferica", "Quadradas", "Hexagonais"])

def fig_to_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=400, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

# CACHE: Evita recalcular simulacoes pesadas ao mover o slider de isolamento
@st.cache_data
def cached_percolation(network_type, num_nodes, **params):
    return fig_to_png(plot_percolation_curves(network_type, num_nodes, **params))

@st.cache_data
def cached_giant_component(network_type, num_nodes, **params):
    return fig_to_png(plot_giant_component_size(network_type, num_nodes, **params))

@st.cache_data
def cached_sir_threshold(network_type, num_nodes, **params):
    return fig_to_png(plot_sir_threshold(network_type, num_nodes, **params))

def render_network_tab(network_type, label, **params):
    st.markdown(f"**Rede {label}**")
    with st.spinner(f"Calculando {label}..."):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Threshold de Percolacao")
            st.image(cached_percolation(network_type, num_nodes, **params), width=img_width)
            st.subheader("Threshold SIR (Monte Carlo)")
            st.image(cached_sir_threshold(network_type, num_nodes, **params), width=img_width)
        with col2:
            st.subheader("Tamanho Absoluto da Componente Gigante")
            st.image(cached_giant_component(network_type, num_nodes, **params), width=img_width)
            st.subheader("Snapshot da Rede")
            st.image(fig_to_png(plot_network_snapshot(network_type, num_nodes, removal_fraction=removal_frac, **params)), width=int(img_width*1.2))

with tab1:
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Small-World", "Scale-Free", "Geometrica"])
    with sub_tab1:
        render_network_tab('small_world', 'Small-World', k=st.slider("k", 2, 10, 4, key='sw_k'), p=st.slider("p", 0.0, 1.0, 0.1, key='sw_p'))
    with sub_tab2:
        render_network_tab('scale_free', 'Scale-Free', m=st.slider("m", 1, 5, 2, key='sf_m'))
    with sub_tab3:
        render_network_tab('geometric', 'Geometrica', radius=st.slider("r", 0.05, 0.5, 0.125, key='geo_r'))

with tab2:
    render_network_tab('spherical', 'Esfera 3D', radius=st.slider("Raio Geodesico (rad)", 0.1, 2.0, 0.8, key='sph_r'))

with tab3:
    sub_tab1, sub_tab2 = st.tabs(["Von Neumann", "Moore"])
    with sub_tab1:
        render_network_tab('von_neumann', 'Von Neumann')
    with sub_tab2:
        render_network_tab('moore', 'Moore')

with tab4:
    sub_tab1, sub_tab2 = st.tabs(["Triangular", "Honeycomb"])
    with sub_tab1:
        render_network_tab('triangular', 'Triangular')
    with sub_tab2:
        render_network_tab('honeycomb', 'Honeycomb')