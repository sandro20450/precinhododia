import streamlit as st
import pandas as pd
from datetime import datetime
import time
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
    .caixa-destaque { background-color: #e6f7ff; padding: 15px; border-radius: 8px; border-left: 5px solid #0066cc; margin-bottom: 20px;}
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
        st.success(f"👋 Olá, {st.session_state.nome_logado}!")
        
        if st.session_state.perfil_logado == "admin":
            st.button("👑 Painel Admin", use_container_width=True)
        elif st.session_state.perfil_logado == "comerciante":
            st.button("🏪 Lançar Oferta", use_container_width=True)
            
        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            fazer_logout()

# =============================================================================
# --- 5. TELA PRINCIPAL (FRONT-END) ---
# =============================================================================
if st.session_state.usuario_logado is None:
    st.title("Descubra as melhores ofertas perto de você! 🛒")
    pesquisa = st.text_input("🔍 O que você procura hoje?", placeholder="Ex: Leite, Carne, Pão...")
    
    # --- CONSTRUÇÃO DO MAPA REAL ---
    df_ofertas = carregar_tabela("Ofertas")
    df_lojas = carregar_tabela("Lojas")
    
    # Inicia o mapa centralizado em Vitória de Santo Antão
    m = folium.Map(location=[-8.1189, -35.2925], zoom_start=14)
    
    if not df_ofertas.empty and not df_lojas.empty:
        ofertas_ativas = df_ofertas[df_ofertas['status_pagamento'].astype(str).str.strip().str.lower() == 'aprovado']
        
        if pesquisa:
            ofertas_ativas = ofertas_ativas[ofertas_ativas['produto'].astype(str).str.contains(pesquisa, case=False, na=False)]
            
        for _, oferta in ofertas_ativas.iterrows():
            usr_loja = str(oferta.get('usuario_loja', '')).strip()
            loja_info = df_lojas[df_lojas['usuario_dono'].astype(str).str.strip() == usr_loja]
            
            if not loja_info.empty:
                try:
                    # Limpa e lê a coordenada
                    lat_str = str(loja_info.iloc[0].get('latitude', '-8.1189')).replace("'", "").strip()
                    lon_str = str(loja_info.iloc[0].get('longitude', '-35.2925')).replace("'", "").strip()
                    lat = float(lat_str)
                    lon = float(lon_str)
                    
                    nome_loja = loja_info.iloc[0].get('nome_fantasia', 'Loja')
                    zap_loja = str(loja_info.iloc[0].get('whatsapp', '')).strip()
                    
                    produto = oferta.get('produto', '')
                    preco_de = oferta.get('preco_de', '')
                    preco_novo = oferta.get('preco_por', '')
                    img = oferta.get('link_imagem', '')
                    
                    # --- CONSTRUÇÃO DO BALÃOZINHO COM BOTÕES ---
                    html_popup = f"<div style='width:220px; text-align:center; font-family:sans-serif;'>"
                    html_popup += f"<h4 style='color:#0066cc; margin:0 0 5px 0;'>{nome_loja}</h4>"
                    html_popup += f"<p style='font-size:16px; font-weight:bold; margin:0;'>{produto}</p>"
                    
                    if preco_de: # Se tiver preço antigo, mostra riscado
                        html_popup += f"<p style='margin:0; font-size:12px; color:#888; text-decoration:line-through;'>De: R$ {preco_de}</p>"
                        
                    html_popup += f"<h3 style='color:#ff4b4b; margin:5px 0 10px 0;'>Por: R$ {preco_novo}</h3>"
                    
                    if img and img.startswith("http"):
                        html_popup += f"<img src='{img}' style='width:100%; border-radius:8px; margin-bottom:10px; border: 1px solid #ccc;'>"
                        
                    # Botão 1: Traçar Rota (Abre Google Maps com Destino)
                    link_maps = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
                    html_popup += f"<a href='{link_maps}' target='_blank' style='display:inline-block; background-color:#ff4b4b; color:white; padding:8px 0; text-decoration:none; border-radius:5px; font-weight:bold; width:100%; box-sizing:border-box; margin-bottom:5px;'>📍 Chegar Lá (GPS)</a>"
                    
                    # Botão 2: Chamar no WhatsApp (Se houver número cadastrado)
                    if zap_loja:
                        zap_limpo = "".join(filter(str.isdigit, zap_loja)) # Remove traços e espaços
                        link_wa = f"https://wa.me/55{zap_limpo}?text=Olá! Vi a oferta do *{produto}* no app No Precinho."
                        html_popup += f"<a href='{link_wa}' target='_blank' style='display:inline-block; background-color:#25D366; color:white; padding:8px 0; text-decoration:none; border-radius:5px; font-weight:bold; width:100%; box-sizing:border-box;'>💬 Reservar no WhatsApp</a>"
                        
                    html_popup += "</div>"
                    
                    # Dispara o Pin para o mapa
                    folium.Marker(
                        [lat, lon], 
                        popup=folium.Popup(html_popup, max_width=250), 
                        tooltip=f"Ver oferta: {produto}",
                        icon=folium.Icon(color="red", icon="shopping-cart", prefix='fa')
                    ).add_to(m)
                except ValueError:
                    pass 
                
    st_folium(m, width=1200, height=500, returned_objects=[])

elif st.session_state.perfil_logado == "admin":
    st.header("👑 Centro de Comando - Administração")
    st.info("💡 Quando um pagamento PIX for confirmado no seu banco, mude o Status da oferta de 'pendente' para 'aprovado' para ela aparecer no mapa.")
    
    df_ofertas_admin = carregar_tabela("Ofertas")
    if not df_ofertas_admin.empty:
        st.markdown("### 📋 Gestão de Ofertas")
        df_editado = st.data_editor(
            df_ofertas_admin, 
            use_container_width=True, 
            num_rows="dynamic",
            column_config={
                "status_pagamento": st.column_config.SelectboxColumn("Status (Pagamento)", options=["pendente", "aprovado", "expirado"], required=True),
                "link_imagem": st.column_config.LinkColumn("Foto")
            }
        )
        if st.button("💾 Salvar Liberações", type="primary", use_container_width=True):
            with st.spinner("Atualizando os radares..."):
                if sincronizar_aba_completa("Ofertas", df_editado):
                    st.success("✅ Ofertas atualizadas com sucesso no banco de dados!")
    else:
        st.write("Nenhuma oferta cadastrada ainda.")

elif st.session_state.perfil_logado == "comerciante":
    st.header("🏪 Central de Lançamento de Ofertas")
    st.markdown("Preencha os dados abaixo para enviar o seu produto para o mapa da cidade. **O anúncio dura 24 horas!**")
    
    st.markdown("<div class='caixa-destaque'>💡 <b>Dica de Imagem:</b> Hospede a foto do seu produto no site <a href='https://pt-br.imgbb.com/' target='_blank'>ImgBB</a> e cole o <b>Link Direto</b> no formulário abaixo.</div>", unsafe_allow_html=True)
    
    with st.form("form_nova_oferta", clear_on_submit=True):
        st.subheader("📦 Dados do Produto")
        
        produto_nome = st.text_input("Nome do Produto + Quantidade (Ex: Leite Ninho 400g)", max_chars=50)
        
        c1, c2 = st.columns(2)
        with c1:
            preco_antigo = st.text_input("De: R$ (Preço Normal)")
        with c2:
            preco_novo = st.text_input("Por: R$ (Preço da Oferta)")
            
        link_img = st.text_input("🔗 Link Direto da Imagem (Opcional, mas recomendado)")
        
        st.markdown("---")
        st.markdown("### 💳 Pagamento da Taxa de Divulgação")
        st.write("Cada anúncio de 24h tem um custo fixo de **R$ 2,00**. Realize o PIX e envie a oferta para a central de aprovação.")
        st.info("🔑 Chave PIX: **04994867460** (Eliude Bernardo de Souza Silva)")
        
        enviar_btn = st.form_submit_button("🚀 Enviar Oferta para Aprovação", type="primary", use_container_width=True)
        
        if enviar_btn:
            if not produto_nome or not preco_novo:
                st.error("⚠️ O nome do produto e o preço da oferta são obrigatórios!")
            else:
                with st.spinner("A transmitir oferta para a central..."):
                    if salvar_nova_oferta(st.session_state.usuario_logado, produto_nome, preco_antigo, preco_novo, link_img):
                        st.success("✅ Oferta enviada com sucesso! Assim que o administrador confirmar o seu PIX de R$ 2,00, ela aparecerá no mapa para toda a cidade.")
