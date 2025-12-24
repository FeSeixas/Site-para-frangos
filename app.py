import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# 1. Configuração da página e Estilo
st.set_page_config(page_title="Diário de Treino", page_icon="💪", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAÇÃO DE SEGURANÇA ---


def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.title("🔐 Acesso Restrito")
        aba_login, aba_cad = st.tabs(["Entrar", "Criar Conta"])

        with aba_cad:
            novo_u = st.text_input("Escolha um Usuário", key="reg_u")
            novo_p = st.text_input("Escolha uma Senha",
                                   type="password", key="reg_p")
            if st.button("Cadastrar Nova Conta"):
                try:
                    df_users = conn.read(worksheet="usuarios")
                    if novo_u in df_users['Usuario'].values:
                        st.error("Este usuário já existe!")
                    else:
                        novo_reg = pd.DataFrame(
                            [{"Usuario": novo_u, "Senha": novo_p}])
                        updated_users = pd.concat([df_users, novo_reg])
                        conn.update(worksheet="usuarios", data=updated_users)
                        st.success(
                            "Conta criada com sucesso! Vá para a aba Entrar.")
                except Exception as e:
                    st.error(f"Erro ao acessar a planilha: {str(e)}")

        with aba_login:
            user = st.text_input("Usuário", key="log_u")
            senha = st.text_input("Senha", type="password", key="log_p")
            if st.button("Entrar"):
                try:
                    df_users = conn.read(worksheet="usuarios")
                    validado = df_users[(df_users['Usuario'] == user) & (
                        df_users['Senha'] == str(senha))]
                    if not validado.empty:
                        st.session_state["autenticado"] = True
                        st.session_state["usuario"] = user
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos!")
                except Exception as e:
                    st.error(f"Erro ao acessar a planilha: {str(e)}")
        return False
    return True


# CSS para Tema Escuro com detalhes em Roxo
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #ffffff !important; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; }
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #6A0DAD;
    }
    div.stButton > button:first-child {
        background-color: #4B0082;
        color: white;
        border: none;
    }
    div.stButton > button:first-child:hover {
        background-color: #6A0DAD;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

if verificar_senha():
    user_atual = st.session_state["usuario"]
    st.sidebar.title(f"Olá, {user_atual}!")
    if st.sidebar.button("Sair"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- FUNÇÕES ---
    def gerar_pdf(df):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(
            200, 10, txt=f"PLANO DE TREINO - {user_atual}", ln=True, align='C')
        pdf.ln(10)
        for treino in sorted(df['Treino'].unique()):
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(0, 10, txt=f" {treino}", ln=True, fill=True)
            df_t = df[df['Treino'] == treino]
            pdf.set_font("Arial", '', 10)
            for _, row in df_t.iterrows():
                linha = f"{row['Exercicio']} | {row['Series']}x{row['Reps']} | KG: {row['KG']}"
                pdf.cell(0, 8, txt=linha, ln=True)
            pdf.ln(4)
        return pdf.output(dest='S').encode('latin-1')

    aba1, aba2 = st.tabs(["📈 Minha Evolução", "🏋️ Meus Treinos"])

    with aba1:
        st.title("💪 Evolução Corporal")
        df_corpo_total = conn.read(worksheet="evolucao")
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
        df_treinos_total = conn.read(worksheet="treinos")
        df_t_user = df_treinos_total[df_treinos_total['Usuario'] == user_atual].copy(
        )

        df_ed = st.data_editor(df_t_user.drop(columns=["Usuario"]), use_container_width=True, num_rows="dynamic",
                               column_config={
            "Treino": st.column_config.SelectboxColumn(options=["TREINO A", "TREINO B", "TREINO C", "CARDIO"]),
        }, key="editor_treino")

        if st.button("💾 Salvar Planilha de Treino"):
            df_ed["Usuario"] = user_atual
            df_outros = df_treinos_total[df_treinos_total['Usuario']
                                         != user_atual]
            updated_treinos = pd.concat([df_outros, df_ed])
            conn.update(worksheet="treinos", data=updated_treinos)
            st.toast("Treino salvo na nuvem!")

        if not df_t_user.empty:
            st.download_button("📄 Exportar PDF", data=gerar_pdf(
                df_t_user), file_name="treino.pdf")
