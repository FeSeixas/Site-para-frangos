import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
import io
import time
import altair as alt
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da página e Estilo
st.set_page_config(page_title="Diário de Treino RPG",
                   page_icon="⚔️", layout="wide")

# --- FUNÇÃO DE CONEXÃO DIRETA COM CACHE ---


@st.cache_data(ttl=5)
def carregar_dados_direto(aba):
    """Lê os dados da planilha usando o link de exportação CSV direta"""
    try:
        spreadsheet_id = "1c7NZQWQv_gV9KFvSnFN8tQpUzJqpj8zEu_35aqTUWHg"
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={aba}"
        return pd.read_csv(url)
    except:
        return pd.DataFrame()  # Retorna vazio se a aba não existir ainda

# --- CONFIGURAÇÃO DE SEGURANÇA ---


def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        col_c, _ = st.columns([1, 2])
        with col_c:
            st.title("🛡️ Login do Aventureiro")
            opcao_login = st.radio("Escolha uma opção:", [
                                   "Entrar", "Se listar na Guilda"], horizontal=True)

            if opcao_login == "Se listar na Guilda":
                st.info("O cadastro requer conexão com a Guilda (Nuvem).")
                novo_u = st.text_input("Escolha um Nome de Herói", key="reg_u")
                novo_p = st.text_input(
                    "Escolha uma Senha", type="password", key="reg_p")

                if st.button("Jurar Bandeira"):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_users = carregar_dados_direto("usuarios")

                    if not df_users.empty and novo_u in df_users['Usuario'].values:
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
                        if not df_users.empty:
                            df_users['Senha'] = df_users['Senha'].astype(str)
                            validado = df_users[(df_users['Usuario'] == user) & (
                                df_users['Senha'] == str(senha))]

                            if not validado.empty:
                                st.session_state["autenticado"] = True
                                st.session_state["usuario"] = user
                                st.rerun()
                            else:
                                st.error("Credenciais inválidas!")
                        else:
                            st.error("Erro ao carregar usuários.")
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")
        return False
    return True

# --- LÓGICA DE GAMIFICATION (RPG) ---


def calcular_status_rpg(df_evolucao, volume_total, df_checkins):
    qtd_marcos_validos = 0
    ultima_data_marco = None

    if not df_evolucao.empty:
        try:
            df_calc = df_evolucao.copy()
            df_calc['Data_dt'] = pd.to_datetime(
                df_calc['Data'], dayfirst=True, errors='coerce')
            df_calc = df_calc.sort_values('Data_dt', ascending=True)
            datas_validas = df_calc['Data_dt'].dropna().tolist()

            if datas_validas:
                qtd_marcos_validos = 1
                ultima_data_marco = datas_validas[0]
                for data in datas_validas[1:]:
                    diferenca = (data - ultima_data_marco).days
                    if diferenca >= 7:
                        qtd_marcos_validos += 1
                        ultima_data_marco = data
        except Exception:
            qtd_marcos_validos = len(df_evolucao)

    xp_logs = qtd_marcos_validos * 150
    xp_forca = int(volume_total * 0.1)
    qtd_checkins = len(df_checkins)
    xp_checkin = qtd_checkins * 25

    total_xp = xp_logs + xp_forca + xp_checkin

    nivel = 1 + int(total_xp / 1000)
    xp_atual_nivel = total_xp % 1000
    xp_proximo = 1000

    if nivel < 5:
        titulo = "Aldeão Iniciante"
        icone = "👨‍🌾"
    elif nivel < 10:
        titulo = "Escudeiro Determinado"
        icone = "🗡️"
    elif nivel < 20:
        titulo = "Guerreiro de Bronze"
        icone = "⚔️"
    elif nivel < 40:
        titulo = "Cavaleiro de Prata"
        icone = "🏇"
    elif nivel < 60:
        titulo = "Senhor da Guerra"
        icone = "👹"
    else:
        titulo = "Divindade do Ferro"
        icone = "⚡"

    return nivel, total_xp, xp_atual_nivel, xp_proximo, titulo, icone, ultima_data_marco


# CSS Aprimorado
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    [data-testid="stMetricValue"] { color: #00ffca !important; text-shadow: 0px 0px 10px rgba(0,255,202,0.5); font-family: 'Courier New', monospace; }
    .stMetric { background-color: rgba(20, 20, 40, 0.8); padding: 10px; border: 1px solid #4B0082; border-radius: 5px; box-shadow: 0 0 10px rgba(75, 0, 130, 0.2); }
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #4B0082, #00ffca); }
    div.stButton > button:first-child { background-color: #2e004f; color: #d4d4d4; border: 1px solid #6A0DAD; }
    div.stButton > button:first-child:hover { background-color: #00ffca; color: black; border-color: white; box-shadow: 0px 0px 15px #00ffca; }
    .avatar-icon { font-size: 80px; text-align: center; line-height: 1.2; filter: drop-shadow(0 0 10px #00ffca); }
    
    /* Estilo para a Navegação (Radio horizontal) */
    div[data-testid="stRadio"] > div {
        display: flex;
        justify-content: center;
        gap: 20px;
        background-color: rgba(255, 255, 255, 0.05);
        padding: 10px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

if verificar_senha():
    conn = st.connection("gsheets", type=GSheetsConnection)
    user_atual = st.session_state["usuario"]

    # --- CARREGAMENTO DE DADOS ---
    df_corpo_total = carregar_dados_direto("evolucao")
    df_treinos_total = carregar_dados_direto("treinos")
    df_checkins_total = carregar_dados_direto("checkins")

    # Filtra dados do usuário
    df_f = df_corpo_total[df_corpo_total['Usuario'] == user_atual].copy()
    df_t_user = df_treinos_total[df_treinos_total['Usuario']
                                 == user_atual].copy()

    if not df_checkins_total.empty:
        df_c_user = df_checkins_total[df_checkins_total['Usuario'] == user_atual].copy(
        )
    else:
        df_c_user = pd.DataFrame(columns=["Usuario", "Data"])

    # Cálculo preliminar de volume
    try:
        for col in ['Series', 'Reps', 'KG']:
            df_t_user[col] = pd.to_numeric(df_t_user[col].astype(
                str).str.replace(',', '.'), errors='coerce').fillna(0)
        volume_total = (df_t_user['Series'] *
                        df_t_user['Reps'] * df_t_user['KG']).sum()
    except:
        volume_total = 0

    # Calcula Stats RPG
    nivel, total_xp, xp_atual, xp_prox, titulo, icone, ultima_data_xp = calcular_status_rpg(
        df_f, volume_total, df_c_user)

    # --- HUD DO JOGADOR ---
    with st.container():
        c_avatar, c_stats, c_logout = st.columns([1, 6, 1])
        with c_avatar:
            st.markdown(
                f"<div class='avatar-icon'>{icone}</div>", unsafe_allow_html=True)
        with c_stats:
            st.markdown(f"### {user_atual} | Lvl {nivel} - *{titulo}*")
            col_xp, col_bar = st.columns([1, 4])
            col_xp.caption(f"XP: {xp_atual}/{xp_prox}")
            col_bar.progress(xp_atual / xp_prox)
        with c_logout:
            st.write("")
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

    # =========================================================================
    # SUBSTITUIÇÃO DAS ABAS POR NAVEGAÇÃO PERSISTENTE (RADIO)
    # =========================================================================

    # Menu de navegação que lembra onde você clicou
    aba_selecionada = st.radio(
        "",
        ["📜 Atributos & Evolução", "⚔️ Grimório de Treino"],
        horizontal=True,
        label_visibility="collapsed"
    )

    # --- CONTEÚDO DA ABA 1: EVOLUÇÃO ---
    if aba_selecionada == "📜 Atributos & Evolução":
        c_kpi1, c_kpi2 = st.columns([2, 1])
        c_kpi1.subheader("Atributos Corporais")

        # Cooldown de 7 dias
        xp_disponivel = True
        dias_restantes = 0
        hoje_dt = datetime.now()

        if ultima_data_xp is not None:
            diff = hoje_dt - ultima_data_xp
            if diff.days < 7:
                xp_disponivel = False
                dias_restantes = 7 - diff.days

        # 1. Área de Registro
        with st.expander("📝 Registrar Novo Status (Save Game)", expanded=False):
            if xp_disponivel:
                st.success("✨ Recompensa Semanal Disponível! (+150 XP)")
                lbl_botao = "💾 Salvar e Ganhar XP"
            else:
                st.info(
                    f"⏳ XP em recarga. Próxima recompensa em {dias_restantes} dias. (Você pode atualizar sem XP)")
                lbl_botao = "💾 Atualizar Dados (Sem XP)"

            with st.form("entrada_dados", clear_on_submit=True):
                col1, col2 = st.columns(2)
                peso = col1.number_input("Peso (kg)", 30.0, 200.0, 70.0)
                altura = col2.number_input("Altura (m)", 1.0, 2.5, 1.75)

                if st.form_submit_button(lbl_botao):
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

                    if xp_disponivel:
                        st.toast("Marco alcançado! +150 XP!", icon="🎉")
                    else:
                        st.toast("Dados atualizados!", icon="📝")
                    time.sleep(1)
                    st.rerun()

        # 2. Editor de Histórico
        with st.expander("✏️ Corrigir Histórico de Peso", expanded=False):
            st.caption(
                "Edite valores errados ou exclua linhas selecionando e apertando 'Del'.")

            df_editavel = st.data_editor(
                df_f,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Data": st.column_config.TextColumn("Data", disabled=False),
                    "Peso": st.column_config.NumberColumn("Peso (kg)", format="%.1f"),
                    "Altura": st.column_config.NumberColumn("Altura (m)", format="%.2f"),
                    "IMC": st.column_config.NumberColumn("IMC", disabled=True)
                },
                key="editor_evolucao"
            )

            if st.button("💾 Salvar Correções no Histórico"):
                try:
                    df_editavel["IMC"] = df_editavel.apply(
                        lambda x: round(x["Peso"]/(x["Altura"]**2), 2), axis=1)
                except:
                    pass

                df_outros_users = df_corpo_total[df_corpo_total['Usuario'] != user_atual]
                df_final = pd.concat([df_outros_users, df_editavel])

                conn.update(worksheet="evolucao", data=df_final)
                st.cache_data.clear()
                st.toast("Histórico corrigido!", icon="✅")
                time.sleep(1)
                st.rerun()

        # 3. Visualização (GRÁFICO ALTAIR)
        if not df_f.empty:
            try:
                p_ini = float(str(df_f['Peso'].iloc[0]).replace(',', '.'))
                p_at = float(str(df_f['Peso'].iloc[-1]).replace(',', '.'))
                imc_raw = df_f['IMC'].iloc[-1]
                imc_atual = float(str(imc_raw).replace(',', '.'))
            except:
                p_ini, p_at, imc_atual = 0.0, 0.0, 0.0
            evol = p_at - p_ini

            if imc_atual < 18.5:
                status, icon = "Buff de Agilidade", "⚠️"
            elif imc_atual < 25:
                status, icon = "Balanceado", "✅"
            elif imc_atual < 30:
                status, icon = "Tank", "🛡️"
            else:
                status, icon = "Heavy Tank", "🚨"

            m1, m2, m3 = st.columns(3)
            m1.metric("Peso Inicial", f"{p_ini}kg")
            m2.metric("Peso Atual", f"{p_at}kg", delta=f"{evol:.1f}kg")
            m3.metric("Build Atual (IMC)",
                      f"{imc_atual:.2f}", delta=f"{icon} {status}", delta_color="off")

            # GRÁFICO
            st.markdown("### 📊 Gráfico de Evolução")
            df_chart = df_f.copy()
            df_chart['Data_dt'] = pd.to_datetime(
                df_chart['Data'], dayfirst=True, errors='coerce')

            base = alt.Chart(df_chart).encode(
                x=alt.X('Data_dt:T', title='Data',
                        axis=alt.Axis(format='%d/%m/%Y')),
                tooltip=[
                    alt.Tooltip('Data', title='Data Registro'),
                    alt.Tooltip('Peso', title='Peso (kg)'),
                    alt.Tooltip('IMC', title='IMC')
                ]
            ).properties(height=350)

            area = base.mark_area(
                line={'color': '#6A0DAD'},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#6A0DAD', offset=0),
                           alt.GradientStop(color='rgba(106, 13, 173, 0.1)', offset=1)],
                    x1=1, x2=1, y1=1, y2=0
                )
            ).encode(y=alt.Y('Peso:Q', title='Peso (kg)', scale=alt.Scale(zero=False)))

            points = base.mark_circle(
                size=80, color='#00ffca').encode(y='Peso:Q')

            chart_final = (area + points).interactive()
            st.altair_chart(chart_final, use_container_width=True)
        else:
            st.info(
                "Sua jornada começa agora. Registre seu peso acima para ganhar XP!")

    # --- CONTEÚDO DA ABA 2: TREINOS ---
    elif aba_selecionada == "⚔️ Grimório de Treino":
        col_t1, col_t2 = st.columns([3, 1])
        col_t1.subheader("⚔️ Grimório de Batalha (Ficha)")
        col_t2.metric("Poder de Combate (Volume)", f"{int(volume_total)} kg")

        # --- CHECK-IN DIÁRIO ---
        st.divider()
        hoje_str = datetime.now().strftime("%d/%m/%Y")

        if not df_c_user.empty and hoje_str in df_c_user['Data'].values:
            checkin_feito = True
        else:
            checkin_feito = False

        col_check1, col_check2 = st.columns([3, 1])
        with col_check1:
            st.markdown("### 📅 Registro de Atividade")
            if checkin_feito:
                st.success(
                    f"✅ Treino de hoje ({hoje_str}) registrado! +25 XP ganhos.")
            else:
                st.warning("⚠️ Você ainda não registrou seu treino hoje.")
                if st.button("🔥 Confirmar Treino do Dia (+25 XP)"):
                    novo_checkin = pd.DataFrame(
                        [{"Usuario": user_atual, "Data": hoje_str}])
                    updated_checkins = pd.concat(
                        [df_checkins_total, novo_checkin])
                    conn.update(worksheet="checkins", data=updated_checkins)
                    st.cache_data.clear()
                    st.toast("Check-in realizado! +25 XP!", icon="🎉")
                    time.sleep(1)
                    st.rerun()

        with col_check2:
            dias_treinados = len(df_c_user)
            st.metric("Dias Treinados", dias_treinados, delta="Total")

        if not df_c_user.empty:
            with st.expander("📆 Ver Histórico de Datas"):
                st.dataframe(df_c_user[['Data']].sort_values(
                    by='Data', ascending=False), use_container_width=True, hide_index=True)

        st.divider()

        # --- EDITOR DE TREINOS COM PROTEÇÃO DE RELOAD (ST.FORM) ---
        with st.expander("🛠️ Forjar/Alterar Equipamentos (Exercícios)", expanded=False):

            # INICIO DO FORMULÁRIO (Evita reload a cada clique)
            with st.form("form_editor_treino"):
                st.caption(
                    "Edite à vontade. O sistema só atualizará quando clicar em 'Salvar Alterações'.")

                df_ed = st.data_editor(
                    df_t_user.drop(columns=["Usuario"]),
                    use_container_width=True,
                    num_rows="dynamic",
                    column_config={
                        "Treino": st.column_config.SelectboxColumn(
                            "Missão",
                            options=[
                                "TREINO A",
                                "TREINO B",
                                "TREINO C",
                                "TREINO D",
                                "TREINO E",
                                "CARDIO"
                            ],
                            required=True
                        ),
                        "Exercicio": st.column_config.TextColumn("Habilidade", required=True),
                        "Series": st.column_config.NumberColumn("Sets", min_value=1, max_value=20, format="%d"),
                        "Reps": st.column_config.NumberColumn("Reps", min_value=1, max_value=100, format="%d"),
                        "KG": st.column_config.NumberColumn("Carga (kg)", min_value=0, step=0.5, format="%.1f kg"),
                    },
                    key="editor_treino"
                )

                # Botão de submit dentro do form
                c_submit, _ = st.columns([1, 2])
                submit_btn = c_submit.form_submit_button(
                    "💾 Salvar Alterações", type="primary")

                if submit_btn:
                    df_ed["Usuario"] = user_atual
                    df_outros = df_treinos_total[df_treinos_total['Usuario']
                                                 != user_atual]
                    updated_treinos = pd.concat([df_outros, df_ed])
                    conn.update(worksheet="treinos", data=updated_treinos)
                    st.cache_data.clear()
                    st.toast("Grimório atualizado!", icon="✨")
                    time.sleep(1)
                    st.rerun()

            # PDF fora do form
            if not df_t_user.empty:
                st.download_button("📜 Baixar Ficha (PDF)", data=gerar_pdf(
                    df_t_user), file_name="ficha_rpg.pdf", mime="application/pdf")

        st.divider()
        if not df_t_user.empty:
            treinos_unicos = sorted(df_t_user['Treino'].unique())
            cols = st.columns(len(treinos_unicos)) if len(
                treinos_unicos) > 0 else [st.container()]
            for i, treino in enumerate(treinos_unicos):
                df_subset = df_t_user[df_t_user['Treino'] == treino].drop(
                    columns=['Usuario', 'Treino'])
                df_display = df_subset.copy()
                df_display['Series'] = df_display['Series'].apply(
                    lambda x: f"{int(x)}")
                df_display['Reps'] = df_display['Reps'].apply(
                    lambda x: f"{int(x)}")
                df_display['KG'] = df_display['KG'].apply(lambda x: f"{x} kg")
                with cols[i] if len(treinos_unicos) <= 3 else st.container():
                    st.markdown(f"#### 🛡️ {treino}")
                    st.dataframe(
                        df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Grimório vazio.")
