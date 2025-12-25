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

# --- FUNÇÃO AUXILIAR PARA CORES NEON ---


def get_neon_color(treino_name):
    # Cores Neon vibrantes definidas no CSS :root
    if treino_name == "TREINO A":
        return "var(--neon-a)"
    if treino_name == "TREINO B":
        return "var(--neon-b)"
    if treino_name == "TREINO C":
        return "var(--neon-c)"
    if treino_name == "TREINO D":
        return "var(--neon-d)"
    if treino_name == "TREINO E":
        return "var(--neon-e)"
    if treino_name == "CARDIO":
        return "var(--neon-cardio)"
    if treino_name == "DESCANSO":
        return "var(--neon-rest)"
    return "#333"


# CSS Aprimorado (CORES SUAVIZADAS)
st.markdown("""
    <style>
    /* Definição das Cores Neon - SUAVIZADAS */
    :root {
        --neon-a: #00bcd4; /* Ciano mais calmo */
        --neon-b: #ffd700; /* Dourado */
        --neon-c: #32cd32; /* Verde Lima */
        --neon-d: #ff8c00; /* Laranja Escuro */
        --neon-e: #9932cc; /* Orquídea Escura */
        --neon-cardio: #ff1493; /* Deep Pink */
        --neon-rest: #cd5c5c; /* Vermelho Indiano (menos agressivo) */
    }

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
    
    /* Estilo do Calendário Visual */
    .day-header {
        font-weight: bold;
        text-align: center;
        padding: 8px;
        border-radius: 5px 5px 0 0;
        margin-bottom: 0px;
        color: black;
        text-transform: uppercase;
        font-size: 0.9em;
        /* Box shadow aplicado via Python para controle de cor */
    }
    .day-body {
        background-color: rgba(255,255,255,0.03);
        padding: 10px;
        border-radius: 0 0 5px 5px;
        font-size: 0.8em;
        min-height: 150px;
        border: 1px solid rgba(255,255,255,0.05);
        border-top: none;
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
    df_agenda_total = carregar_dados_direto("agenda")

    # Filtra dados do usuário
    df_f = df_corpo_total[df_corpo_total['Usuario'] == user_atual].copy()
    df_t_user = df_treinos_total[df_treinos_total['Usuario']
                                 == user_atual].copy()

    if not df_checkins_total.empty:
        df_c_user = df_checkins_total[df_checkins_total['Usuario'] == user_atual].copy(
        )
    else:
        df_c_user = pd.DataFrame(columns=["Usuario", "Data"])

    # Filtra Agenda do Usuário
    if not df_agenda_total.empty:
        df_a_user = df_agenda_total[df_agenda_total['Usuario']
                                    == user_atual].copy()
    else:
        df_a_user = pd.DataFrame()

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
    # NAVEGAÇÃO
    # =========================================================================

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

        # --- SUB-SEÇÃO: CHECK-IN ---
        col_check1, col_check2 = st.columns([3, 1])
        with col_check1:
            st.markdown("### 📅 Registro de Atividade")
            hoje_str = datetime.now().strftime("%d/%m/%Y")
            checkin_feito = False
            if not df_c_user.empty and hoje_str in df_c_user['Data'].values:
                checkin_feito = True

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

        # =====================================================================
        # === 📅 ÁREA DA AGENDA SEMANAL (CALENDÁRIO VISUAL) ===
        # =====================================================================
        st.subheader("📅 Cronograma Semanal")

        col_ag1, col_ag2 = st.columns([3, 1])
        col_ag1.caption(
            "Defina sua rotina. O calendário abaixo se atualizará automaticamente.")
        col_ag2.metric("Poder de Combate", f"{int(volume_total)} kg")

        # 1. Visualização do Calendário (Estilo Tabela Neon Suavizada)
        # Prepara dados padrão se não houver agenda
        dias_semana = ['Segunda', 'Terca', 'Quarta',
                       'Quinta', 'Sexta', 'Sabado', 'Domingo']

        rotina_display = {d: "DESCANSO" for d in dias_semana}
        if not df_a_user.empty:
            for d in dias_semana:
                if d in df_a_user.columns:
                    rotina_display[d] = df_a_user[d].iloc[0]

        cols_cal = st.columns(7)
        dias_display = {'Segunda': 'Seg', 'Terca': 'Ter', 'Quarta': 'Qua',
                        'Quinta': 'Qui', 'Sexta': 'Sex', 'Sabado': 'Sáb', 'Domingo': 'Dom'}

        for i, dia_key in enumerate(dias_semana):
            treino_dia = rotina_display[dia_key]
            cor_fundo = get_neon_color(treino_dia)

            with cols_cal[i]:
                # Cabeçalho com brilho neon reduzido (sem inset shadow forte)
                st.markdown(
                    f"""<div class='day-header' style='background-color: {cor_fundo}; box-shadow: 0 0 10px {cor_fundo};'>{dias_display[dia_key]}</div>""",
                    unsafe_allow_html=True
                )

                conteudo_html = ""
                if treino_dia != "DESCANSO":
                    conteudo_html += f"<strong>{treino_dia}</strong><br><hr style='margin:5px 0; border-color: rgba(255,255,255,0.1)'>"
                    treino_detalhes = df_t_user[df_t_user['Treino'] == treino_dia][[
                        'Exercicio', 'Series', 'Reps']]

                    if not treino_detalhes.empty:
                        for _, row in treino_detalhes.iterrows():
                            conteudo_html += f"<div style='margin-bottom:4px; line-height:1.2'><small>• {row['Exercicio']}<br><span style='color:#aaa'>({int(row['Series'])}x{int(row['Reps'])})</span></small></div>"
                    else:
                        conteudo_html += "<small>Vazio</small>"
                else:
                    # Emoji removido, apenas texto discreto ou vazio
                    conteudo_html += "<div style='text-align:center; padding-top:20px; color: #555'>Descanso</div>"

                st.markdown(
                    f"<div class='day-body'>{conteudo_html}</div>", unsafe_allow_html=True)

        # 2. Configuração da Agenda (EMBAIXO)
        with st.expander("⚙️ Editar Rotina Semanal", expanded=False):
            opcoes_treino_agenda = ["DESCANSO"] + \
                sorted(df_t_user['Treino'].unique().tolist())

            with st.form("form_agenda"):
                cols_cfg = st.columns(7)
                selecoes = {}
                for i, dia in enumerate(dias_semana):
                    with cols_cfg[i]:
                        val_atual = rotina_display[dia]
                        idx = opcoes_treino_agenda.index(
                            val_atual) if val_atual in opcoes_treino_agenda else 0
                        selecoes[dia] = st.selectbox(
                            dia[:3], options=opcoes_treino_agenda, index=idx)

                if st.form_submit_button("💾 Salvar Rotina"):
                    selecoes['Usuario'] = user_atual
                    novo_reg_agenda = pd.DataFrame([selecoes])
                    df_agenda_limpa = df_agenda_total[df_agenda_total['Usuario'] != user_atual]
                    updated_agenda = pd.concat(
                        [df_agenda_limpa, novo_reg_agenda])

                    conn.update(worksheet="agenda", data=updated_agenda)
                    st.cache_data.clear()
                    st.toast("Rotina atualizada!", icon="✅")
                    time.sleep(1)
                    st.rerun()

        st.divider()

        # --- EDITOR DE TREINOS ---
        with st.expander("🛠️ Forjar/Alterar Equipamentos (Exercícios)", expanded=False):
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
                            options=["TREINO A", "TREINO B", "TREINO C",
                                     "TREINO D", "TREINO E", "CARDIO"],
                            required=True
                        ),
                        "Exercicio": st.column_config.TextColumn("Habilidade", required=True),
                        "Series": st.column_config.NumberColumn("Sets", min_value=1, max_value=20, format="%d"),
                        "Reps": st.column_config.NumberColumn("Reps", min_value=1, max_value=100, format="%d"),
                        "KG": st.column_config.NumberColumn("Carga (kg)", min_value=0, step=0.5, format="%.1f kg"),
                    },
                    key="editor_treino"
                )
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

            if not df_t_user.empty:
                st.download_button("📜 Baixar Ficha (PDF)", data=gerar_pdf(
                    df_t_user), file_name="ficha_rpg.pdf", mime="application/pdf")

        # --- VISUALIZAÇÃO GERAL DOS TREINOS (ESTILO NEON CARD SUAVIZADO) ---
        st.divider()
        st.subheader("📋 Visualização da Ficha Completa")

        if not df_t_user.empty:
            treinos_unicos = sorted(df_t_user['Treino'].unique())
            if len(treinos_unicos) <= 3:
                cols = st.columns(len(treinos_unicos))
            else:
                cols = [st.container() for _ in range(len(treinos_unicos))]

            for i, treino in enumerate(treinos_unicos):
                df_subset = df_t_user[df_t_user['Treino'] == treino].drop(
                    columns=['Usuario', 'Treino'])
                df_display = df_subset.copy()
                df_display['Series'] = df_display['Series'].apply(
                    lambda x: f"{int(x)}")
                df_display['Reps'] = df_display['Reps'].apply(
                    lambda x: f"{int(x)}")
                df_display['KG'] = df_display['KG'].apply(lambda x: f"{x} kg")

                cor_header = get_neon_color(treino)

                container_usado = cols[i]

                with container_usado:
                    # ESTILO CARD (Sombra reduzida)
                    st.markdown(f"""
                        <div style="
                            border: 1px solid rgba(255,255,255,0.1);
                            border-left: 5px solid {cor_header};
                            box-shadow: -3px 0 10px {cor_header}, inset 0 0 5px rgba(0,0,0,0.5);
                            background-color: rgba(255, 255, 255, 0.03);
                            border-radius: 5px;
                            padding: 10px;
                            margin-bottom: 15px;
                        ">
                        <h4 style="margin: 0; padding-bottom: 10px; color: {cor_header}; text-shadow: 0 0 5px {cor_header};">{treino}</h4>
                    """, unsafe_allow_html=True)

                    st.dataframe(
                        df_display, use_container_width=True, hide_index=True)

                    st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Grimório vazio.")
