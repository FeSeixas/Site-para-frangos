import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF
import io

# 1. Configuração da página e Estilo Personalizado
st.set_page_config(page_title="Diário de Treino", page_icon="💪", layout="wide")

# CSS para Tema Escuro com detalhes em Roxo Escuro
st.markdown("""
    <style>
    /* Cor de fundo principal e texto */
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    
    /* Customização das Métricas (Cartões) */
    [data-testid="stMetricValue"] {
        color: #BB86FC !important; /* Roxo claro para o valor */
    }
    [data-testid="stMetricLabel"] {
        color: #E0E0E0 !important;
    }
    .stMetric {
        background-color: #1E1E26;
        padding: 15px;
        border-radius: 12px;
        border-left: 5px solid #4B0082; /* Detalhe em Roxo Escuro */
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }

    /* Botões em Roxo Escuro */
    div.stButton > button:first-child {
        background-color: #4B0082;
        color: white;
        border-radius: 8px;
        border: none;
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #6A0DAD;
        border: none;
        transform: scale(1.02);
    }

    /* Ajuste de inputs e tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #1E1E26;
        border-radius: 8px 8px 0px 0px;
        color: white;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4B0082 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Definição de arquivos
arquivo_corpo = 'dados_academia.csv'
arquivo_treinos = 'meus_treinos.csv'

# --- FUNÇÕES DE APOIO ---


def gerar_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="PLANO DE TREINAMENTO", ln=True, align='C')
    pdf.ln(10)

    col_agrupar = 'Treino' if 'Treino' in df.columns else df.columns[0]
    for treino in sorted(df[col_agrupar].unique()):
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(200, 200, 200)  # Fundo cinza para cabeçalho no PDF
        pdf.cell(0, 10, txt=f" {treino}", ln=True, fill=True)

        df_t = df[df[col_agrupar] == treino]
        pdf.set_font("Arial", '', 10)
        for _, row in df_t.iterrows():
            linha = f"{row.get('Exercício', '')} | {row.get('Séries', '')}x{row.get('Repetições', '')} | KG: {row.get('KG', '')} | Desc: {row.get('Descanso', '')}"
            pdf.cell(0, 8, txt=linha, ln=True)
        pdf.ln(4)
    return pdf.output(dest='S').encode('latin-1')


def carregar_dados(caminho, colunas):
    if os.path.exists(caminho):
        try:
            df = pd.read_csv(caminho)
            for col in colunas:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            return pd.DataFrame(columns=colunas)
    return pd.DataFrame(columns=colunas)

# --- INTERFACE ---


aba1, aba2 = st.tabs(["📈 Evolução Corporal", "🏋️ Planejamento de Treinos"])

with aba1:
    st.title("💪 Acompanhamento de Evolução")

    with st.container():
        st.subheader("📝 Novo Registro")
        with st.form("entrada_dados", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            nome = c1.text_input("Nome", placeholder="Ex: Felipe")
            idade = c2.number_input("Idade", 10, 100, 22)
            altura = c3.number_input("Altura (m)", 1.0, 2.5, 1.90, step=0.01)

            c4, c5, c6 = st.columns(3)
            peso = c4.number_input("Peso (kg)", 30.0, 200.0, 66.0, step=0.1)
            freq = c5.slider("Dias por Semana", 1, 7, 3)
            horas = c6.number_input(
                "Duração Média (h)", 0.5, 5.0, 1.3, step=0.1)

            if st.form_submit_button("Salvar Evolução"):
                if nome:
                    imc = round(peso / (altura ** 2), 2)
                    novo = {'Data': datetime.now().strftime("%d/%m/%Y"), 'Nome': nome.strip().title(),
                            'Idade': idade, 'Altura': altura, 'Peso': peso, 'IMC': imc,
                            'Frequência Semanal': freq, 'Duração (h)': horas}
                    pd.DataFrame([novo]).to_csv(
                        arquivo_corpo, mode='a', header=not os.path.exists(arquivo_corpo), index=False)
                    st.toast("Evolução registrada!")
                    st.rerun()

    df_corpo = carregar_dados(arquivo_corpo, ['Data', 'Nome', 'Peso'])
    if not df_corpo.empty:
        st.divider()
        u_nomes = df_corpo['Nome'].unique()
        p_filtro = st.sidebar.selectbox("Filtro de Usuário:", u_nomes)

        df_f = df_corpo[df_corpo['Nome'] == p_filtro].copy()

        # Métricas com visual refinado
        if len(df_f) > 0:
            p_ini = float(df_f['Peso'].iloc[0])
            p_at = float(df_f['Peso'].iloc[-1])
            evol = p_at - p_ini

            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Peso Inicial", f"{p_ini}kg")
            with col_m2:
                st.metric("Peso Atual", f"{p_at}kg")
            with col_m3:
                st.metric("Evolução Total", f"{evol:.1f}kg", delta=evol)

        with st.expander("🛠️ Gerenciar Histórico (Editar/Excluir)"):
            df_ed_c = st.data_editor(
                df_f, use_container_width=True, hide_index=True, num_rows="dynamic")
            if st.button("Confirmar Mudanças no Histórico"):
                df_outros = df_corpo[df_corpo['Nome'] != p_filtro]
                pd.concat([df_outros, df_ed_c]).to_csv(
                    arquivo_corpo, index=False)
                st.success("Histórico atualizado!")
                st.rerun()

        st.line_chart(df_f, x="Data", y="Peso", color="#6A0DAD")

with aba2:
    st.title("🏋️ Planejamento de Treinos")
    cols_t = ['Treino', 'Exercício', 'Séries',
              'Repetições', 'Descanso', 'KG', 'Observações']
    df_t = carregar_dados(arquivo_treinos, cols_t)

    st.subheader("📝 Editor de Planilha")
    df_ed = st.data_editor(df_t, use_container_width=True, hide_index=True, num_rows="dynamic",
                           column_config={
                               "Treino": st.column_config.SelectboxColumn("Treino", options=["TREINO A", "TREINO B", "TREINO C", "TREINO D", "CARDIO"], required=True),
                               "Séries": st.column_config.SelectboxColumn("Séries", options=list(range(1, 11)))
                           })

    c_save, c_pdf, c_del = st.columns([1, 1, 2])
    if c_save.button("💾 Salvar Treinos"):
        df_ed.to_csv(arquivo_treinos, index=False)
        st.toast("Planilha salva!")

    if not df_ed.empty:
        c_pdf.download_button("📄 Baixar PDF", data=gerar_pdf(
            df_ed), file_name="treino.pdf")

        st.divider()
        st.subheader("📋 Visualização por Grupos")
        for t in sorted(df_ed['Treino'].unique()):
            with st.expander(f"📖 {t}", expanded=True):
                st.table(df_ed[df_ed['Treino'] == t].drop(columns=['Treino']))

    if c_del.button("⚠️ Apagar Planilha Completa"):
        if os.path.exists(arquivo_treinos):
            os.remove(arquivo_treinos)
        st.rerun()