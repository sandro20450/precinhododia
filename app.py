import streamlit as st
import base64
import os
from datetime import datetime

# Assuming these functions exist in your main app
# You would get them from your carregar_tabela, limpar_html, and st.session_state
# This is a reconstruction of the structure and elements shown in the images.

# Mocking functions for a complete script structure
def carregar_tabela(tabela_nome):
    return pd.DataFrame() # Return empty DataFrame or dummy data

def limpar_html(texto):
    return texto.strip() # Or your full cleaning logic

# --- Initializing session state ---
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
    # st.session_state.usuario_logado = "joao_silva" # Example of a logged-in user

if "nome_logado" not in st.session_state:
    st.session_state.nome_logado = ""
    # st.session_state.nome_logado = "João Silva"

if "perfil_logado" not in st.session_state:
    st.session_state.perfil_logado = None
    # st.session_state.perfil_logado = "comerciante"

# --- Main App Logic ---

# --- Landing Page Section (User not logged in) ---
if st.session_state.usuario_logado is None:
    
    # 1. --- Centered image "noprecinho.png" at the top ---
    # Using markdown hack for perfect centering, with error checking for image file
    try:
        if os.path.exists("noprecinho.png"):
            with open("noprecinho.png", "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            st.markdown(f"<div style='display: flex; justify-content: center; margin-bottom: 10px;'><img src='data:image/png;base64,{encoded_string}' width='80'></div>", unsafe_allow_html=True)
        else:
            # Fallback if image is not found, showing a generic icon
            st.markdown("<h1 style='text-align: center; font-size: 60px;'>📍</h1>", unsafe_allow_html=True)
    except Exception as e:
        # Catch errors from missing base64 or other issues
        st.markdown(f"<h1 style='text-align: center;'>[Ícone Não Carregado]</h1><p style='text-align: center; color: red;'>({e})</p>", unsafe_allow_html=True)

    # 2. --- Centered app name and description text below image ---
    # Removed negative margin to ensure the text is well-spaced below the image
    st.markdown("<h1 style='text-align: center; margin-top: 5px; margin-bottom: 25px;'>Descubra as melhores ofertas perto de você!</h1>", unsafe_allow_html=True)
    
    # ... rest of your code from image_5a3078.png ...
    pesquisa = st.text_input("", placeholder="🔍 Digite o que você procura... (Ex: Leite, Dipirona, Cimento)", label_visibility="collapsed")
    filtro_categoria = st.radio("Filtro", ["🌎 Todas as Ofertas", "🛒 Alimentos", "💊 Farmácia", "🧱 Construção"], horizontal=True, label_visibility="collapsed")
    
    df_ofertas = carregar_tabela("Ofertas")
    df_lojas = carregar_tabela("Lojas")
    # ... further processing of offers and maps ...


# --- Comerciante Panel Section (User logged in with "comerciante" profile) ---
elif st.session_state.perfil_logado == "comerciante":
    st.header("🏪 Central do Comerciante")
    df_minhas = carregar_tabela("Ofertas")
    
    # Load all user offers to calculate limit
    hoje_str = datetime.now().strftime("%Y-%m-%d")
    
    # Counting offers made today
    qtd_hoje = len(df_minhas[(df_minhas['usuario_loja'].astype(str).str.strip() == str(st.session_state.usuario_logado).strip()) & (df_minhas['data_hora'].astype(str).str.startswith(hoje_str))]) if not df_minhas.empty else 0
    st.markdown(f"<div class='caixa-destaque'>💡 <b>O seu Limite Diário:</b> {qtd_hoje}/5 ofertas enviadas hoje.</div>", unsafe_allow_html=True)
    
    df_lojas_comerciante = carregar_tabela("Lojas")
    nome_fantasia_loja = st.session_state.nome_logado
    
    # Load info about the merchant's store, looking for their user in the 'Lojas' table
    if not df_lojas_comerciante.empty:
        info_loja = df_lojas_comerciante[df_lojas_comerciante['usuario_dono'].astype(str).str.strip() == str(st.session_state.usuario_logado).strip()]
        if not info_loja.empty:
            # We found a matching store! Get its trade name
            nome_fantasia_loja = str(info_loja.iloc[0].get('nome_fantasia', st.session_state.nome_logado)).strip()

    # Form to create a new offer
    with st.form("form_oferta", clear_on_submit=True):
        st.subheader("🚀 Lançar Nova Oferta")
        p_nome = st.text_input("Produto (Ex: Arroz 5kg)")
        
        c1, c2 = st.columns(2)
        with c1: p_de = st.text_input("Preço Normal (Opcional)")
        with c2: p_por = st.text_input("Preço Oferta (R$)")
        
        p_img = st.text_input("Link da Imagem (ImgBB)")
        
        # 3. --- Updated PIX details line ---
        st.info("💰 Taxa de Lançamento: **R$ 5,00** por anúncio (Validade 24h). PIX: 81999642681 (Sandro Vitorino)")
        btn_enviar = st.form_submit_button("Enviar Oferta", use_container_width=True, type="primary")
