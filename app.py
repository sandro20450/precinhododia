import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import gspread
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium
import urllib.parse
import os
import base64
import re
import uuid

# =============================================================================
# --- 1. CONFIGURAÇÕES GERAIS E CSS CUSTOMIZADO ---
# =============================================================================
st.set_page_config(page_title="Precinho do Dia - Ofertas", page_icon="noprecinho.png", layout="wide")

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
    
    /* EFEITO SOMBREADO/FLUTUANTE (3D) EM TODOS OS BOTÕES DO APP */
    div[data-testid="stButton"] button {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
        transition: all 0.2s ease-in-out !important;
    }
    div[data-testid="stButton"] button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 6px 12px rgba(0,0,0,0.25) !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# --- 2. FUNÇÕES COMERCIAIS E BANCO DE DADOS ---
# =============================================================================

def gerar_id():
    return f"OP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

def exibir_banner_comercial():
    msg = "🚀 Quer fazer parte do nosso aplicativo? Fale conosco agora!"
    link = "https://wa.me/5581999642681?text=Olá! Quero anunciar no Precinho do Dia."
    st.markdown(f"""
        <div style="background-color:#007bff; padding:15px; border-radius:10px; text-align:center; margin-top:20px; margin-bottom:20px; box-shadow: 0 4px 8px rgba(0,0,0,0.15);">
            <a href='{link}' target='_blank' style='color:white; font-size:18px; font-weight:bold; text-decoration:none;'>{msg}</a>
        </div>
    """, unsafe_allow_html=True)

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

def salvar_nova_oferta(usuario_loja, id_oferta, produto, preco_de, preco_por, link_imagem):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_NoPrecinho").worksheet("Ofertas")
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

def limpar_html(texto):
    if texto is None: return ""
    texto = str(texto)
    if texto.lower() in ['nan', 'nat', 'none']: return ""
    texto = re.sub(r'<.*?>', '', texto)
    texto = texto.replace('R$', '').replace('R', '').replace('_', '').strip()
    return texto

# =============================================================================
# --- 3. SISTEMA DE LOGIN ---
# =============================================================================
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = None
if "perfil_logado" not in st.session_state: st.session_state.perfil_logado = None
if "nome_logado" not in st.session_state: st.session_state.nome_logado = None
if "alvo_mapa" not in st.session_state: st.session_state.alvo_mapa = None

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
    try:
        img_path_sidebar = None
        if os.path.exists("noprecinho.png"): img_path_sidebar = "noprecinho.png"
        elif os.path.exists("Noprecinho.png"): img_path_sidebar = "Noprecinho.png"
        elif os.path.exists("noprecinho.PNG"): img_path_sidebar = "noprecinho.PNG"
        
        if img_path_sidebar:
            with open(img_path_sidebar, "rb") as image_file:
                encoded_string_side = base64.b64encode(image_file.read()).decode()
            st.markdown(f'''
                <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                    <img src="data:image/png;base64,{encoded_string_side}" width="120" style="border-radius: 18px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown("<h2 style='text-align: center; color: #ff4b4b;'>📍 PRECINHO DO DIA</h2>", unsafe_allow_html=True)
    except:
        st.markdown("<h2 style='text-align: center; color: #ff4b4b;'>📍 PRECINHO DO DIA</h2>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    if st.session_state.usuario_logado is None:
        st.markdown("<div class='painel-login'>", unsafe_allow_html=True)
        st.markdown("### 🔑 Acesso Empresa")
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
    
    try:
        img_path = None
        if os.path.exists("noprecinho.png"): img_path = "noprecinho.png"
        elif os.path.exists("Noprecinho.png"): img_path = "Noprecinho.png"
        elif os.path.exists("noprecinho.PNG"): img_path = "noprecinho.PNG"
        
        if img_path:
            with open(img_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            st.markdown(f'''<div style="display: flex; justify-content: center; margin-bottom: 10px; margin-top: 10px;"><img src="data:image/png;base64,{encoded_string}" width="130" style="border-radius: 18px; box-shadow: 0 8px 16px rgba(0,0,0,0.15);"></div>''', unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='text-align: center; font-size: 60px; margin-top: 10px;'>📍</h1>", unsafe_allow_html=True)
    except:
        st.markdown("<h1 style='text-align: center; font-size: 60px; margin-top: 10px;'>📍</h1>", unsafe_allow_html=True)
        
    st.markdown("<h1 style='text-align: center; margin-top: 5px; margin-bottom: 30px;'>Descubra as melhores ofertas perto de você!</h1>", unsafe_allow_html=True)
    
    # --- NOVO: PRÉ-CARREGAMENTO E CONTAGEM DE OFERTAS ---
    df_ofertas = carregar_tabela("Ofertas")
    df_lojas = carregar_tabela("Lojas")
    
    total_ofertas = 0
    qtd_ali = 0
    qtd_far = 0
    qtd_con = 0
    
    ofertas_ativas = pd.DataFrame()
    if not df_ofertas.empty and not df_lojas.empty:
        ofertas_ativas_temp = df_ofertas[df_ofertas['status_pagamento'].astype(str).str.strip().str.lower() == 'aprovado']
        agora = datetime.now()
        ofertas_24h = []
        for _, row in ofertas_ativas_temp.iterrows():
            try:
                data_postagem = datetime.strptime(str(row['data_hora']), "%Y-%m-%d %H:%M:%S")
                if (agora - data_postagem).total_seconds() <= 86400:
                    ofertas_24h.append(row)
            except: pass
        ofertas_ativas = pd.DataFrame(ofertas_24h)

        if not ofertas_ativas.empty:
            total_ofertas = len(ofertas_ativas)
            df_merged = pd.merge(ofertas_ativas, df_lojas, left_on='usuario_loja', right_on='usuario_dono', how='left')
            if 'categoria' in df_merged.columns:
                cat_lower = df_merged['categoria'].astype(str).str.strip().str.lower()
                qtd_ali = len(df_merged[cat_lower == 'alimentos'])
                qtd_far = len(df_merged[cat_lower.isin(['farmácia', 'farmacia'])])
                qtd_con = len(df_merged[cat_lower.isin(['construção', 'construcao'])])

    # Construindo os nomes dos botões com as contagens
    lbl_todas = f"🌎 Todas as Ofertas ({total_ofertas})"
    lbl_ali = f"🛒 Alimentos ({qtd_ali})"
    lbl_far = f"💊 Farmácia ({qtd_far})"
    lbl_con = f"🧱 Construção ({qtd_con})"
    
    pesquisa = st.text_input("", placeholder="🔍 Digite o que você procura... (Ex: Leite, Dipirona, Cimento)", label_visibility="collapsed")
    filtro_categoria = st.radio("Filtro", [lbl_todas, lbl_ali, lbl_far, lbl_con], horizontal=True, label_visibility="collapsed")
    
    centro_inicial = st.session_state.alvo_mapa if st.session_state.alvo_mapa else [-8.1189, -35.2925]
    zoom_inicial = 18 if st.session_state.alvo_mapa else 14
    m = folium.Map(location=centro_inicial, zoom_start=zoom_inicial)
    
    coordenadas_ativas = []
    lista_catalogo = [] 
    
    if not ofertas_ativas.empty:
        if pesquisa:
            ofertas_ativas = ofertas_ativas[ofertas_ativas['produto'].astype(str).str.contains(pesquisa, case=False, na=False)]
        
        lojas_com_oferta = ofertas_ativas['usuario_loja'].unique()
        for usr_loja in lojas_com_oferta:
            loja_info = df_lojas[df_lojas['usuario_dono'].astype(str).str.strip() == usr_loja.strip()]
            
            if not loja_info.empty:
                categoria_loja = str(loja_info.iloc[0].get('categoria', 'Alimentos')).strip()
                mostrar_no_mapa = False
                
                # Regra de filtro usando os novos labels dinâmicos
                if filtro_categoria == lbl_todas: mostrar_no_mapa = True
                elif filtro_categoria == lbl_ali and categoria_loja.lower() == "alimentos": mostrar_no_mapa = True
                elif filtro_categoria == lbl_far and categoria_loja.lower() in ["farmácia", "farmacia"]: mostrar_no_mapa = True
                elif filtro_categoria == lbl_con and categoria_loja.lower() in ["construção", "construcao"]: mostrar_no_mapa = True
                
                if mostrar_no_mapa:
                    try:
                        lat = float(str(loja_info.iloc[0].get('latitude', '-8.1189')).replace("'", "").strip())
                        lon = float(str(loja_info.iloc[0].get('longitude', '-35.2925')).replace("'", "").strip())
                        nome_loja = loja_info.iloc[0].get('nome_fantasia', 'Loja')
                        zap_loja = str(loja_info.iloc[0].get('whatsapp', '')).strip()
                        
                        coordenadas_ativas.append([lat, lon])
                        
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
                        
                        # --- NOVO: MENSAGEM WHATSAPP DINÂMICA ---
                        msg_zap = "Olá! Vi no app Precinho do Dia as seguintes ofertas:\n"
                        
                        for _, row in produtos_da_loja.iterrows():
                            prod = str(row.get('produto', ''))
                            p_de = limpar_html(row.get('preco_de', ''))
                            p_por = limpar_html(row.get('preco_por', ''))
                            img = str(row.get('link_imagem', '')).strip()
                            
                            # Adiciona o produto na string do WhatsApp
                            msg_zap += f"👉 *{prod}* (Por: R$ {p_por})\n"
                            
                            lista_catalogo.append({
                                "loja": nome_loja, "produto": prod, 
                                "preco_por": p_por, "categoria": categoria_loja, "lat": lat, "lon": lon
                            })
                            
                            html_popup += f"<div class='item-oferta'><p style='font-size:14px; font-weight:bold; margin:0;'>{prod}</p>"
                            if p_de:
                                html_popup += f"<span style='font-size:11px; color:#888; text-decoration:line-through;'>De: R$ {p_de}</span><br>"
                            html_popup += f"<span style='color:#ff4b4b; font-weight:bold; font-size:15px;'>Por: R$ {p_por}</span>"
                            
                            if img and img.startswith("http"): 
                                html_popup += f"<img src='{img}' style='width:100%; border-radius:5px; margin-top:5px; border: 1px solid #ccc;'>"
                            html_popup += "</div>"
                        
                        html_popup += "<div style='margin-top:15px;'>"
                        html_popup += f"<a href='https://www.google.com/maps/dir/?api=1&destination={lat},{lon}' target='_blank' style='display:inline-block; background-color:#ff4b4b; color:white; padding:8px 0; text-decoration:none; border-radius:5px; font-weight:bold; width:100%; text-align:center; margin-bottom:5px;'>📍 Chegar Lá (GPS)</a>"
                        
                        if zap_loja:
                            zap_limpo = "".join(filter(str.isdigit, zap_loja))
                            # Codifica a mensagem gigante para o formato de Link do WhatsApp
                            msg_zap_encoded = urllib.parse.quote(msg_zap)
                            html_popup += f"<a href='https://wa.me/55{zap_limpo}?text={msg_zap_encoded}' target='_blank' style='display:inline-block; background-color:#25D366; color:white; padding:8px 0; text-decoration:none; border-radius:5px; font-weight:bold; width:100%; text-align:center;'>💬 WhatsApp</a>"
                            
                        html_popup += f"<p style='font-size:9px; color:#888; margin-top:10px; text-align:center; line-height:1.2;'>* Ofertas válidas por 24h ou até durar o estoque.<br>Imagem meramente ilustrativa.</p></div></div>"
                        
                        folium.Marker([lat, lon], popup=folium.Popup(html_popup, max_width=260), icon=folium.DivIcon(html=pin_3d_html, icon_anchor=(19, 38), popup_anchor=(0, -38))).add_to(m)
                    except: pass 
    
    if coordenadas_ativas and not st.session_state.alvo_mapa: m.fit_bounds(coordenadas_ativas)
    st_folium(m, width=1200, height=550, returned_objects=[])

    if st.session_state.alvo_mapa: st.session_state.alvo_mapa = None

    exibir_banner_comercial()

    # -------------------------------------------------------------
    # 🛒 CATÁLOGO EM LISTA ABAIXO DO MAPA
    # -------------------------------------------------------------
    if lista_catalogo:
        st.markdown("<h3 style='color:#333; margin-top: 30px; margin-bottom: 15px;'>🔥 Destaques da Categoria</h3>", unsafe_allow_html=True)
        
        with st.container(height=480):
            for idx, item in enumerate(lista_catalogo):
                c_img, c_texto, c_btn = st.columns([1, 4.5, 1.5], vertical_alignment="center")
                
                with c_img:
                    cat = item['categoria']
                    cor_clara, cor_escura = "#ff6b6b", "#cc0000" 
                    icone_list = "shopping-basket"
                    
                    if cat.lower() in ["farmácia", "farmacia"]: 
                        cor_clara, cor_escura = "#4dabf7", "#0050b3" 
                        icone_list = "medkit"
                    elif cat.lower() in ["construção", "construcao"]: 
                        cor_clara, cor_escura = "#ffa94d", "#d97706" 
                        icone_list = "hammer"
                    
                    pin_list_html = f"""
                    <div style="display:flex; justify-content:center; align-items:center; height: 100%;">
                        <div style="width:40px; height:40px; background:radial-gradient(circle at 30% 30%, {cor_clara}, {cor_escura});
                                     border-radius:50% 50% 50% 0; transform:rotate(-45deg); box-shadow:-4px 5px 8px rgba(0,0,0,0.3);
                                     display:flex; align-items:center; justify-content:center; border:2px solid white;">
                            <i class="fa fa-{icone_list}" style="transform:rotate(45deg); color:white; font-size:18px;"></i>
                        </div>
                    </div>
                    """
                    st.markdown(pin_list_html, unsafe_allow_html=True)
                
                with c_texto:
                    st.markdown(f"<p style='margin:0; font-weight:bold; font-size:16px; color:#333;'>{item['produto']}</p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='margin:0; font-size:12px; color:#666; margin-bottom:5px;'>🏪 {item['loja']}</p>", unsafe_allow_html=True)
                    st.markdown(f"<span style='color:#ff4b4b; font-weight:bold; font-size:18px;'>R$ {item['preco_por']}</span>", unsafe_allow_html=True)
                    
                with c_btn:
                    if st.button("📍 Ver no Mapa", key=f"btn_zoom_{idx}", use_container_width=True):
                        st.session_state.alvo_mapa = [item['lat'], item['lon']]
                        st.rerun()
                
                st.markdown("<hr style='margin: 10px 0; border-top: 1px solid #f0f0f0;'>", unsafe_allow_html=True)

elif st.session_state.perfil_logado == "admin":
    st.header("👑 Centro de Comando (Admin)")
    aba_ofertas, aba_lojas, aba_usuarios = st.tabs(["🛒 Gestão de Ofertas (R$ 5,00)", "🏪 Lojas", "👥 Usuários (Anuidade)"])
    
    with aba_ofertas:
        st.info("💡 Confirme o PIX de R$ 5,00 e mude o status para 'aprovado'.")
        df_ofertas_admin = carregar_tabela("Ofertas")
        if not df_ofertas_admin.empty:
            if 'preco_por' in df_ofertas_admin.columns:
                df_ofertas_admin['preco_por'] = df_ofertas_admin['preco_por'].apply(limpar_html)
            if 'preco_de' in df_ofertas_admin.columns:
                df_ofertas_admin['preco_de'] = df_ofertas_admin['preco_de'].apply(limpar_html)
            
            df_editado_ofertas = st.data_editor(df_ofertas_admin, use_container_width=True, num_rows="dynamic",
                column_config={"status_pagamento": st.column_config.SelectboxColumn("Status", options=["pendente", "aprovado", "expirado"], required=True), "link_imagem": st.column_config.LinkColumn("Foto")})
            if st.button("💾 Salvar Ofertas", type="primary", use_container_width=True, key="btn_off"):
                if sincronizar_aba_completa("Ofertas", df_editado_ofertas): st.success("Atualizado!")
        else: st.write("Nenhuma oferta no radar.")
        
    with aba_lojas:
        st.info("💡 Cadastros de lojas feitos pelos Vendedores ou Admin.")
        df_lojas_admin = carregar_tabela("Lojas")
        if not df_lojas_admin.empty:
            df_editado_lojas = st.data_editor(df_lojas_admin, use_container_width=True, num_rows="dynamic",
                column_config={"categoria": st.column_config.SelectboxColumn("Categoria", options=["Alimentos", "Farmácia", "Construção"], required=True)})
            if st.button("💾 Salvar Lojas", type="primary", use_container_width=True, key="btn_loj"):
                if sincronizar_aba_completa("Lojas", df_editado_lojas): st.success("Atualizado!")
                
    with aba_usuarios:
        st.info("💡 Controle as anuidades de R$ 120,00! Mude o status do comerciante para 'aprovado' e defina a data de 'vencimento' (Ex: 31/12/2026).")
        df_users_admin = carregar_tabela("Usuarios")
        if not df_users_admin.empty:
            df_editado_users = st.data_editor(df_users_admin, use_container_width=True, num_rows="dynamic",
                column_config={"status": st.column_config.SelectboxColumn("Status", options=["pendente", "aprovado"], required=True), "perfil": st.column_config.SelectboxColumn("Perfil", options=["admin", "comerciante", "vendedor"], required=True)})
            if st.button("💾 Salvar Usuários", type="primary", use_container_width=True, key="btn_usr"):
                if sincronizar_aba_completa("Usuarios", df_editado_users): st.success("Atualizado!")

elif st.session_state.perfil_logado == "vendedor":
    st.header("🤝 Painel de Captação (Vendedor)")
    st.info("Utilize este painel para fechar contratos com novos Comerciantes. Lembre-se que a anuidade é de **R$ 120,00**. Após enviar o cadastro, o Admin fará a aprovação final e definirá o vencimento.")
    
    with st.expander("👤 1. Cadastrar Novo Comerciante (Acesso)", expanded=True):
        with st.form("form_novo_user", clear_on_submit=True):
            u_login, u_senha, u_nome, u_cid = st.text_input("Usuário"), st.text_input("Senha"), st.text_input("Nome"), st.text_input("Cidade")
            if st.form_submit_button("Enviar Cadastro do Dono", type="primary"):
                if u_login and u_senha:
                    if salvar_novo_usuario_vendedor(u_login, u_senha, u_nome, u_cid): st.success("Enviado!")
                else: st.error("Preencha Login e Senha.")
                
    with st.expander("🏪 2. Cadastrar Loja (Endereço e Mapa)", expanded=False):
        with st.form("form_nova_loja", clear_on_submit=True):
            l_dono, l_nome, l_cat, l_end, l_zap, l_inst, l_lat, l_lon = st.text_input("Usuário Dono"), st.text_input("Nome Fantasia"), st.selectbox("Categoria", ["Alimentos", "Farmácia", "Construção"]), st.text_input("Endereço"), st.text_input("WhatsApp"), st.text_input("Instagram"), st.text_input("Latitude"), st.text_input("Longitude")
            if st.form_submit_button("Enviar Dados da Loja", type="primary"):
                if l_dono and l_lat and l_lon:
                    if salvar_nova_loja_vendedor(l_dono, l_nome, l_end, l_zap, l_inst, l_lat, l_lon, l_cat): st.success("Cadastrada!")
                else: st.error("Dono e Coordenadas são obrigatórios!")

elif st.session_state.perfil_logado == "comerciante":
    st.header("🏪 Central do Comerciante")
    
    df_minhas = carregar_tabela("Ofertas")
    hoje_str = datetime.now().strftime("%Y-%m-%d")
    qtd_hoje = len(df_minhas[(df_minhas['usuario_loja'].astype(str).str.strip() == str(st.session_state.usuario_logado).strip()) & (df_minhas['data_hora'].astype(str).str.startswith(hoje_str))]) if not df_minhas.empty else 0
    st.markdown(f"<div class='caixa-destaque'>💡 <b>O seu Limite Diário:</b> {qtd_hoje}/5 ofertas enviadas hoje.</div>", unsafe_allow_html=True)
    
    df_lojas_comerciante = carregar_tabela("Lojas")
    nome_fantasia_loja = st.session_state.nome_logado
    if not df_lojas_comerciante.empty:
        info_loja = df_lojas_comerciante[df_lojas_comerciante['usuario_dono'].astype(str).str.strip() == str(st.session_state.usuario_logado).strip()]
        if not info_loja.empty:
            nome_fantasia_loja = str(info_loja.iloc[0].get('nome_fantasia', st.session_state.nome_logado)).strip()

    with st.form("form_oferta", clear_on_submit=True):
        st.subheader("🚀 Lançar Nova Oferta")
        p_nome = st.text_input("Produto (Ex: Arroz 5kg)")
        
        c1, c2 = st.columns(2)
        with c1: p_de = st.text_input("Preço Normal (Opcional)")
        with c2: p_por = st.text_input("Preço Oferta (R$)")
        
        p_img = st.text_input("Link da Imagem (ImgBB)")
        
        # --- NOVO: BANNER FINANCEIRO COMPLETO ---
        st.info("💰 **Taxa de Lançamento: R$ 5,00** por anúncio (Validade 24h). Seu anúncio só será inserido em nossa plataforma após a confirmação do pagamento.\n\n**NOSSA CHAVE PIX: 81999642681** (Sandro Vitorino) BANCO BRADESCO.\n\n*Favor enviar o comprovante de pagamento para o mesmo número.*")
        
        btn_enviar = st.form_submit_button("Enviar Oferta", use_container_width=True, type="primary")
        
    if btn_enviar and p_nome and p_por:
        if qtd_hoje >= 5: st.error("❌ Limite atingido!")
        else:
            novo_id = gerar_id()
            if salvar_nova_oferta(st.session_state.usuario_logado, novo_id, p_nome, p_de, p_por, p_img):
                st.success(f"✅ Oferta enviada com sucesso! ID: {novo_id}")
                
                texto_zap = urllib.parse.quote(f"Nova Oferta recebida!\n\nID: *{novo_id}*\nLoja: *{nome_fantasia_loja}*\nProduto: *{p_nome}*\nPreço: *{p_por}*")
                st.markdown(f"<a href='https://wa.me/5581999642681?text={texto_zap}' target='_blank' style='display:block; background-color:#25D366; color:white; text-align:center; padding:15px; border-radius:8px; font-weight:bold; text-decoration:none; margin-top:10px; box-shadow: 0 4px 8px rgba(0,0,0,0.15);'>📲 Avisar Admin no WhatsApp (ID: {novo_id})</a>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🗑️ Gerenciar Ofertas")
    if not df_minhas.empty:
        minhas = df_minhas[df_minhas['usuario_loja'].astype(str).str.strip() == str(st.session_state.usuario_logado).strip()]
        for _, row in minhas.iterrows():
            c_info, c_btn = st.columns([4, 1])
            with c_info: st.write(f"📦 **{row.get('produto', '')}** — R$ {limpar_html(row.get('preco_por', ''))}")
            with c_btn:
                if st.button("❌", key=f"del_{row.get('id_oferta', '')}"):
                    if excluir_oferta_bd(row.get('id_oferta', '')): st.rerun()
