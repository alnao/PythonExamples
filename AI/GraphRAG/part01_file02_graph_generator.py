import pandas as pd
from pyvis.network import Network
import os

# NOTA: LEGGERE PRIMA IL FILE part01_file02_graphrag.md


# Percorsi ai file corretti (assicurati che esistano dopo l'indexing)
path="./part01_file02_test/output/"
rel_path = os.path.join(path, 'relationships.parquet')
nodes_path = os.path.join(path, 'entities.parquet')

if not os.path.exists(rel_path) or not os.path.exists(nodes_path):
    print("Errore: Assicurati di aver completato l'indexing. File non trovati in output " , rel_path, " o ", nodes_path)
else:
    # Carichiamo i dati
    df_rel = pd.read_parquet(rel_path)
    df_nodes = pd.read_parquet(nodes_path)

    net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white", filter_menu=True)

    # Aggiungiamo i nodi con colori basati sul tipo (Person, Org, ecc.)
    color_map = {"person": "#ff4d4d", "organization": "#4d94ff", "geo": "#4dff88", "event": "#ffdb4d"}
    
    for _, node in df_nodes.iterrows():
        n_type = str(node['type']).lower()
        color = color_map.get(n_type, "#97c2fc")
        net.add_node(node['title'], label=node['title'], title=f"Tipo: {node['type']}", color=color)

    # Aggiungiamo le relazioni (archi)
    for _, rel in df_rel.iterrows():
        net.add_edge(rel['source'], rel['target'], value=rel['weight'], title=rel['description'])

    # Opzioni di fisica per rendere il grafo "vivo"
    net.force_atlas_2based()
    net.show("grafo_finale.html", notebook=False)
    print("Grafo generato con successo! Apri 'grafo_finale.html' nel browser.")