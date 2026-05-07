import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium

# =============================================================================
# --- 1. CONFIGURAÇÕES GERAIS ---
# =============================================================================
st.set_page_config(page_title="No Precinho - Ofertas", page_icon="📍", layout="wide")

st.markdown("""
<style>
    footer { display: none !important; visibility: hidden !important; }
    .painel-login { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-top: 4px solid #ff4b4b; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# --- 2. CONEXÃO COM BANCO DE DADOS (GOOGLE SHEETS) ---
# =============================================================================
@st.cache_resource(ttl=3600, show_spinner=False)
def get_gspread_client():
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    return None

@st.cache_data(ttl=60, show_spinner=False)
def carregar_tabela(nome_aba):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_NoPrecinho").worksheet(nome_aba)
            dados = ws.get_all_values()
            if len(dados) <= 1:
                return pd.DataFrame(columns=dados[0] if dados else [])
            df = pd.DataFrame(dados[1:], columns=dados[0])
            df.columns = df.columns.astype(str).str.strip().str.lower()
            return df
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# =============================================================================
# --- 3. SISTEMA DE LOGIN ---
# =============================================================================
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = None
if "perfil_logado" not in st.session_state: st.session_state.perfil_logado = None

def fazer_login(usuario, senha):
    df_users = carregar_tabela("Usuarios")
    if not df_users.empty and 'usuario' in df_users.columns:
        user_row = df_users[(df_users['usuario'] == usuario) & (df_users['senha'] == senha)]
        if not user_row.empty:
            st.session_state.usuario_logado = user_row.iloc[0]['nome']
            st.session_state.perfil_logado = user_row.iloc[0]['perfil']
            st.success("✅ Acesso Concedido!")
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos.")
    else:
        st.warning("⚠️ Banco de dados vazio ou sem conexão.")

def fazer_logout():
    st.session_state.usuario_logado = None
    st.session_state.perfil_logado = None
    st.rerun()

# =============================================================================
# --- 4. BARRA LATERAL (MENU E LOGIN) ---
# =============================================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #ff4b4b;'>📍 NO PRECINHO</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    if st.session_state.usuario_logado is None:
        st.markdown("<div class='painel-login'>", unsafe_allow_html=True)
        st.markdown("### 🔐 Área do Comerciante")
        user_input = st.text_input("Usuário")
        pass_input = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            fazer_login(user_input, pass_input)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br><p style='font-size:0.8em; text-align:center;'>Quer anunciar? Fale conosco!</p>", unsafe_allow_html=True)
    else:
        st.success(f"Bem-vindo, {st.session_state.usuario_logado}!")
        if st.session_state.perfil_logado == "admin":
            st.button("👑 Painel Admin (Aprovações)", use_container_width=True)
        elif st.session_state.perfil_logado == "comerciante":
            st.button("🏪 Minha Loja e Ofertas", use_container_width=True)
            
        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            fazer_logout()

# =============================================================================
# --- 5. TELA PRINCIPAL (MAPA DO CLIENTE) ---
# =============================================================================
if st.session_state.usuario_logado is None:
    st.title("Descubra as melhores ofertas perto de você! 🛒")
    
    # Campo de busca rápida
    pesquisa = st.text_input("🔍 O que você procura hoje?", placeholder="Ex: Leite, Carne, Pão...")
    
    # Mapa
    m = folium.Map(location=[-8.1189, -35.2925], zoom_start=14)
    folium.Marker([-8.1189, -35.2925], popup="Leite Ninho - R$ 15,00", tooltip="Mercadinho do João").add_to(m)
    
    st_folium(m, width=1200, height=500, returned_objects=[])

elif st.session_state.perfil_logado == "admin":
    st.header("👑 Centro de Comando - Administração")
    st.info("Aqui você aprovará novos comerciantes e validará os pagamentos de ofertas.")

elif st.session_state.perfil_logado == "comerciante":
    st.header("🏪 Meu Painel de Ofertas")
    st.info("Aqui você poderá cadastrar seus produtos, colocar fotos e disparar para o mapa!")
