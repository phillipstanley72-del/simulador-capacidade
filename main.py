import streamlit as st
import pandas as pd
import io

# --- Configuração inicial ---
st.set_page_config(page_title="📊 Simulador de Capacidade de Extrusão", layout="wide")

# URL do GitHub
url_github = "https://raw.githubusercontent.com/phillipstanley72-del/simulador-capacidade/e53411d5533c9127610b781be8ce2087b9fb39ff/base_dados_jan_jul2025.xlsx"

# Carregar base
@st.cache_data
def carregar_dados():
    return pd.read_excel(url_github)

df_base = carregar_dados()
st.success(f"✅ Dados carregados: {df_base.shape[0]} linhas e {df_base.shape[1]} colunas")

# Extrair listas únicas
formularios_unicos = sorted(df_base["Formulation"].dropna().unique())
larguras_por_formula = {
    f: sorted(df_base.loc[df_base["Formulation"] == f, "Width"].dropna().unique())
    for f in formularios_unicos
}

# Work centers de bag extrusion
work_centers = ["4027/EXBA01", "4027/EXBA02", "4027/EXBA03", "4027/EXBA04"]

# --- Valores padrão (cenário inicial) ---
valores_padrao = {
    "4027/EXBA01": {"YB206": {"200": 50, "220": 50}},
    "4027/EXBA02": {"YB206": {"310": 50, "340": 50}},
    "4027/EXBA03": {"YB206": {"430": 50, "400": 50}},
    "4027/EXBA04": {"YB206": {"260": 50, "280": 50}},
}

# --- Interface de configuração ---
st.header("🎛️ Configuração do Cenário")

mix_config = {}
for wc in work_centers:
    st.subheader(f"🔹 {wc}")

    formulas_selecionadas = st.multiselect(
        f"Selecione fórmulas para {wc}",
        options=formularios_unicos,
        default=list(valores_padrao.get(wc, {}).keys())
    )

    mix_config[wc] = {}
    for formula in formulas_selecionadas:
        pct_formula = st.number_input(
            f"% da formulação {formula} em {wc}",
            min_value=0, max_value=100, value=100 if formula in valores_padrao.get(wc, {}) else 0,
            step=1, key=f"{wc}_{formula}_pct"
        )

        larguras = larguras_por_formula.get(formula, [])
        mix_config[wc][formula] = {"%_formula": pct_formula, "larguras": {}}

        for largura in larguras:
            valor_padrao = valores_padrao.get(wc, {}).get(formula, {}).get(str(largura), 0)
            pct_largura = st.number_input(
                f"% da largura {largura} mm ({formula}) em {wc}",
                min_value=0, max_value=100, value=valor_padrao,
                step=1, key=f"{wc}_{formula}_{largura}_pct"
            )
            mix_config[wc][formula]["larguras"][largura] = pct_largura

# --- Resumo das premissas ---
st.header("📋 Resumo das Premissas Configuradas")
resumo_data = []
for wc, formulas in mix_config.items():
    for formula, dados in formulas.items():
        resumo_data.append({
            "Work Center": wc,
            "Formulação": formula,
            "% Formulação": f"{dados['%_formula']:.1f}%",
            "Larguras (%)": ", ".join([f"{lw}mm: {p:.1f}%" for lw, p in dados["larguras"].items() if p > 0])
        })

df_resumo = pd.DataFrame(resumo_data)
st.dataframe(df_resumo, use_container_width=True)

# --- Simulação de resultados ---
st.header("📊 Resultados Detalhados")
df_resultados = df_base.copy()
df_resultados["Produção Estimada (kg)"] = (df_resultados["Qtd"] * 1.05).round(0).astype("Int64")

df_resultados_fmt = df_resultados.copy()
df_resultados_fmt["Mix %"] = (df_resultados_fmt["Qtd"] / df_resultados_fmt["Qtd"].sum() * 100).round(1)

st.dataframe(df_resultados_fmt, use_container_width=True)

# --- Exportar relatório para Excel ---
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    df_resumo.to_excel(writer, sheet_name="Premissas", index=False)
    df_resultados_fmt.to_excel(writer, sheet_name="Resultados", index=False)
st.download_button(
    label="📥 Baixar Relatório em Excel",
    data=buffer.getvalue(),
    file_name="relatorio_simulador.xlsx",
    mime="application/vnd.ms-excel"
)
