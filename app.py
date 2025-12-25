import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
import time
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da página e Estilo
st.set_page_config(page_title="Diário de Treino RPG",
                   page_icon="⚔️", layout="wide")

# --- FUNÇÃO DE CONEXÃO DIRETA COM CACHE ---


@st.cache_data(ttl=5)
def carregar_dados_direto(aba):
    """Lê os dados da planilha usando o link de exportação CSV direta"""
    spreadsheet_id = "1c7NZQWQv_gV9KFvSnFN8tQpUzJqpj8zEu_35aqTUWHg"
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={aba}"
    return pd.read_csv(url)

# --- CONFIGURAÇÃO DE SEGURANÇA ---


def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        col_c, _ = st.columns([1, 2])
        with col_c:
            st.title("🛡️ Login do Aventureiro")
            opcao_login = st.radio("Escolha uma opção:", [
                                   "Entrar", "Criar Conta"], horizontal=True)

            if opcao_login == "Criar Conta":
                st.info("O cadastro requer conexão com a Guilda (Nuvem).")
                novo_u = st.text_input("Escolha um Nome de Herói", key="reg_u")
                novo_p = st.text_input(
                    "Escolha uma Senha", type="password", key="reg_p")

                if st.button("Jurar Bandeira"):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_users = carregar_dados_direto("usuarios")

                    if novo_u in df_users['Usuario'].values:
                        st.error("Este herói já existe nas lendas!")
                    else:
                        novo_reg = pd.DataFrame(
                            [{"Usuario": novo_u, "Senha": str(novo_p)}])
                        updated_users = pd.concat([df_users, novo_reg])
                        conn.update(worksheet="usuarios", data=updated_users)
                        st.cache_data.clear()
                        st.success("Conta criada! Mude para a opção 'Entrar'.")

            else:  # Opção Entrar
                with st.form("login_form"):
                    user = st.text_input("Nome do Herói", key="log_u")
                    senha = st.text_input(
                        "Senha", type="password", key="log_p")
                    submit_login = st.form_submit_button(
                        "Entrar na Masmorra", type="primary")

                if submit_login:
                    try:
                        df_users = carregar_dados_direto("usuarios")
                        df_users['Senha'] = df_users['Senha'].astype(str)
                        validado = df_users[(df_users['Usuario'] == user) & (
                            df_users['Senha'] == str(senha))]

                        if not validado.empty:
                            st.session_state["autenticado"] = True
                            st.session_state["usuario"] = user
                            st.rerun()
                        else:
                            st.error("Credenciais inválidas!")
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")
        return False
    return True

# --- LÓGICA DE GAMIFICATION (RPG) ---


def calcular_status_rpg(df_evolucao, volume_total):
    # XP Baseado em Logs (Consistência) + Volume (Força)
    qtd_logs = len(df_evolucao)
    xp_logs = qtd_logs * 150  # Cada pesagem vale 150 XP
    xp_forca = int(volume_total * 0.1)  # 10% do volume vira XP

    total_xp = xp_logs + xp_forca

    # Sistema de Nível (Curva simples: a cada 1000xp sobe)
    nivel = 1 + int(total_xp / 1000)
    xp_atual_nivel = total_xp % 1000
    xp_proximo = 1000

    # Lógica de Títulos e Ícones (Avatares) baseada na imagem
    if nivel < 5:
        titulo = "Aldeão Iniciante"
        icone = "👨‍🌾"  # Aldeão com chapéu de palha
    elif nivel < 10:
        titulo = "Escudeiro Determinado"
        icone = "🗡️"  # Adaga/Espada curta
    elif nivel < 20:
        titulo = "Guerreiro de Bronze"
        icone = "⚔️"  # Espadas cruzadas
    elif nivel < 40:
        titulo = "Cavaleiro de Prata"
        icone = "🏇"  # Cavaleiro montado
    elif nivel < 60:
        titulo = "Senhor da Guerra"
        icone = "👹"  # Máscara Oni (Lembra elmo escuro/agressivo)
    else:
        titulo = "Divindade do Ferro"
        icone = "⚡"  # Poder divino

    return nivel, total_xp, xp_atual_nivel, xp_proximo, titulo, icone


# CSS Aprimorado (Tema Dark RPG)
st.markdown("""
    <style>
    /* Cores gerais */
    .stApp { background-color: #0e1117; }
    
    /* Métricas estilo HUD */
    [data-testid="stMetricValue"] { color: #00ffca !important; text-shadow: 0px 0px 10px rgba(0,255,202,0.5); font-family: 'Courier New', monospace; }
    .stMetric { background-color: rgba(20, 20, 40, 0.8); padding: 10px; border: 1px solid #4B0082; border-radius: 5px; box-shadow: 0 0 10px rgba(75, 0, 130, 0.2); }
    
    /* Barra de progresso customizada */
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #4B0082, #00ffca); }
    
    /* Botões */
    div.stButton > button:first-child { background-color: #2e004f; color: #d4d4d4; border: 1px solid #6A0DAD; }
    div.stButton > button:first-child:hover { background-color: #00ffca; color: black; border-color: white; box-shadow: 0px 0px 15px #00ffca; }
    
    /* Estilo do Avatar */
    .avatar-icon {
        font-size: 80px;
        text-align: center;
        line-height: 1.2;
        filter: drop-shadow(0 0 10px #00ffca);
    }
    </style>
    """, unsafe_allow_html=True)

if verificar_senha():
    conn = st.connection("gsheets", type=GSheetsConnection)
    user_atual = st.session_state["usuario"]

    # --- CARREGAMENTO INICIAL DE DADOS (PARA CALCULAR O RPG ANTES DE TUDO) ---
    df_corpo_total = carregar_dados_direto("evolucao")
    df_treinos_total = carregar_dados_direto("treinos")

    # Filtra dados do usuário
    df_f = df_corpo_total[df_corpo_total['Usuario'] == user_atual].copy()
    df_t_user = df_treinos_total[df_treinos_total['Usuario']
                                 == user_atual].copy()

    # Cálculo preliminar de volume para o RPG
    try:
        for col in ['Series', 'Reps', 'KG']:
            df_t_user[col] = pd.to_numeric(df_t_user[col].astype(
                str).str.replace(',', '.'), errors='coerce').fillna(0)
        volume_total = (df_t_user['Series'] *
                        df_t_user['Reps'] * df_t_user['KG']).sum()
    except:
        volume_total = 0

    # Calcula Stats RPG (Agora retorna o ícone também)
    nivel, total_xp, xp_atual, xp_prox, titulo, icone = calcular_status_rpg(
        df_f, volume_total)

    # --- HUD DO JOGADOR (HEADER) ---
    # Container estilizado no topo
    with st.container():
        c_avatar, c_stats, c_logout = st.columns([1, 6, 1])

        with c_avatar:
            # Renderiza o ícone grande usando HTML para ficar visualmente impactante
            st.markdown(
                f"<div class='avatar-icon'>{icone}</div>", unsafe_allow_html=True)

        with c_stats:
            st.markdown(f"### {user_atual} | Lvl {nivel} - *{titulo}*")
            col_xp, col_bar = st.columns([1, 4])
            col_xp.caption(f"XP: {xp_atual}/{xp_prox}")
            col_bar.progress(xp_atual / xp_prox)

        with c_logout:
            st.write("")  # Espaçamento
            if st.button("🚪 Sair"):
                st.session_state["autenticado"] = False
                st.rerun()

    st.divider()

    # --- FUNÇÃO GERAR PDF ---
    def gerar_pdf(df):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(
            200, 10, f"FICHA DE PERSONAGEM - {user_atual}", ln=True, align='C')
        pdf.ln(10)
        for treino in sorted(df['Treino'].unique()):
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(0, 10, f" >> {treino}", ln=True, fill=True)
            df_t = df[df['Treino'] == treino]
            pdf.set_font("Arial", '', 10)
            for _, row in df_t.iterrows():
                linha = f"[ ] {row['Exercicio']} | {row['Series']}x{row['Reps']} | Carga: {row['KG']}kg"
                pdf.cell(0, 8, linha, ln=True)
            pdf.ln(4)
        saida = pdf.output(dest='S')
        return saida.encode('latin-1') if isinstance(saida, str) else bytes(saida)

    # --- ÁREA PRINCIPAL COM ABAS ---
    aba1, aba2 = st.tabs(["📜 Atributos & Evolução", "⚔️ Grimório de Treino"])

    # --- ABA 1: EVOLUÇÃO ---
    with aba1:
        c_kpi1, c_kpi2 = st.columns([2, 1])
        c_kpi1.subheader("Atributos Corporais")

        with st.expander("📝 Registrar Novo Status (Save Game)", expanded=False):
            with st.form("entrada_dados", clear_on_submit=True):
                col1, col2 = st.columns(2)
                peso = col1.number_input("Peso (kg)", 30.0, 200.0, 70.0)
                altura = col2.number_input("Altura (m)", 1.0, 2.5, 1.75)
                if st.form_submit_button("💾 Salvar Progresso"):
                    novo = pd.DataFrame([{
                        "Usuario": user_atual,
                        "Data": datetime.now().strftime("%d/%m/%Y"),
                        "Peso": peso,
                        "Altura": altura,
                        "IMC": round(peso/(altura**2), 2)
                    }])
                    updated_corpo = pd.concat([df_corpo_total, novo])
                    conn.update(worksheet="evolucao", data=updated_corpo)
                    st.cache_data.clear()
                    st.toast("XP Adquirido! Dados salvos.", icon="✨")
                    time.sleep(1)
                    st.rerun()

        if not df_f.empty:
            # Tratamento de dados
            try:
                p_ini = float(str(df_f['Peso'].iloc[0]).replace(',', '.'))
                p_at = float(str(df_f['Peso'].iloc[-1]).replace(',', '.'))
                imc_raw = df_f['IMC'].iloc[-1]
                imc_atual = float(str(imc_raw).replace(',', '.'))
            except:
                p_ini, p_at, imc_atual = 0.0, 0.0, 0.0

            evol = p_at - p_ini

            # Lógica do Status do IMC (HP Bar Logic)
            if imc_atual < 18.5:
                status, icon, cor_imc = "Buff de Agilidade (Leve)", "⚠️", "yellow"
            elif imc_atual < 25:
                status, icon, cor_imc = "Balanceado (Ideal)", "✅", "green"
            elif imc_atual < 30:
                status, icon, cor_imc = "Tank (Sobrepeso)", "🛡️", "orange"
            else:
                status, icon, cor_imc = "Heavy Tank (Obesidade)", "🚨", "red"

            # EXIBIÇÃO DAS MÉTRICAS
            m1, m2, m3 = st.columns(3)
            m1.metric("Peso Inicial", f"{p_ini}kg")
            m2.metric("Peso Atual", f"{p_at}kg", delta=f"{evol:.1f}kg")
            m3.metric("Build Atual (IMC)",
                      f"{imc_atual:.2f}", delta=f"{icon} {status}", delta_color="off")

            st.caption("Histórico de Loot (Peso)")
            st.area_chart(df_f, x="Data", y="Peso", color="#6A0DAD")
        else:
            st.info(
                "Sua jornada começa agora. Registre seu peso acima para ganhar XP!")

    # --- ABA 2: TREINOS ---
    with aba2:
        col_t1, col_t2 = st.columns([3, 1])
        col_t1.subheader("⚔️ Grimório de Batalha (Ficha)")
        col_t2.metric("Poder de Combate (Volume)", f"{int(volume_total)} kg")

        # --- ÁREA DE EDIÇÃO ---
        with st.expander("🛠️ Forjar/Alterar Equipamentos (Exercícios)", expanded=False):
            st.caption(
                "Edite seus exercícios. Aumentar a carga aumenta seu XP passivo!")
            df_ed = st.data_editor(
                df_t_user.drop(columns=["Usuario"]),
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "Treino": st.column_config.SelectboxColumn("Missão", options=["TREINO A", "TREINO B", "TREINO C", "BOSS RUSH (CARDIO)"], required=True),
                    "Exercicio": st.column_config.TextColumn("Habilidade", required=True),
                    "Series": st.column_config.NumberColumn("Sets", min_value=1, max_value=20, format="%d"),
                    "Reps": st.column_config.NumberColumn("Reps", min_value=1, max_value=100, format="%d"),
                    "KG": st.column_config.NumberColumn("Carga (kg)", min_value=0, step=0.5, format="%.1f kg"),
                },
                key="editor_treino"
            )

            c1, c2 = st.columns(2)
            if c1.button("💾 Salvar Alterações", use_container_width=True):
                df_ed["Usuario"] = user_atual
                df_outros = df_treinos_total[df_treinos_total['Usuario']
                                             != user_atual]
                updated_treinos = pd.concat([df_outros, df_ed])
                conn.update(worksheet="treinos", data=updated_treinos)
                st.cache_data.clear()
                st.toast("Grimório atualizado com sucesso!", icon="✨")
                time.sleep(1)
                st.rerun()

            if not df_t_user.empty:
                c2.download_button("📜 Exportar Pergaminho (PDF)", data=gerar_pdf(
                    df_t_user), file_name="ficha_rpg.pdf", mime="application/pdf", use_container_width=True)

        # --- VISUALIZAÇÃO ---
        st.divider()
        if df_t_user.empty:
            st.info("Seu grimório está vazio. Adicione habilidades acima.")
        else:
            treinos_unicos = sorted(df_t_user['Treino'].unique())
            cols = st.columns(len(treinos_unicos)) if len(
                treinos_unicos) > 0 else [st.container()]

            for i, treino in enumerate(treinos_unicos):
                df_subset = df_t_user[df_t_user['Treino'] == treino].drop(
                    columns=['Usuario', 'Treino'])

                # Formatação visual para tabela
                df_display = df_subset.copy()
                df_display['Series'] = df_display['Series'].apply(
                    lambda x: f"{int(x)}")
                df_display['Reps'] = df_display['Reps'].apply(
                    lambda x: f"{int(x)}")
                df_display['KG'] = df_display['KG'].apply(lambda x: f"{x} kg")

                container = cols[i] if len(
                    treinos_unicos) <= 3 else st.container()

                with container:
                    st.markdown(f"#### 🛡️ {treino}")
                    st.dataframe(
                        df_display, use_container_width=True, hide_index=True)
