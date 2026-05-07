import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="No Precinho", layout="wide")
st.title("📍 NO PRECINHO - Ofertas da Região")

# Criar um mapa centralizado (Exemplo: Vitória de Santo Antão)
m = folium.Map(location=[-8.1189, -35.2925], zoom_start=14)

# Simular um Pin de oferta
folium.Marker(
    [-8.1189, -35.2925], 
    popup="Leite Ninho - R$ 15,00", 
    tooltip="Clique para ver a oferta"
).add_to(m)

st_folium(m, width=1200, height=500)
