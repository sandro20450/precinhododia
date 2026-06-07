import streamlit as st
import pandas as pd
import uuid
import urllib.parse
from datetime import datetime

# --- Configurações Iniciais ---
st.set_page_config(page_title="No Precinho", page_icon="noprecinho.png", layout="wide")

# --- Função Geradora de ID ---
def gerar_id():
    return f"OP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

# --- Alterações Visuais e Banner ---
def exibir_banner_comercial():
    msg = "🚀 Quer fazer parte do nosso aplicativo? Fale conosco agora!"
    link = "https://wa.me/5581999642681?text=Olá! Quero anunciar no No Precinho."
    st.markdown(f"""
        <div style="background-color:#007bff; padding:15px; border-radius:10px; text-align:center;">
            <a href='{link}' target='_blank' style='color:white; font-size:18px; font-weight:bold; text-decoration:none;'>{msg}</a>
        </div>
    """, unsafe_allow_html=True)

# --- Exemplo de como usar no código de envio da oferta ---
# Dentro da função que salva a oferta, adicione:
# novo_id = gerar_id()
# ... salvar na planilha ...
# E na hora de montar a mensagem do WhatsApp:
# texto_zap = urllib.parse.quote(f"Nova Oferta ID: {novo_id}. Loja: {loja}...")
