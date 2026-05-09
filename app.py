import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import gspread
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium
import urllib.parse

# =============================================================================
# --- 1. CONFIGURAÇÕES GERAIS E CSS CUSTOMIZADO ---
# =============================================================================
st.set_page_config(page_title="No Precinho - Ofertas", page_icon="icone.png", layout="wide")

st.markdown("""
<style>
    footer { display: none !important; visibility: hidden !important; }
    div[data-testid="stTextInput"] {
        box-shadow: 0 8px 24px rgba(0,0,0,0.15); border-radius: 12px; padding: 5px; background-color: white; border: 1px solid #eee; margin-bottom: 20px;
    }
    div.row-widget.stRadio > div {
        background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); display: flex; justify-content: center; gap: 20px;
    }
    .painel-login { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-top: 4px solid #ff4b4b; }
    .caixa-destaque { background-color: #e6f7ff; padding: 15px; border-radius: 8px; border-left: 5px solid #0066cc; margin-bottom: 20px;}
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
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    return None

@st.cache_data(ttl=60, show_spinner=False)
def carregar_tabela(nome_aba):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_NoPrecinho").worksheet(nome_aba)
            dados = ws.get_all_values()
            if len(dados) <= 1: return pd.DataFrame(columns=dados[0] if dados else [])
            df = pd.DataFrame(dados[1:], columns=dados[0])
            df.columns = df.columns.astype(str).str.strip().str.lower()
            return df
        return pd.DataFrame()
    except Exception: return pd.DataFrame()

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
        st.error(f"Erro ao sincronizar: {e}")
        return False

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
    except Exception: return False

def salvar_novo_usuario_vendedor(usuario, senha, nome, cidade):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_NoPrecinho").worksheet("Usuarios")
            ws.append_row([usuario, senha, "comerciante", nome, cidade, "pendente", "PENDENTE"])
            st.cache_data.clear()
            return True
    except Exception: return False

def salvar_nova_loja_vendedor(usuario_dono, nome_fantasia, endereco, zap, instagram, lat, lon, categoria):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_NoPrecinho").worksheet("Lojas")
            ws.append_row([usuario_dono, nome_fantasia, endereco, zap, instagram, f"'{lat}", f"'{lon}", categoria])
            st.cache_data.clear()
            return True
    except Exception: return False

def excluir_oferta_bd(id_oferta):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_NoPrecinho").worksheet("Ofertas")
            celula = ws.find(id_oferta)
            if celula:
                ws.delete_rows(celula.row)
                st.cache_data.clear()
                return True
        return False
    except Exception: return False

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
            perfil = str(user_row.iloc[0].get('perfil', '')).strip().lower()
            
            if status_user == 'aprovado':
                if perfil == "comerciante":
                    vencimento_str = str(user_row.iloc[0].get('vencimento', '')).strip()
                    try:
                        data_venc = datetime.strptime(vencimento_str, "%d/%m/%Y")
                        if datetime.now() > data_venc:
                            st.error("🚫 Anuidade expirou! Contate a administração.")
                            return
                    except: return

                st.session_state.usuario_logado = str(user_row.iloc[0]['usuario']).strip()
                st.session_state.nome_logado = str(user_row.iloc[0].get('nome', '')).strip()
                st.session_state.perfil_logado = perfil
                st.success("✅ Acesso Concedido!")
                st.rerun()
            else: st.warning("⏳ Cadastro pendente.")
        else: st.error("❌ Credenciais incorretas.")

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
        st.markdown("### 🔐 Acesso Restrito")
        user_input = st.text_input("Usuário", key="login_user")
        pass_input = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Entrar", type="primary", use_container_width=True):
            fazer_login(user_input, pass_input)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.success(f"👋 Olá, {st.session_state.nome_logado}!")
        if st.session_state.perfil_logado == "admin": st.button("👑 Painel Admin", use_container_width=True)
        elif st.session_state.perfil_logado == "comerciante": st.button("🏪 Lançar Oferta", use_container_width=True)
        elif st.session_state.perfil_logado == "vendedor": st.button("🤝 Painel Vendas", use_container_width=True)
        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True): fazer_logout()

# =============================================================================
# --- 5. TELA PRINCIPAL (FRONT-END) ---
# =============================================================================
if st.session_state.usuario_logado is None:
    
    # --- NOVO CABEÇALHO USANDO ARQUIVO NATIVO DO REPOSITÓRIO ---
    c_logo, c_titulo = st.columns([0.1, 1.1])
    with c_logo:
        st.image("icone.png", width=50) # Puxa o arquivo icone.png do seu GitHub
    with c_titulo:
        st.markdown("<h1 style='margin-top: -10px;'>Descubra as melhores ofertas perto de você!</h1>", unsafe_allow_html=True)
    
    pesquisa = st.text_input("", placeholder="🔍 Digite o que você procura... (Ex: Leite, Dipirona, Cimento)", label_visibility="collapsed")
    filtro_categoria = st.radio("Filtro", ["🌎 Todas as Ofertas", "🛒 Alimentos", "💊 Farmácia", "🧱 Construção"], horizontal=True, label_visibility="collapsed")
    
    df_ofertas = carregar_tabela("Ofertas")
    df_lojas = carregar_tabela("Lojas")
    m = folium.Map(location=[-8.1189, -35.2925], zoom_start=14)
    
    coordenadas_ativas = []
    
    if not df_ofertas.empty and not df_lojas.empty:
        ofertas_ativas = df_ofertas[df_ofertas['status_pagamento'].astype(str).str.strip().str.lower() == 'aprovado']
        
        agora = datetime.now()
        ofertas_24h = []
        for _, row in ofertas_ativas.iterrows():
            try:
                data_postagem = datetime.strptime(str(row['data_hora']), "%Y-%m-%d %H:%M:%S")
                if (agora - data_postagem).total_seconds() <= 86400:
                    ofertas_24h.append(row)
            except: pass
        ofertas_ativas = pd.DataFrame(ofertas_24h)

        if not ofertas_ativas.empty:
            if pesquisa:
                ofertas_ativas = ofertas_ativas[ofertas_ativas['produto'].astype(str).str.contains(pesquisa, case=False, na=False)]
            
            lojas_com_oferta = ofertas_ativas['usuario_loja'].unique()
            for usr_loja in lojas_com_oferta:
                loja_info = df_lojas[df_lojas['usuario_dono'].astype(str).str.strip() == usr_loja.strip()]
                
                if not loja_info.empty:
                    categoria_loja = str(loja_info.iloc[0].get('categoria', 'Alimentos')).strip()
                    mostrar_no_mapa = False
                    if filtro_categoria == "🌎 Todas as Ofertas": mostrar_no_mapa = True
                    elif filtro_categoria == "🛒 Alimentos" and categoria_loja.lower() == "alimentos": mostrar_no_mapa = True
                    elif filtro_categoria == "💊 Farmácia" and categoria_loja.lower() in ["farmácia", "farmacia"]: mostrar_no_mapa = True
                    elif filtro_categoria == "🧱 Construção" and categoria_loja.lower() in ["construção", "construcao"]: mostrar_no_mapa = True
                    
                    if mostrar_no_mapa:
                        try:
                            lat = float(str(loja_info.iloc[0].get('latitude', '-8.1189')).replace("'", "").strip())
                            lon = float(str(loja_info.iloc[0].get('longitude', '-35.2925')).replace("'", "").strip())
                            nome_loja = loja_info.iloc[0].get('nome_fantasia', 'Loja')
                            zap_loja = str(loja_info.iloc[0].get('whatsapp', '')).strip()
                            
                            coordenadas_ativas.append([lat, lon])
                            
                            # CORES E ÍCONES 3D
                            cor_clara, cor_escura = "#ff6b6b", "#cc0000" 
                            icone_pin = "shopping-basket"
                            if categoria_loja.lower() in ["farmácia", "farmacia"]: 
                                cor_clara, cor_escura = "#4dabf7", "#0050b3"
                                icone_pin = "medkit"
                            elif categoria_loja.lower() in ["construção", "construcao"]: 
                                cor_clara, cor_escura = "#ffa94d", "#d97706"
                                icone_pin = "hammer"
                                
                            pin_3d_html = f"""
                            <div style="width:38px; height:38px; background:radial-gradient(circle at 30% 30%, {cor_clara}, {cor_escura});
                                 border-radius:50% 50% 50% 0; transform:rotate(-45deg); box-shadow:-4px 5px 8px rgba(0,0,0,0.4);
                                 display:flex; align-items:center; justify-content:center; border:2px solid white;">
                                <i class="fa fa-{icone_pin}" style="transform:rotate(45deg); color:white; font-size:16px; text-shadow:1px 1px 2px rgba(0,0,0,0.5);"></i>
                            </div>
                            """
                                
                            produtos_da_loja = ofertas_ativas[ofertas_ativas['usuario_loja'] == usr_loja]
                            html_popup = f"<div style='width:240px; font-family:sans-serif;'><h3 style='color:#0066cc; margin:0 0 10px 0; text-align:center; border-bottom:2px solid #0066cc;'>{nome_loja}</h3>"
                            
                            for _, row in produtos_da_loja.iterrows():
                                prod, p_de, p_por, img = row.get('produto', ''), row.get('preco_de', ''), row.get('preco_por', ''), row.get('link_imagem', '')
                                html_popup += f"<div class='item-oferta'><p style='font-size:14px; font-weight:bold; margin:0;'>{prod}</p>"
                                if p_de: html_popup += f"<span style='font-size:11px; color:#888; text-decoration:line-through;'>De: R$ {p_de}</span> "
                                html_popup += f"<span style='color:#ff4b4b; font-weight:bold; font-size:15px;'>Por: R$ {p_por}</span>"
                                if img and img.startswith("http"): html_popup += f"<img src='{img}' style='width:100%; border-radius:5px; margin-top:5px;'>"
                                html_popup += "</div>"
                            
                            html_popup += "<div style='margin-top:15px;'>"
                            html_popup += f"<a href='https://www.google.com/maps/dir/?api=1&destination={lat},{lon}' target='_blank' style='display:inline-block; background-color:#ff4b4b; color:white; padding:8px 0; text-decoration:none; border-radius:5px; font-weight:bold; width:100%; text-align:center; margin-bottom:5px;'>📍 Chegar Lá (GPS)</a>"
                            if zap_loja:
                                zap_limpo = "".join(filter(str.isdigit, zap_loja))
                                html_popup += f"<a href='https://wa.me/55{zap_limpo}?text=Olá! Vi suas ofertas no app No Precinho.' target='_blank' style='display:inline-block; background-color:#25D366; color:white; padding:8px 0; text-decoration:none; border-radius:5px; font-weight:bold; width:100%; text-align:center;'>💬 WhatsApp</a>"
                            html_popup += f"<p style='font-size:9px; color:#888; margin-top:10px; text-align:center; line-height:1.2;'>* Ofertas válidas por 24h ou até durar o estoque.<br>Imagem meramente ilustrativa.</p></div></div>"
                            
                            folium.Marker([lat, lon], popup=folium.Popup(html_popup, max_width=260), icon=folium.DivIcon(html=pin_3d_html, icon_anchor=(19, 38), popup_anchor=(0, -38))).add_to(m)
                        except: pass 
    
    if coordenadas_ativas: m.fit_bounds(coordenadas_ativas)
    st_folium(m, width=1200, height=550, returned_objects=[])

elif st.session_state.perfil_logado == "admin":
    st.header("👑 Centro de Comando (Admin)")
    aba_ofertas, aba_lojas, aba_usuarios = st.tabs(["🛒 Gestão de Ofertas (R$ 5,00)", "🏪 Lojas", "👥 Usuários (Anuidade)"])
    
    with aba_ofertas:
        df_ofertas_admin = carregar_tabela("Ofertas")
        if not df_ofertas_admin.empty:
            df_editado_ofertas = st.data_editor(df_ofertas_admin, use_container_width=True, num_rows="dynamic",
                column_config={"status_pagamento": st.column_config.SelectboxColumn("Status", options=["pendente", "aprovado", "expirado"], required=True)})
            if st.button("💾 Salvar Ofertas", type="primary", use_container_width=True):
                if sincronizar_aba_completa("Ofertas", df_editado_ofertas): st.success("Atualizado!")
                
    with aba_lojas:
        df_lojas_admin = carregar_tabela("Lojas")
        if not df_lojas_admin.empty:
            df_editado_lojas = st.data_editor(df_lojas_admin, use_container_width=True, num_rows="dynamic",
                column_config={"categoria": st.column_config.SelectboxColumn("Categoria", options=["Alimentos", "Farmácia", "Construção"], required=True)})
            if st.button("💾 Salvar Lojas", type="primary", use_container_width=True):
                if sincronizar_aba_completa("Lojas", df_editado_lojas): st.success("Atualizado!")
                
    with aba_usuarios:
        df_users_admin = carregar_tabela("Usuarios")
        if not df_users_admin.empty:
            df_editado_users = st.data_editor(df_users_admin, use_container_width=True, num_rows="dynamic",
                column_config={"status": st.column_config.SelectboxColumn("Status", options=["pendente", "aprovado"], required=True), "perfil": st.column_config.SelectboxColumn("Perfil", options=["admin", "comerciante", "vendedor"], required=True)})
            if st.button("💾 Salvar Usuários", type="primary", use_container_width=True):
                if sincronizar_aba_completa("Usuarios", df_editado_users): st.success("Atualizado!")

elif st.session_state.perfil_logado == "vendedor":
    st.header("🤝 Painel de Captação (Vendedor)")
    with st.expander("👤 1. Cadastrar Novo Comerciante", expanded=True):
        with st.form("form_novo_user", clear_on_submit=True):
            u_login, u_senha, u_nome, u_cid = st.text_input("Usuário"), st.text_input("Senha"), st.text_input("Nome"), st.text_input("Cidade")
            if st.form_submit_button("Enviar Cadastro", type="primary"):
                if u_login and u_senha:
                    if salvar_novo_usuario_vendedor(u_login, u_senha, u_nome, u_cid): st.success("Enviado!")
                
    with st.expander("🏪 2. Cadastrar Loja", expanded=False):
        with st.form("form_nova_loja", clear_on_submit=True):
            l_dono, l_nome, l_cat, l_end, l_zap, l_inst, l_lat, l_lon = st.text_input("Usuário Dono"), st.text_input("Nome Fantasia"), st.selectbox("Categoria", ["Alimentos", "Farmácia", "Construção"]), st.text_input("Endereço"), st.text_input("WhatsApp"), st.text_input("Instagram"), st.text_input("Latitude"), st.text_input("Longitude")
            if st.form_submit_button("Enviar Loja", type="primary"):
                if l_dono and l_lat and l_lon:
                    if salvar_nova_loja_vendedor(l_dono, l_nome, l_end, l_zap, l_inst, l_lat, l_lon, l_cat): st.success("Cadastrada!")

elif st.session_state.perfil_logado == "comerciante":
    st.header("🏪 Central do Comerciante")
    df_minhas = carregar_tabela("Ofertas")
    
    with st.form("form_oferta", clear_on_submit=True):
        p_nome, p_de, p_por, p_img = st.text_input("Produto"), st.text_input("Preço Normal"), st.text_input("Preço Oferta"), st.text_input("Link Imagem")
        if st.form_submit_button("Enviar Oferta", type="primary", use_container_width=True):
            if p_nome and p_por:
                if salvar_nova_oferta(st.session_state.usuario_logado, p_nome, p_de, p_por, p_img):
                    st.success("✅ Oferta enviada!")
                    link_wa = f"https://wa.me/558199964261?text=Nova%20oferta%20enviada%20por%20{st.session_state.nome_logado}"
                    st.markdown(f"<a href='{link_wa}' target='_blank' style='display:block; background-color:#25D366; color:white; text-align:center; padding:10px; border-radius:8px; font-weight:bold; text-decoration:none; margin-top:10px;'>📲 Avisar Admin no WhatsApp</a>", unsafe_allow_html=True)

    st.subheader("🗑️ Gerenciar Ofertas")
    if not df_minhas.empty:
        minhas = df_minhas[df_minhas['usuario_loja'].astype(str).str.strip() == str(st.session_state.usuario_logado).strip()]
        for _, row in minhas.iterrows():
            c_info, c_btn = st.columns([4, 1])
            with c_info: st.write(f"📦 {row.get('produto', '')} - R$ {row.get('preco_por', '')}")
            with c_btn:
                if st.button("❌", key=row.get('id_oferta')):
                    if excluir_oferta_bd(row.get('id_oferta')): st.rerun()
