import streamlit as st
import pandas as pd
from datetime import datetime
import time
import gspread
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium

# =============================================================================
# --- 1. CONFIGURAÇÕES GERAIS E CSS CUSTOMIZADO ---
# =============================================================================
st.set_page_config(page_title="No Precinho - Ofertas", page_icon="📍", layout="wide")

st.markdown("""
<style>
    footer { display: none !important; visibility: hidden !important; }
    
    /* CAIXA DE PESQUISA FLUTUANTE COM SOMBRA */
    div[data-testid="stTextInput"] {
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        border-radius: 12px;
        padding: 5px;
        background-color: white;
        border: 1px solid #eee;
        margin-bottom: 20px;
    }
    
    .painel-login { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-top: 4px solid #ff4b4b; }
    .caixa-destaque { background-color: #e6f7ff; padding: 15px; border-radius: 8px; border-left: 5px solid #0066cc; margin-bottom: 20px;}
    
    /* Estilo para a lista de produtos no Popup */
    .item-oferta { border-bottom: 1px solid #eee; padding: 10px 0; }
    .item-oferta:last-child { border-bottom: none; }
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

def salvar_nova_oferta(usuario_loja, produto, preco_de, preco_por, link_imagem):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_NoPrecinho").worksheet("Ofertas")
            id_oferta = f"OFT-{int(time.time())}"
            data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            nova_linha = [id_oferta, usuario_loja, produto, preco_de, preco_por, link_imagem, data_hora, "pendente"]
            ws.append_row(nova_linha)
            st.cache_data.clear()
            return True
    except Exception as e:
        st.error(f"Erro ao comunicar com o servidor: {e}")
        return False

def sincronizar_aba_completa(nome_aba, df_editado):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_NoPrecinho").worksheet(nome_aba)
            df_editado = df_editado.fillna("")
            dados_lista = [df_editado.columns.values.tolist()] + df_editado.values.tolist()
            ws.clear()
            ws.update(values=dados_lista, range_name="A1")
            st.cache_data.clear()
            return True
    except Exception as e:
        st.error(f"Erro ao sincronizar a aba {nome_aba}: {e}")
        return False

# =============================================================================
# --- 3. SISTEMA DE LOGIN ---
# =============================================================================
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = None
if "perfil_logado" not in st.session_state: st.session_state.perfil_logado = None
if "nome_logado" not in st.session_state: st.session_state.nome_logado = None

def fazer_login(usuario, senha):
    df_users = carregar_tabela("Usuarios")
    if not df_users.empty and 'usuario' in df_users.columns:
        user_row = df_users[(df_users['usuario'].astype(str).str.strip() == str(usuario).strip()) & (df_users['senha'].astype(str).str.strip() == str(senha).strip())]
        if not user_row.empty:
            status_user = str(user_row.iloc[0].get('status', '')).strip().lower()
            if status_user == 'aprovado':
                st.session_state.usuario_logado = str(user_row.iloc[0]['usuario']).strip()
                st.session_state.nome_logado = str(user_row.iloc[0].get('nome', '')).strip()
                st.session_state.perfil_logado = str(user_row.iloc[0].get('perfil', '')).strip().lower()
                st.success("✅ Acesso Concedido!")
                st.rerun()
            else:
                st.warning("⏳ O seu cadastro está em análise pela nossa equipa. Aguarde a aprovação.")
        else:
            st.error("❌ Usuário ou senha incorretos.")
    else:
        st.warning("⚠️ Banco de dados vazio ou sem conexão.")

def fazer_logout():
    st.session_state.usuario_logado = None
    st.session_state.perfil_logado = None
    st.session_state.nome_logado = None
    st.cache_data.clear()
    st.rerun()

# =============================================================================
# --- 4. BARRA LATERAL ---
# =============================================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #ff4b4b;'>📍 NO PRECINHO</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    if st.session_state.usuario_logado is None:
        st.markdown("<div class='painel-login'>", unsafe_allow_html=True)
        st.markdown("### 🔐 Área do Comerciante")
        user_input = st.text_input("Usuário", key="login_user")
        pass_input = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Entrar", type="primary", use_container_width=True):
            fazer_login(user_input, pass_input)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.success(f"👋 Olá, {st.session_state.nome_logado}!")
        if st.session_state.perfil_logado == "admin": st.button("👑 Painel Admin", use_container_width=True)
        elif st.session_state.perfil_logado == "comerciante": st.button("🏪 Lançar Oferta", use_container_width=True)
        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True): fazer_logout()

# =============================================================================
# --- 5. TELA PRINCIPAL (FRONT-END) ---
# =============================================================================
if st.session_state.usuario_logado is None:
    st.title("Descubra as melhores ofertas perto de você! 🛒")
    
    # Campo de busca tático (com o estilo flutuante aplicado via CSS acima)
    pesquisa = st.text_input("", placeholder="🔍 Digite o que você procura... (Ex: Leite, Arroz, Fralda)", label_visibility="collapsed")
    
    df_ofertas = carregar_tabela("Ofertas")
    df_lojas = carregar_tabela("Lojas")
    
    m = folium.Map(location=[-8.1189, -35.2925], zoom_start=14)
    
    if not df_ofertas.empty and not df_lojas.empty:
        # Filtra apenas ofertas aprovadas
        ofertas_ativas = df_ofertas[df_ofertas['status_pagamento'].astype(str).str.strip().str.lower() == 'aprovado']
        
        if pesquisa:
            ofertas_ativas = ofertas_ativas[ofertas_ativas['produto'].astype(str).str.contains(pesquisa, case=False, na=False)]
        
        # --- LÓGICA DE AGRUPAMENTO: Uma Loja -> Múltiplas Ofertas ---
        # Pegamos a lista de lojas únicas que têm ofertas ativas
        lojas_com_oferta = ofertas_ativas['usuario_loja'].unique()
        
        for usr_loja in lojas_com_oferta:
            loja_info = df_lojas[df_lojas['usuario_dono'].astype(str).str.strip() == usr_loja.strip()]
            
            if not loja_info.empty:
                try:
                    lat = float(str(loja_info.iloc[0].get('latitude', '-8.1189')).replace("'", "").strip())
                    lon = float(str(loja_info.iloc[0].get('longitude', '-35.2925')).replace("'", "").strip())
                    nome_loja = loja_info.iloc[0].get('nome_fantasia', 'Loja')
                    zap_loja = str(loja_info.iloc[0].get('whatsapp', '')).strip()
                    
                    # Filtra todas as ofertas aprovadas deste comerciante específico
                    produtos_da_loja = ofertas_ativas[ofertas_ativas['usuario_loja'] == usr_loja]
                    
                    # Início do Balão (Popup)
                    html_popup = f"<div style='width:240px; font-family:sans-serif;'>"
                    html_popup += f"<h3 style='color:#0066cc; margin:0 0 10px 0; text-align:center; border-bottom:2px solid #0066cc;'>{nome_loja}</h3>"
                    
                    # Loop para listar cada produto dentro do mesmo balão
                    for _, row in produtos_da_loja.iterrows():
                        prod = row.get('produto', '')
                        p_de = row.get('preco_de', '')
                        p_por = row.get('preco_por', '')
                        img = row.get('link_imagem', '')
                        
                        html_popup += f"<div class='item-oferta'>"
                        html_popup += f"<p style='font-size:14px; font-weight:bold; margin:0;'>{prod}</p>"
                        if p_de: html_popup += f"<span style='font-size:11px; color:#888; text-decoration:line-through;'>De: R$ {p_de}</span> "
                        html_popup += f"<span style='color:#ff4b4b; font-weight:bold; font-size:15px;'>Por: R$ {p_por}</span>"
                        
                        if img and img.startswith("http"):
                            html_popup += f"<img src='{img}' style='width:100%; border-radius:5px; margin-top:5px;'>"
                        html_popup += "</div>"
                    
                    # Botões de Ação da Loja (Ficam no final do balão)
                    html_popup += "<div style='margin-top:15px;'>"
                    link_maps = f"http://googleusercontent.com/maps.google.com/4{lat},{lon}"
                    html_popup += f"<a href='{link_maps}' target='_blank' style='display:inline-block; background-color:#ff4b4b; color:white; padding:8px 0; text-decoration:none; border-radius:5px; font-weight:bold; width:100%; text-align:center; margin-bottom:5px;'>📍 Chegar Lá (GPS)</a>"
                    
                    if zap_loja:
                        zap_limpo = "".join(filter(str.isdigit, zap_loja))
                        link_wa = f"https://wa.me/55{zap_limpo}?text=Olá! Vi suas ofertas no app No Precinho."
                        html_popup += f"<a href='{link_wa}' target='_blank' style='display:inline-block; background-color:#25D366; color:white; padding:8px 0; text-decoration:none; border-radius:5px; font-weight:bold; width:100%; text-align:center;'>💬 WhatsApp</a>"
                    
                    html_popup += f"<p style='font-size:8px; color:#999; margin-top:10px; text-align:center;'>* Ofertas válidas por tempo indeterminado ou até durar o estoque.</p>"
                    html_popup += "</div></div>"
                    
                    folium.Marker(
                        [lat, lon], 
                        popup=folium.Popup(html_popup, max_width=260), 
                        tooltip=f"{nome_loja} ({len(produtos_da_loja)} ofertas)",
                        icon=folium.Icon(color="red", icon="shopping-basket", prefix='fa')
                    ).add_to(m)
                except: pass 
                
    st_folium(m, width=1200, height=550, returned_objects=[])

elif st.session_state.perfil_logado == "admin":
    st.header("👑 Administração de Ofertas")
    df_ofertas_admin = carregar_tabela("Ofertas")
    if not df_ofertas_admin.empty:
        df_editado = st.data_editor(df_ofertas_admin, use_container_width=True, num_rows="dynamic",
            column_config={"status_pagamento": st.column_config.SelectboxColumn("Status", options=["pendente", "aprovado", "expirado"], required=True)})
        if st.button("💾 Salvar Liberações", type="primary", use_container_width=True):
            if sincronizar_aba_completa("Ofertas", df_editado): st.success("✅ Sistema atualizado!")
    else: st.write("Nenhuma oferta no radar.")

elif st.session_state.perfil_logado == "comerciante":
    st.header("🏪 Lançar Nova Oferta")
    st.markdown("<div class='caixa-destaque'>💡 <b>Múltiplos Produtos:</b> Você pode cadastrar quantos produtos quiser! Todos aparecerão no seu Pin no mapa.</div>", unsafe_allow_html=True)
    with st.form("form_oferta", clear_on_submit=True):
        p_nome = st.text_input("Produto (Ex: Arroz 5kg)")
        c1, c2 = st.columns(2)
        with c1: p_de = st.text_input("Preço Normal (R$)")
        with c2: p_por = st.text_input("Preço Oferta (R$)")
        p_img = st.text_input("Link da Imagem (ImgBB)")
        st.info("💰 Taxa: R$ 2,00 por anúncio de 24h. PIX: 04994867460")
        if st.form_submit_button("🚀 Enviar Oferta", use_container_width=True):
            if p_nome and p_por:
                if salvar_nova_oferta(st.session_state.usuario_logado, p_nome, p_de, p_por, p_img):
                    st.success("✅ Oferta enviada! Aguarde a aprovação do Admin.")
