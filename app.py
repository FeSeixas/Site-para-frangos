import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
# Import moved to top for better organization
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da página e Estilo
st.set_page_config(page_title="Diário de Treino", page_icon="💪", layout="wide")

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
        st.title("🔐 Acesso Restrito")
        aba_login, aba_cad = st.tabs(["Entrar", "Criar Conta"])

        with aba_cad:
            st.info(
                "O cadastro requer conexão com a nuvem. Use o login se já tiver conta.")
            novo_u = st.text_input("Escolha um Usuário", key="reg_u")
            novo_p = st.text_input("Escolha uma Senha",
                                   type="password", key="reg_p")

            if st.button("Cadastrar Nova Conta"):
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_users = carregar_dados_direto("usuarios")

                if novo_u in df_users['Usuario'].values:
                    st.error("Este usuário já existe!")
                else:
                    # Forçamos a senha a ser salva como string
                    novo_reg = pd.DataFrame(
                        [{"Usuario": novo_u, "Senha": str(novo_p)}])
                    updated_users = pd.concat([df_users, novo_reg])
                    conn.update(worksheet="usuarios", data=updated_users)
                    st.cache_data.clear()  # Limpa o cache
                    st.success("Conta criada! Vá para a aba Entrar.")

        with aba_login:
            user = st.text_input("Usuário", key="log_u")
            senha = st.text_input("Senha", type="password", key="log_p")
            if st.button("Entrar"):
                try:
                    df_users = carregar_dados_direto("usuarios")
                    # AJUSTE: Convertemos as senhas da planilha para texto antes de comparar
                    df_users['Senha'] = df_users['Senha'].astype(str)

                    validado = df_users[(df_users['Usuario'] == user) & (
                        df_users['Senha'] == str(senha))]
                    if not validado.empty:
                        st.session_state["autenticado"] = True
                        st.session_state["usuario"] = user
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos!")
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")
        return False
    return True


# CSS para Tema Escuro com detalhes em Roxo
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #ffffff !important; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; }
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border-left: 5px solid #6A0DAD; }
    div.stButton > button:first-child { background-color: #4B0082; color: white; border: none; }
    div.stButton > button:first-child:hover { background-color: #6A0DAD; border: none; }
    </style>
    """, unsafe_allow_html=True)

if verificar_senha():
    conn = st.connection("gsheets", type=GSheetsConnection)
    user_atual = st.session_state["usuario"]
    st.sidebar.title(f"Olá, {user_atual}!")

    col_logout = st.sidebar
    if col_logout.button("Sair"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- FUNÇÃO GERAR PDF CORRIGIDA ---
    def gerar_pdf(df):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        # Removido txt= e encode
        pdf.cell(
            200, 10, f"PLANO DE TREINO - {user_atual}", ln=True, align='C')
        pdf.ln(10)

        for treino in sorted(df['Treino'].unique()):
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(0, 10, f" {treino}", ln=True, fill=True)

            df_t = df[df['Treino'] == treino]
            pdf.set_font("Arial", '', 10)

            for _, row in df_t.iterrows():
                linha = f"{row['Exercicio']} | {row['Series']}x{row['Reps']} | KG: {row['KG']}"
                pdf.cell(0, 8, linha, ln=True)
            pdf.ln(4)

        # RETORNO EM BYTES CORRIGIDO
        return bytes(pdf.output(dest='S'))

    aba1, aba2 = st.tabs(["📈 Minha Evolução", "🏋️ Meus Treinos"])

    with aba1:
        st.title("💪 Evolução Corporal")
        df_corpo_total = carregar_dados_direto("evolucao")
        df_f = df_corpo_total[df_corpo_total['Usuario'] == user_atual].copy()

        with st.form("entrada_dados", clear_on_submit=True):
            col1, col2 = st.columns(2)
            peso = col1.number_input("Peso (kg)", 30.0, 200.0, 70.0)
            altura = col2.number_input("Altura (m)", 1.0, 2.5, 1.75)
            if st.form_submit_button("Registrar Peso"):
                novo = pd.DataFrame([{
                    "Usuario": user_atual,
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Peso": peso,
                    "Altura": altura,
                    "IMC": round(peso/(altura**2), 2)
                }])
                updated_corpo = pd.concat([df_corpo_total, novo])
                conn.update(worksheet="evolucao", data=updated_corpo)
                st.cache_data.clear()  # Limpa cache
                st.success("Registrado!")
                st.rerun()

        if not df_f.empty:
            p_ini, p_at = float(df_f['Peso'].iloc[0]), float(
                df_f['Peso'].iloc[-1])
            evol = p_at - p_ini
            m1, m2, m3 = st.columns(3)
            m1.metric("Peso Inicial", f"{p_ini}kg")
            m2.metric("Peso Atual", f"{p_at}kg")
            m3.metric("Evolução", f"{evol:.1f}kg", delta=evol)
            st.line_chart(df_f, x="Data", y="Peso")

    with aba2:
        st.title("🏋️ Meus Treinos")
        df_treinos_total = carregar_dados_direto("treinos")
        df_t_user = df_treinos_total[df_treinos_total['Usuario'] == user_atual].copy(
        )

        # --- EDITOR DE TREINO ---
        df_ed = st.data_editor(
            df_t_user.drop(columns=["Usuario"]),
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Treino": st.column_config.SelectboxColumn(
                    "Treino",
                    options=["TREINO A", "TREINO B", "TREINO C", "CARDIO"],
                    required=True
                ),
                "Series": st.column_config.NumberColumn(
                    "Séries",
                    min_value=1, max_value=20, step=1, format="%d"
                ),
                "Reps": st.column_config.NumberColumn(
                    "Repetições",
                    min_value=1, max_value=100, step=1, format="%d"
                ),
                "KG": st.column_config.NumberColumn(
                    "Carga (kg)",
                    min_value=0, step=0.5, format="%.1f kg"
                ),
            },
            key="editor_treino"
        )

        if st.button("💾 Salvar Planilha de Treino"):
            df_ed["Usuario"] = user_atual
            df_outros = df_treinos_total[df_treinos_total['Usuario']
                                         != user_atual]
            updated_treinos = pd.concat([df_outros, df_ed])
            conn.update(worksheet="treinos", data=updated_treinos)
            st.cache_data.clear()
            st.toast("Treino salvo na nuvem!")

        if not df_t_user.empty:
            st.download_button("📄 Exportar PDF", data=gerar_pdf(
                df_t_user), file_name="treino.pdf")
