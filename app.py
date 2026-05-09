import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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
# --- 3. SISTEMA DE LOGIN COM VALIDAÇÃO DE PLANO ANUAL ---
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
                # VALIDAÇÃO DO PLANO ANUAL PARA COMERCIANTES
                if perfil == "comerciante":
                    vencimento_str = str(user_row.iloc[0].get('vencimento', '')).strip()
                    try:
                        data_venc = datetime.strptime(vencimento_str, "%d/%m/%Y")
                        if datetime.now() > data_venc:
                            st.error("🚫 A sua anuidade expirou! Renove o seu plano de R$ 120,00 com a administração para voltar a anunciar.")
                            return
                    except Exception:
                        st.warning("⚠️ Data de vencimento inválida no sistema. Contate o suporte.")
                        return

                st.session_state.usuario_logado = str(user_row.iloc[0]['usuario']).strip()
                st.session_state.nome_logado = str(user_row.iloc[0].get('nome', '')).strip()
                st.session_state.perfil_logado = perfil
                st.success("✅ Acesso Concedido!")
                st.rerun()
            else: st.warning("⏳ O seu cadastro está pendente de pagamento ou análise.")
        else: st.error("❌ Usuário ou senha incorretos.")
    else: st.warning("⚠️ Banco de dados sem conexão.")

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
    st.title("Descubra as melhores ofertas perto de você! 🛒")
    pesquisa = st.text_input("", placeholder="🔍 Digite o que você procura... (Ex: Leite, Dipirona, Cimento)", label_visibility="collapsed")
    filtro_categoria = st.radio("Filtro", ["🌎 Todas as Ofertas", "🛒 Alimentos", "💊 Farmácia", "🧱 Construção"], horizontal=True, label_visibility="collapsed")
    
    df_ofertas = carregar_tabela("Ofertas")
    df_lojas = carregar_tabela("Lojas")
    m = folium.Map(location=[-8.1189, -35.2925], zoom_start=14)
    
    if not df_ofertas.empty and not df_lojas.empty:
        # --- FILTRO 1: APENAS APROVADOS ---
        ofertas_ativas = df_ofertas[df_ofertas['status_pagamento'].astype(str).str.strip().str.lower() == 'aprovado']
        
        # --- FILTRO 2: APENAS OFERTAS NAS ÚLTIMAS 24H ---
        agora = datetime.now()
        ofertas_24h = []
        for _, row in ofertas_ativas.iterrows():
            try:
                data_postagem = datetime.strptime(str(row['data_hora']), "%Y-%m-%d %H:%M:%S")
                if (agora - data_postagem).total_seconds() <= 86400: # 86400 seg = 24 horas
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
                            
                            cor_pin, icone_pin = "red", "shopping-basket"
                            if categoria_loja.lower() in ["farmácia", "farmacia"]: cor_pin, icone_pin = "blue", "medkit"
                            elif categoria_loja.lower() in ["construção", "construcao"]: cor_pin, icone_pin = "orange", "hammer"
                                
                            produtos_da_loja = ofertas_ativas[ofertas_ativas['usuario_loja'] == usr_loja]
                            
                            html_popup = f"<div style='width:240px; font-family:sans-serif;'>"
                            html_popup += f"<h3 style='color:#0066cc; margin:0 0 10px 0; text-align:center; border-bottom:2px solid #0066cc;'>{nome_loja}</h3>"
                            
                            for _, row in produtos_da_loja.iterrows():
                                prod = row.get('produto', '')
                                p_de = row.get('preco_de', '')
                                p_por = row.get('preco_por', '')
                                img = row.get('link_imagem', '')
                                
                                html_popup += f"<div class='item-oferta'><p style='font-size:14px; font-weight:bold; margin:0;'>{prod}</p>"
                                if p_de: html_popup += f"<span style='font-size:11px; color:#888; text-decoration:line-through;'>De: R$ {p_de}</span> "
                                html_popup += f"<span style='color:#ff4b4b; font-weight:bold; font-size:15px;'>Por: R$ {p_por}</span>"
                                if img and img.startswith("http"): html_popup += f"<img src='{img}' style='width:100%; border-radius:5px; margin-top:5px;'>"
                                html_popup += "</div>"
                            
                            html_popup += "<div style='margin-top:15px;'>"
                            link_maps = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
                            html_popup += f"<a href='{link_maps}' target='_blank' style='display:inline-block; background-color:#ff4b4b; color:white; padding:8px 0; text-decoration:none; border-radius:5px; font-weight:bold; width:100%; text-align:center; margin-bottom:5px;'>📍 Chegar Lá (GPS)</a>"
                            
                            if zap_loja:
                                zap_limpo = "".join(filter(str.isdigit, zap_loja))
                                html_popup += f"<a href='https://wa.me/55{zap_limpo}?text=Olá! Vi suas ofertas no app No Precinho.' target='_blank' style='display:inline-block; background-color:#25D366; color:white; padding:8px 0; text-decoration:none; border-radius:5px; font-weight:bold; width:100%; text-align:center;'>💬 WhatsApp</a>"
                            
                            html_popup += f"<p style='font-size:9px; color:#888; margin-top:10px; text-align:center; line-height:1.2;'>* Ofertas válidas por 24h ou até durar o estoque.<br>Imagem meramente ilustrativa.</p></div></div>"
                            
                            folium.Marker([lat, lon], popup=folium.Popup(html_popup, max_width=260), tooltip=f"{nome_loja} ({len(produtos_da_loja)} ofertas)", icon=folium.Icon(color=cor_pin, icon=icone_pin, prefix='fa')).add_to(m)
                        except: pass 
                
    st_folium(m, width=1200, height=550, returned_objects=[])

elif st.session_state.perfil_logado == "admin":
    st.header("👑 Centro de Comando (Admin)")
    aba_ofertas, aba_lojas, aba_usuarios = st.tabs(["🛒 Gestão de Ofertas (R$ 5,00)", "🏪 Lojas", "👥 Usuários (Anuidade)"])
    
    with aba_ofertas:
        st.info("💡 Confirme o PIX de R$ 5,00 e mude o status para 'aprovado'.")
        df_ofertas_admin = carregar_tabela("Ofertas")
        if not df_ofertas_admin.empty:
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
            u_login = st.text_input("Nome de Usuário (Para Login)")
            u_senha = st.text_input("Senha (Para Login)")
            u_nome = st.text_input("Nome Completo do Dono")
            u_cid = st.text_input("Cidade")
            if st.form_submit_button("Enviar Cadastro do Dono", type="primary"):
                if u_login and u_senha:
                    if salvar_novo_usuario_vendedor(u_login, u_senha, u_nome, u_cid):
                        st.success(f"Comerciante {u_nome} enviado para análise!")
                else: st.error("Preencha Login e Senha.")
                
    with st.expander("🏪 2. Cadastrar Loja (Endereço e Mapa)", expanded=False):
        with st.form("form_nova_loja", clear_on_submit=True):
            l_dono = st.text_input("Usuário do Dono (O mesmo digitado acima)")
            l_nome = st.text_input("Nome Fantasia (Aparece no Mapa)")
            l_cat = st.selectbox("Categoria", ["Alimentos", "Farmácia", "Construção"])
            l_end = st.text_input("Endereço Completo")
            l_zap = st.text_input("WhatsApp (Só números)")
            l_inst = st.text_input("Instagram")
            st.warning("⚠️ DICA DE GPS: Use o formato -8.1234 usando PONTO. O sistema blindará sozinho com apóstrofo.")
            l_lat = st.text_input("Latitude (Ex: -8.1189)")
            l_lon = st.text_input("Longitude (Ex: -35.2925)")
            
            if st.form_submit_button("Enviar Dados da Loja", type="primary"):
                if l_dono and l_lat and l_lon:
                    if salvar_nova_loja_vendedor(l_dono, l_nome, l_end, l_zap, l_inst, l_lat, l_lon, l_cat):
                        st.success("Loja cadastrada com sucesso!")
                else: st.error("Dono e Coordenadas são obrigatórios!")

elif st.session_state.perfil_logado == "comerciante":
    st.header("🏪 Central do Comerciante")
    
    df_minhas = carregar_tabela("Ofertas")
    hoje_str = datetime.now().strftime("%Y-%m-%d")
    qtd_hoje = 0
    if not df_minhas.empty:
        df_hoje = df_minhas[(df_minhas['usuario_loja'].astype(str).str.strip() == str(st.session_state.usuario_logado).strip()) & (df_minhas['data_hora'].astype(str).str.startswith(hoje_str))]
        qtd_hoje = len(df_hoje)
        
    st.markdown(f"<div class='caixa-destaque'>💡 <b>O seu Limite Diário:</b> {qtd_hoje}/5 ofertas enviadas hoje.</div>", unsafe_allow_html=True)
    
    with st.form("form_oferta", clear_on_submit=True):
        st.subheader("🚀 Lançar Nova Oferta")
        p_nome = st.text_input("Produto (Ex: Arroz 5kg)")
        c1, c2 = st.columns(2)
        with c1: p_de = st.text_input("Preço Normal (R$)")
        with c2: p_por = st.text_input("Preço Oferta (R$)")
        p_img = st.text_input("Link da Imagem (ImgBB)")
        st.info("💰 Taxa de Lançamento: **R$ 5,00** por anúncio (Validade 24h). PIX SANDRO VITORINO: 81999642681")
        
        btn_enviar = st.form_submit_button("Enviar Oferta", use_container_width=True, type="primary")
        
    if btn_enviar:
        if qtd_hoje >= 5:
            st.error("❌ Limite de 5 ofertas diárias atingido! Volte amanhã para anunciar mais.")
        elif p_nome and p_por:
            if salvar_nova_oferta(st.session_state.usuario_logado, p_nome, p_de, p_por, p_img):
                st.success("✅ Oferta enviada para o painel do administrador com sucesso!")
                # BOTÃO DE AVISO RÁPIDO PARA O ADMIN VIA WHATSAPP (558199964261)
                texto_zap = f"Olá! Acabei de enviar uma nova oferta no app No Precinho (Produto: {p_nome}). Pode conferir o pagamento e liberar, por favor?"
                link_wa_admin = f"https://wa.me/558199964261?text={texto_zap.replace(' ', '%20')}"
                st.link_button("📲 Avisar Admin no WhatsApp para Aprovar", link_wa_admin, type="primary", use_container_width=True)

    st.markdown("---")
    st.subheader("🗑️ Gerenciar Minhas Ofertas (Ativas e Pendentes)")
    if not df_minhas.empty:
        minhas_totais = df_minhas[df_minhas['usuario_loja'].astype(str).str.strip() == str(st.session_state.usuario_logado).strip()]
        if not minhas_totais.empty:
            for _, row in minhas_totais.iterrows():
                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    st.write(f"📦 **{row.get('produto', '')}** — R$ {row.get('preco_por', '')} (Status: *{row.get('status_pagamento', '')}*)")
                with col_btn:
                    if st.button("❌ Excluir", key=f"del_{row.get('id_oferta', '')}", use_container_width=True):
                        with st.spinner("Apagando registro..."):
                            if excluir_oferta_bd(row.get('id_oferta', '')):
                                st.success("Removido!")
                                time.sleep(1)
                                st.rerun()
                st.markdown("<hr style='margin: 2px 0; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)
        else: st.info("Sem anúncios no momento.")
