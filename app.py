import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import altair as alt
from streamlit_gsheets import GSheetsConnection
import time

# 1. Configuração da página
st.set_page_config(page_title="Life RPG", page_icon="🐉", layout="wide")

# --- FUNÇÕES AUXILIARES ---


@st.cache_data(ttl=5)
def carregar_dados_direto(aba):
    try:
        # Substitua pelo ID da sua planilha se necessário
        spreadsheet_id = "1c7NZQWQv_gV9KFvSnFN8tQpUzJqpj8zEu_35aqTUWHg"
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={aba}"
        return pd.read_csv(url)
    except:
        return pd.DataFrame()


def gerar_pdf(df, user_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"FICHA DE PERSONAGEM - {user_name}", ln=True, align='C')
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


def get_neon_color(treino_name):
    if treino_name == "TREINO A":
        return "var(--neon-blue)"
    if treino_name == "TREINO B":
        return "var(--neon-gold)"
    if treino_name == "TREINO C":
        return "var(--neon-green)"
    if treino_name == "TREINO D":
        return "var(--neon-orange)"
    if treino_name == "TREINO E":
        return "var(--neon-purple)"
    if treino_name == "CARDIO":
        return "var(--neon-pink)"
    if treino_name == "DESCANSO":
        return "var(--neon-red)"
    return "#333"


def calcular_status_rpg(df_evolucao, volume_total, df_checkins, df_estudos):
    # 1. FORÇA (STR)
    qtd_marcos = 0
    ultima_data = None
    if not df_evolucao.empty:
        try:
            df_c = df_evolucao.copy()
            df_c['Data_dt'] = pd.to_datetime(
                df_c['Data'], dayfirst=True, errors='coerce')
            df_c = df_c.sort_values('Data_dt', ascending=True)
            dts = df_c['Data_dt'].dropna().tolist()
            if dts:
                qtd_marcos = 1
                ultima_data = dts[0]
                for d in dts[1:]:
                    if (d - ultima_data).days >= 7:
                        qtd_marcos += 1
                        ultima_data = d
        except:
            pass

    xp_str = (qtd_marcos * 150) + int(volume_total * 0.1) + \
        (len(df_checkins) * 25)

    # 2. INTELIGÊNCIA (INT)
    xp_int = 0
    pags = 0
    horas = 0
    if not df_estudos.empty:
        # Garante que Qtd é número
        df_estudos['Qtd'] = pd.to_numeric(
            df_estudos['Qtd'], errors='coerce').fillna(0)

        for _, row in df_estudos.iterrows():
            t = row['Tipo']
            q = row['Qtd']

            if t == 'Livro':
                # NOVA LÓGICA: 5 XP a cada 3 páginas
                xp_int += int(q * (5/3))
                pags += q
            elif t in ['Mangá', 'HQ']:
                # NOVA LÓGICA: 2 XP a cada 3 páginas
                xp_int += int(q * (2/3))
                pags += q
            elif t in ['Estudos', 'Curso']:
                xp_int += int(q * 50)
                horas += q

    # 3. GLOBAL
    xp_total = xp_str + int(xp_int)
    nivel = 1 + int(xp_total / 1000)

    # Títulos e Ícones (Emojis Seguros)
    if nivel < 5:
        titulo, icone = "Novato", "🌱"       # Broto
    elif nivel < 10:
        titulo, icone = "Aprendiz", "⚔️"    # Espadas
    elif nivel < 20:
        titulo, icone = "Guerreiro", "🛡️"   # Escudo
    elif nivel < 40:
        titulo, icone = "Veterano", "🦁"    # Leão
    elif nivel < 60:
        titulo, icone = "Mestre", "👑"      # Coroa
    else:
        titulo, icone = "Lenda", "🐉"                # Dragão

    return nivel, xp_total, xp_total % 1000, 1000, titulo, icone, ultima_data, xp_str, int(xp_int), pags, horas

# --- LOGIN ---


def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        c1, _ = st.columns([1, 2])
        with c1:
            st.title("🛡️ Login RPG")
            mode = st.radio(
                "Opção", ["Entrar", "Criar Conta"], horizontal=True)
            if mode == "Criar Conta":
                u = st.text_input("Novo Herói")
                p = st.text_input("Nova Senha", type="password")
                if st.button("Criar"):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df = carregar_dados_direto("usuarios")
                    if not df.empty and u in df['Usuario'].values:
                        st.error("Já existe!")
                    else:
                        conn.update(worksheet="usuarios", data=pd.concat(
                            [df, pd.DataFrame([{"Usuario": u, "Senha": str(p)}])]))
                        st.success("Criado! Faça login.")
                        st.cache_data.clear()
            else:
                with st.form("log"):
                    u = st.text_input("Herói")
                    p = st.text_input("Senha", type="password")
                    if st.form_submit_button("Entrar"):
                        df = carregar_dados_direto("usuarios")
                        if not df.empty:
                            df['Senha'] = df['Senha'].astype(str)
                            if not df[(df['Usuario'] == u) & (df['Senha'] == str(p))].empty:
                                st.session_state["autenticado"] = True
                                st.session_state["usuario"] = u
                                st.rerun()
                            else:
                                st.error("Senha incorreta")
                        else:
                            st.error("Erro de conexão")
        return False
    return True


# --- CSS VISUAL ---
st.markdown("""
<style>
:root {
    --neon-blue: #00f2ff; --neon-gold: #ffea00; --neon-green: #39ff14; 
    --neon-orange: #ff5e00; --neon-purple: #b700ff; --neon-pink: #ff00d4; --neon-red: #ff0000;
    --bg-dark: #0e1117; --card-bg: rgba(255,255,255,0.05);
}
.stApp { background-color: var(--bg-dark); }

/* HUD */
.hud-box {
    background: rgba(20,20,30,0.8); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 15px; padding: 20px; margin-bottom: 20px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
}
.avatar { font-size: 60px; text-align: center; }
.stat-bar-label { font-weight: bold; font-size: 0.9em; margin-bottom: 2px; display: block; }
.hp { color: #ff4d4d; } .mp { color: #4d94ff; }

/* NAV */
div[data-testid="stRadio"] > div {
    background: var(--card-bg); padding: 5px; border-radius: 10px;
    display: flex; justify-content: space-around;
}

/* CARDS DE ESTUDO */
.mage-card {
    background: linear-gradient(135deg, rgba(30,0,50,0.9), rgba(10,10,20,0.9));
    border-left: 4px solid #b700ff;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 10px;
    box-shadow: 0 2px 10px rgba(183, 0, 255, 0.15);
    transition: transform 0.2s;
}
.mage-card:hover { transform: translateY(-2px); border-left-color: #00f2ff; }
.mage-title { color: #fff; font-weight: bold; font-size: 1.05em; margin-bottom: 5px; }
.mage-tags { display: flex; gap: 8px; font-size: 0.75em; align-items: center; }
.tag { padding: 2px 8px; border-radius: 4px; font-weight: bold; color: #000; }
.tag-livro { background: #00f2ff; }
.tag-hq { background: #ff00d4; color: white; }
.tag-estudos { background: #ffea00; } 
.mage-date { margin-left: auto; color: #888; font-size: 0.75em; }

/* CALENDÁRIO */
.cal-day { font-weight:bold; text-align:center; padding:5px; border-radius:5px 5px 0 0; color:black; font-size:0.8em; }
.cal-body { background:rgba(255,255,255,0.03); padding:8px; min-height:120px; font-size:0.8em; border-radius:0 0 5px 5px; }
</style>
""", unsafe_allow_html=True)

# --- EXECUÇÃO PRINCIPAL ---
if verificar_senha():
    conn = st.connection("gsheets", type=GSheetsConnection)
    user = st.session_state["usuario"]

    # CARREGAR DADOS
    df_users_tot = carregar_dados_direto("usuarios")
    df_evol_tot = carregar_dados_direto("evolucao")
    df_treinos_tot = carregar_dados_direto("treinos")
    df_check_tot = carregar_dados_direto("checkins")
    df_agenda_tot = carregar_dados_direto("agenda")
    df_estudos_tot = carregar_dados_direto("estudos")

    # FILTRAR USER
    df_f = df_evol_tot[df_evol_tot['Usuario'] == user].copy()
    df_t = df_treinos_tot[df_treinos_tot['Usuario'] == user].copy()

    # Tratamento seguro se vazio
    if not df_check_tot.empty:
        df_c = df_check_tot[df_check_tot['Usuario'] == user].copy()
    else:
        df_c = pd.DataFrame(columns=["Usuario", "Data"])

    if not df_agenda_tot.empty:
        df_a = df_agenda_tot[df_agenda_tot['Usuario'] == user].copy()
    else:
        df_a = pd.DataFrame()

    if not df_estudos_tot.empty:
        df_e = df_estudos_tot[df_estudos_tot['Usuario'] == user].copy()
    else:
        df_e = pd.DataFrame(
            columns=["Usuario", "Data", "Assunto", "Qtd", "Tipo"])

    # CALCULAR VOLUME
    vol = 0
    try:
        for c in ['Series', 'Reps', 'KG']:
            df_t[c] = pd.to_numeric(df_t[c].astype(str).str.replace(
                ',', '.'), errors='coerce').fillna(0)
        vol = (df_t['Series']*df_t['Reps']*df_t['KG']).sum()
    except:
        pass

    # --- CALCULAR RPG (COM PAGS E HORAS) ---
    nivel, total_xp, xp_curr, xp_next, title, icon, last_dt, xp_str, xp_int, pags, horas = calcular_status_rpg(
        df_f, vol, df_c, df_e)

    # --- HUD ---
    st.markdown('<div class="hud-box">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 5, 1])
    with c1:
        st.markdown(
            f"<div class='avatar'>{icon}</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(
            f"### {user} | Lvl {nivel} - <span style='color:#ccc'>{title}</span>", unsafe_allow_html=True)
        h1, h2 = st.columns(2)
        with h1:
            st.markdown(
                f"<span class='stat-bar-label hp'>HP (Físico): {xp_str} XP</span>", unsafe_allow_html=True)
            st.progress(min(1.0, xp_str / (xp_str + xp_int + 1)
                        if (xp_str+xp_int) > 0 else 0))
        with h2:
            st.markdown(
                f"<span class='stat-bar-label mp'>MP (Mental): {xp_int} XP</span>", unsafe_allow_html=True)
            st.progress(min(1.0, xp_int / (xp_str + xp_int + 1)
                        if (xp_str+xp_int) > 0 else 0))
    with c3:
        if st.button("Sair"):
            st.session_state["autenticado"] = False
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # --- TABS ---
    nav = st.radio("", ["📜 Atributos", "⚔️ Grimório", "📚 Biblioteca"],
                   horizontal=True, label_visibility="collapsed")

    # ==========================
    # ABA 1: ATRIBUTOS
    # ==========================
    if nav == "📜 Atributos":
        c1, c2 = st.columns([2, 1])
        c1.subheader("Evolução Física")

        can_xp = True
        days_left = 0
        if last_dt:
            diff = datetime.now() - last_dt
            if diff.days < 7:
                can_xp, days_left = False, 7 - diff.days

        with c2.expander("📝 Atualizar Peso", expanded=True):
            if can_xp:
                st.success("✨ XP Disponível!")
            else:
                st.caption(f"⏳ XP em {days_left} dias")
            with st.form("att_peso"):
                p = st.number_input("Peso (kg)", 30.0, 200.0, 70.0)
                a = st.number_input("Altura (m)", 1.0, 2.5, 1.75)
                if st.form_submit_button("Salvar"):
                    new = pd.DataFrame([{"Usuario": user, "Data": datetime.now().strftime(
                        "%d/%m/%Y"), "Peso": p, "Altura": a, "IMC": round(p/(a**2), 2)}])
                    conn.update(worksheet="evolucao",
                                data=pd.concat([df_evol_tot, new]))
                    st.cache_data.clear()
                    st.toast("Salvo!", icon="✅")
                    time.sleep(1)
                    st.rerun()

        if not df_f.empty:
            df_chart = df_f.copy()
            df_chart['Date'] = pd.to_datetime(
                df_chart['Data'], dayfirst=True, errors='coerce')
            chart = alt.Chart(df_chart).mark_area(
                line={'color': '#00f2ff'},
                color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(
                    color='#00f2ff', offset=0), alt.GradientStop(color='rgba(0,0,0,0)', offset=1)], x1=1, x2=1, y1=1, y2=0)
            ).encode(x='Date:T', y=alt.Y('Peso:Q', scale=alt.Scale(zero=False))).properties(height=300)
            st.altair_chart(chart, use_container_width=True)

    # ==========================
    # ABA 2: GRIMÓRIO (TREINO)
    # ==========================
    elif nav == "⚔️ Grimório":
        c1, c2 = st.columns([3, 1])
        c1.subheader("Rotina de Batalha")
        hoje = datetime.now().strftime("%d/%m/%Y")

        if not df_c.empty and hoje in df_c['Data'].values:
            c2.success("✅ Check-in feito!")
        else:
            if c2.button("🔥 Check-in (+25 XP)"):
                conn.update(worksheet="checkins", data=pd.concat(
                    [df_check_tot, pd.DataFrame([{"Usuario": user, "Data": hoje}])]))
                st.cache_data.clear()
                st.rerun()

        st.divider()

        # Calendário
        days = ['Segunda', 'Terca', 'Quarta',
                'Quinta', 'Sexta', 'Sabado', 'Domingo']
        routine = {d: "DESCANSO" for d in days}
        if not df_a.empty:
            for d in days:
                if d in df_a.columns:
                    routine[d] = df_a[d].iloc[0]

        cols = st.columns(7)
        short_days = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB', 'DOM']

        for i, d in enumerate(days):
            t = routine[d]
            color = get_neon_color(t)
            with cols[i]:
                st.markdown(
                    f"<div class='cal-day' style='background:{color}; box-shadow:0 0 8px {color};'>{short_days[i]}</div>", unsafe_allow_html=True)
                html = f"<strong>{t}</strong><hr style='margin:5px 0; border-color:#ffffff20'>" if t != "DESCANSO" else "<div style='text-align:center; padding-top:20px; color:#555'>Descanso</div>"
                if t != "DESCANSO":
                    exs = df_t[df_t['Treino'] == t]
                    for _, r in exs.iterrows():
                        html += f"<div style='font-size:0.9em; margin-bottom:3px'>• {r['Exercicio']} <span style='color:#aaa'>({int(r['Series'])}x{int(r['Reps'])})</span></div>"
                st.markdown(
                    f"<div class='cal-body'>{html}</div>", unsafe_allow_html=True)

        with st.expander("⚙️ Editar Rotina"):
            with st.form("edit_rotina"):
                cols_f = st.columns(7)
                opts = ["DESCANSO"] + sorted(df_t['Treino'].unique().tolist())
                new_rot = {}
                for i, d in enumerate(days):
                    idx = opts.index(routine[d]) if routine[d] in opts else 0
                    new_rot[d] = cols_f[i].selectbox(d[:3], opts, index=idx)
                if st.form_submit_button("Salvar"):
                    clean = df_agenda_tot[df_agenda_tot['Usuario'] != user]
                    new_rot['Usuario'] = user
                    conn.update(worksheet="agenda", data=pd.concat(
                        [clean, pd.DataFrame([new_rot])]))
                    st.cache_data.clear()
                    st.rerun()

        st.divider()
        with st.expander("🛠️ Editor de Exercícios"):
            with st.form("edit_ex"):
                edited = st.data_editor(
                    df_t.drop(columns=['Usuario']), num_rows="dynamic", use_container_width=True)
                if st.form_submit_button("Salvar Alterações"):
                    edited['Usuario'] = user
                    clean = df_treinos_tot[df_treinos_tot['Usuario'] != user]
                    conn.update(worksheet="treinos",
                                data=pd.concat([clean, edited]))
                    st.cache_data.clear()
                    st.toast("Treinos salvos!", icon="⚔️")
                    time.sleep(1)
                    st.rerun()
            if not df_t.empty:
                st.download_button("📜 PDF", data=gerar_pdf(
                    df_t, user), file_name="treino.pdf")

    # ==========================
    # ABA 3: BIBLIOTECA (MAGE)
    # ==========================
    elif nav == "📚 Biblioteca":
        c1, c2 = st.columns([3, 1])
        c1.subheader("Biblioteca Arcana")
        c2.metric("Inteligência (MP)", f"{xp_int} XP")

        col_L, col_R = st.columns([1, 1])

        with col_L:
            st.markdown("""
            <div style="background:rgba(183, 0, 255, 0.1); padding:15px; border-radius:10px; border:1px solid #b700ff; margin-bottom:15px;">
                <h4 style="margin:0; color:#e0b0ff">✨ Conjurar Sabedoria</h4>
                <small style="color:#aaa">Livro (5XP/3pág) | Mangá (2XP/3pág) | Estudos (50XP/h)</small>
            </div>
            """, unsafe_allow_html=True)

            with st.form("study_form", clear_on_submit=True):
                name = st.text_input(
                    "Nome do Tomo", placeholder="Ex: O Hobbit, Python...")
                # OPÇÕES ATUALIZADAS
                tipo = st.radio(
                    "Tipo", ["Livro", "Mangá/HQ", "Estudos"], horizontal=False)
                qtd = st.number_input(
                    "Qtd (Páginas/Horas)", min_value=1, step=1)

                if st.form_submit_button("Registrar", type="primary"):
                    if name:
                        # Mapeamento do nome visual para o nome salvo no banco
                        real_type = tipo
                        if tipo == "Mangá/HQ":
                            real_type = "Mangá"

                        new_row = pd.DataFrame([{"Usuario": user, "Data": datetime.now().strftime(
                            "%d/%m/%Y"), "Assunto": name, "Qtd": qtd, "Tipo": real_type}])
                        conn.update(worksheet="estudos", data=pd.concat(
                            [df_estudos_tot, new_row]))
                        st.cache_data.clear()

                        gain = 0
                        if real_type == 'Livro':
                            gain = int(qtd*(5/3))
                        elif real_type in ['Mangá', 'HQ']:
                            gain = int(qtd*(2/3))
                        else:
                            gain = qtd*50

                        st.toast(f"+{gain} MP ganho!", icon="🔮")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("Nome obrigatório")

        with col_R:
            st.caption("📜 Pergaminhos Recentes")
            if not df_e.empty:
                recents = df_e.iloc[::-1].head(4)
                for _, row in recents.iterrows():
                    t = row['Tipo']
                    # TAG ATUALIZADA
                    if t in ['Estudos', 'Curso']:
                        tag_cls = "tag-estudos"
                        unit = "h"
                    elif t in ['Mangá', 'HQ']:
                        tag_cls = "tag-hq"
                        unit = "pág"
                    else:
                        tag_cls = "tag-livro"
                        unit = "pág"

                    st.markdown(f"""
                    <div class="mage-card">
                        <div class="mage-title">{row['Assunto']}</div>
                        <div class="mage-tags">
                            <span class="tag {tag_cls}">{t}</span>
                            <span>{int(row['Qtd'])}{unit}</span>
                            <span class="mage-date">{row['Data']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("O Grimório está vazio.")

        st.divider()
        k1, k2 = st.columns(2)
        # MÉTRICAS CORRIGIDAS
        k1.metric("Páginas Lidas", int(pags))
        k2.metric("Horas Estudadas", int(horas))

        with st.expander("🛠️ Gerenciar Histórico"):
            if not df_e.empty:
                edited_e = st.data_editor(
                    df_e.iloc[::-1], num_rows="dynamic", use_container_width=True)
                if st.button("Salvar Correções"):
                    clean = df_estudos_tot[df_estudos_tot['Usuario'] != user]
                    conn.update(worksheet="estudos",
                                data=pd.concat([clean, edited_e]))
                    st.cache_data.clear()
                    st.rerun()
