import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import random
from matplotlib.collections import LineCollection
from mpl_toolkits.mplot3d.art3d import Line3DCollection

def create_network(network_type, num_nodes, **kwargs):
    if network_type == 'small_world':
        return nx.watts_strogatz_graph(num_nodes, kwargs.get('k', 4), kwargs.get('p', 0.1))
    elif network_type == 'scale_free':
        return nx.barabasi_albert_graph(num_nodes, kwargs.get('m', 2))
    elif network_type == 'geometric':
        return nx.random_geometric_graph(num_nodes, kwargs.get('radius', 0.125))
    elif network_type == 'spherical':
        radius = kwargs.get('radius', 0.5)
        vec = np.random.randn(num_nodes, 3)
        vec = vec / np.linalg.norm(vec, axis=1)[:, np.newaxis]
        G = nx.Graph()
        G.add_nodes_from(range(num_nodes))
        for i in range(num_nodes):
            for j in range(i+1, num_nodes):
                dot = np.clip(np.dot(vec[i], vec[j]), -1.0, 1.0)
                if np.arccos(dot) < radius:
                    G.add_edge(i, j)
        nx.set_node_attributes(G, {i: {'pos_3d': vec[i]} for i in range(num_nodes)})
        return G
    elif network_type == 'von_neumann':
        size = int(np.sqrt(num_nodes))
        return nx.grid_2d_graph(size, size, periodic=True)
    elif network_type == 'moore':
        size = int(np.sqrt(num_nodes))
        G = nx.grid_2d_graph(size, size, periodic=True)
        for x in range(size):
            for y in range(size):
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    G.add_edge((x,y), ((x+dx)%size, (y+dy)%size))
        return G
    elif network_type == 'triangular':
        size = int(np.sqrt(num_nodes))
        return nx.triangular_lattice_graph(size, size, periodic=True)
    elif network_type == 'honeycomb':
        size = int(np.sqrt(num_nodes))
        if size % 2 != 0: size += 1
        return nx.hexagonal_lattice_graph(size, size, periodic=True)
    return None

def simulate_percolation(network_type, num_nodes, removal_strategy='random', removal_fraction=0.1, return_absolute=False, **kwargs):
    G = create_network(network_type, num_nodes, **kwargs)
    if G is None or not list(nx.connected_components(G)):
        return 0
    initial_giant = len(max(nx.connected_components(G), key=len))
    nodes = list(G.nodes())
    if removal_strategy == 'random':
        nodes_to_remove = random.sample(nodes, int(len(nodes) * removal_fraction))
    else: 
        degrees = dict(G.degree())
        sorted_nodes = sorted(degrees, key=degrees.get, reverse=True)
        nodes_to_remove = sorted_nodes[:int(len(nodes) * removal_fraction)]
    G.remove_nodes_from(nodes_to_remove)
    if len(G.nodes()) == 0 or not list(nx.connected_components(G)):
        return 0
    final_giant = len(max(nx.connected_components(G), key=len))
    return final_giant if return_absolute else final_giant / initial_giant

def plot_percolation_curves(network_type, num_nodes, **kwargs):
    fractions = np.linspace(0, 0.8, 12)
    rand, targ = [], []
    for f in fractions:
        rand.append(np.mean([simulate_percolation(network_type, num_nodes, removal_fraction=f, **kwargs) for _ in range(10)]))
        targ.append(np.mean([simulate_percolation(network_type, num_nodes, removal_fraction=f, removal_strategy='targeted', **kwargs) for _ in range(10)]))
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(fractions*100, rand, 'bo-', label='Aleatoria')
    ax.plot(fractions*100, targ, 'rs-', label='Direcionada')
    ax.set_title(f'Threshold - {network_type}')
    ax.set_xlabel('Fracao Removida (%)')
    ax.set_ylabel('Fracao Percolada')
    ax.legend()
    ax.grid(True)
    return fig

def plot_giant_component_size(network_type, num_nodes, **kwargs):
    fractions = np.linspace(0, 0.8, 12)
    rand, targ = [], []
    for f in fractions:
        rand.append(np.mean([simulate_percolation(network_type, num_nodes, removal_fraction=f, return_absolute=True, **kwargs) for _ in range(10)]))
        targ.append(np.mean([simulate_percolation(network_type, num_nodes, removal_fraction=f, removal_strategy='targeted', return_absolute=True, **kwargs) for _ in range(10)]))
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(fractions*100, rand, 'bo-', label='Aleatoria')
    ax.plot(fractions*100, targ, 'rs-', label='Direcionada')
    ax.set_title(f'Componente Gigante - {network_type}')
    ax.set_xlabel('Fracao Removida (%)')
    ax.set_ylabel('Tamanho Absoluto')
    ax.legend()
    ax.grid(True)
    return fig

def monte_carlo_sir(G, beta, num_sim=50):
    nodes = list(G.nodes())
    N = len(nodes)
    if N == 0: return 0
    total_size = 0
    gamma = 1 - beta
    adj = {n: list(G.neighbors(n)) for n in nodes}
    for _ in range(num_sim):
        pz = random.choice(nodes)
        inf = {pz}
        rec = set()
        sus = set(nodes) - inf
        while inf:
            new_inf = set()
            new_rec = set()
            for node in inf:
                if random.random() < gamma:
                    new_rec.add(node)
                else:
                    for nb in adj[node]:
                        if nb in sus and random.random() < beta:
                            new_inf.add(nb)
            inf = (inf - new_rec) | new_inf
            rec |= new_rec
            sus -= new_inf
        total_size += len(rec)
    return total_size / (num_sim * N)

def plot_sir_threshold(network_type, num_nodes, **kwargs):
    betas = np.linspace(0.01, 0.99, 12)
    final_sizes = []
    G_base = create_network(network_type, num_nodes, **kwargs)
    for beta in betas:
        size = monte_carlo_sir(G_base, beta, num_sim=50)
        final_sizes.append(size)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(betas, final_sizes, 'go-', label='Tamanho Final (Monte Carlo)')
    ax.set_title(f'Threshold SIR - {network_type}')
    ax.set_xlabel(r'Taxa de Infeccao ($\beta$)')
    ax.set_ylabel('Fracao Infectada')
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(True)
    return fig

def plot_network_snapshot(network_type, num_nodes, removal_fraction=0.3, figsize=(10, 4), **kwargs):
    snap_nodes = min(num_nodes, 400)
    G = create_network(network_type, snap_nodes, **kwargs)
    
    if network_type == 'spherical':
        node_size = max(2, 100 / (snap_nodes ** 0.5))
        edge_alpha = 0.1
        edge_lw = 0.3
    else:
        node_size = max(5, 200 / (snap_nodes ** 0.5))
        edge_alpha = 0.35
        edge_lw = 0.6
    
    G_iso = G.copy()
    edges = list(G_iso.edges())
    num_edges_to_cut = int(len(edges) * removal_fraction)
    
    if num_edges_to_cut > 0 and edges:
        if network_type == 'scale_free':
            degrees = dict(G_iso.degree())
            edges.sort(key=lambda e: max(degrees[e[0]], degrees[e[1]]), reverse=True)
            edges_to_cut = edges[:num_edges_to_cut]
        else:
            edges_to_cut = random.sample(edges, num_edges_to_cut)
        G_iso.remove_edges_from(edges_to_cut)
    
    if list(nx.connected_components(G_iso)):
        giant = max(nx.connected_components(G_iso), key=len)
    else:
        giant = set()
        
    if network_type == 'spherical':
        pos = nx.get_node_attributes(G, 'pos_3d')
    elif network_type in ['triangular', 'honeycomb', 'geometric']:
        pos = nx.get_node_attributes(G, 'pos')
    elif network_type in ['von_neumann', 'moore']:
        pos = {n: n for n in G.nodes()} 
    else:
        pos = nx.spring_layout(G, seed=42)
        
    if network_type == 'spherical':
        fig = plt.figure(figsize=figsize)
        ax1 = fig.add_subplot(121, projection='3d')
        ax2 = fig.add_subplot(122, projection='3d')
        axes = [ax1, ax2]
    else:
        fig, axes = plt.subplots(1, 2, figsize=figsize)
        
    L0 = 0
    if list(G.edges()):
        u, v = list(G.edges())[0]
        L0 = np.linalg.norm(np.array(pos[u]) - np.array(pos[v]))
        
    for ax, graph, title in zip(axes, [G, G_iso], ["Rede Inicial", f"Rede Apos Isolamento {removal_fraction*100:.0f}%"]):
        ax.set_title(title)
        
        lines = []
        for u, v in graph.edges():
            dist = np.linalg.norm(np.array(pos[u]) - np.array(pos[v]))
            if L0 > 0 and dist > 2 * L0: continue
            if network_type == 'spherical':
                lines.append([(pos[u][0], pos[u][1], pos[u][2]), (pos[v][0], pos[v][1], pos[v][2])])
            else:
                lines.append([(pos[u][0], pos[u][1]), (pos[v][0], pos[v][1])])
                
        if network_type == 'spherical':
            lc = Line3DCollection(lines, colors='black', alpha=edge_alpha, linewidths=edge_lw)
            ax.add_collection3d(lc)
        else:
            lc = LineCollection(lines, colors='black', alpha=edge_alpha, linewidths=edge_lw)
            ax.add_collection(lc)
                
        x, y, z, colors = [], [], [], []
        for node in graph.nodes():
            x.append(pos[node][0])
            y.append(pos[node][1])
            if network_type == 'spherical':
                z.append(pos[node][2])
                
            if graph is G_iso:
                if node in giant:
                    colors.append('red')
                else:
                    colors.append('lightblue')
            else:
                colors.append('blue')
                
        if network_type == 'spherical':
            ax.scatter(x, y, z, s=node_size, c=colors, alpha=0.9)
            # ZOOM APLICADO AQUI
            ax.set_xlim([-1.1, 1.1])
            ax.set_ylim([-1.1, 1.1])
            ax.set_zlim([-1.1, 1.1])
            ax.dist = 7 # Zoom in digital
        else:
            ax.scatter(x, y, s=node_size, c=colors, alpha=0.9)
            
        ax.set_axis_off()
        
    plt.tight_layout()
    return fig