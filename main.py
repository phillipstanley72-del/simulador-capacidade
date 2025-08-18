# main.py - Simulador de Capacidade de Extrusão (Streamlit)
import pandas as pd
import streamlit as st
import altair as alt

# ===============================================================
# 1. Configuração da página
# ===============================================================
st.set_page_config(page_title="Simulador de Capacidade", layout="wide")
st.title("📊 Simulador de Capacidade de Extrusão")
st.markdown("Carregue a base de dados diretamente do GitHub e ajuste as premissas interativamente")

# ===============================================================
# 2. Carregar Excel direto do GitHub
# ===============================================================
url_excel = "https://raw.githubusercontent.com/phillipstanley72-del/simulador-capacidade/e53411d5533c9127610b781be8ce2087b9fb39ff/base_dados_jan_jul2025.xlsx"

xls = pd.ExcelFile(url_excel)
if "Planilha1" in xls.sheet_names:
    df = pd.read_excel(url_excel, sheet_name="Planilha1")
else:
    df = pd.read_excel(url_excel, sheet_name=xls.sheet_names[0])

st.success(f"✅ Dados carregados: {df.shape[0]} linhas e {df.shape[1]} colunas")
with st.expander("🔎 Visualizar primeiras linhas da base"):
    st.dataframe(df.head())

# ===============================================================
# 3. Calcular Run Rates médios
# ===============================================================
df_grouped = (
    df.groupby(["Work Center", "Formulation", "Width"], dropna=False)
      .agg({"Matl Produced, Wgt": "sum", "Run Time": "sum"})
      .reset_index()
)
df_grouped["Run Rate (kg/h)"] = df_grouped["Matl Produced, Wgt"] / df_grouped["Run Time"]

# ===============================================================
# 4. Configuração Interativa do Cenário (somente Bag Extrusion)
# ===============================================================
st.subheader("🎛️ Configuração do Cenário")

linhas = [l for l in df_grouped["Work Center"].unique() if "EXBA" in l]
cenarios_interativos = {}

for linha in linhas:
    st.markdown(f"## 🔹 {linha}")
    formulas_disponiveis = df_grouped[df_grouped["Work Center"] == linha]["Formulation"].unique()

    formulas_escolhidas = st.multiselect(
        f"Selecione fórmulas para {linha}",
        formulas_disponiveis,
        default=list(formulas_disponiveis[:1]),
        key=f"{linha}_formulas"
    )

    cenarios_interativos[linha] = {}
    total_share_formula = 0

    for formula in formulas_escolhidas:
        share_formula_pct = st.number_input(
            f"% da formulação {formula} em {linha}",
            min_value=0, max_value=100, step=5,
            value=int(100/len(formulas_escolhidas)),
            key=f"{linha}_{formula}_share"
        )
        share_formula = share_formula_pct / 100
        total_share_formula += share_formula
        cenarios_interativos[linha][formula] = {"share_formula": share_formula, "widths": {}}

        widths_disponiveis = df_grouped[
            (df_grouped["Work Center"] == linha) &
            (df_grouped["Formulation"] == formula)
        ]["Width"].unique()

        total_share_widths = 0
        for largura in widths_disponiveis:
            share_width_pct = st.number_input(
                f"% da largura {largura} mm ({formula}) em {linha}",
                min_value=0, max_value=100, step=5,
                value=int(100/len(widths_disponiveis)),
                key=f"{linha}_{formula}_{largura}"
            )
            share_width = share_width_pct / 100
            cenarios_interativos[linha][formula]["widths"][largura] = share_width
            total_share_widths += share_width

        if abs(total_share_widths - 1) > 0.001:
            st.warning(f"⚠️ A soma das larguras da fórmula {formula} em {linha} é {total_share_widths*100:.1f}% (deve ser 100%)")

    if abs(total_share_formula - 1) > 0.001:
        st.error(f"❌ A soma das fórmulas em {linha} é {total_share_formula*100:.1f}% (deve ser 100%)")

# ===============================================================
# 5. Aplicar Cenário
# ===============================================================
uptime = 0.95
horas_mes = 24 * 30 * uptime
cenarios = cenarios_interativos

producoes = []
for linha, formulas in cenarios.items():
    for formula, config in formulas.items():
        frac_formula = config.get("share_formula", 1.0)
        widths_override = config.get("widths", None)

        subset = df_grouped[(df_grouped["Work Center"] == linha) & (df_grouped["Formulation"] == formula)]

        for _, row in subset.iterrows():
            largura = row["Width"]
            run_rate = row["Run Rate (kg/h)"]

            if widths_override and largura in widths_override:
                perc = widths_override[largura]
            else:
                perc = 0

            producao = run_rate * horas_mes * perc * frac_formula
            producoes.append([linha, formula, largura, producao])

df_resultados = pd.DataFrame(producoes, columns=["Work Center", "Formulation", "Width", "Produção Estimada (kg)"])

# ===============================================================
# 6. Totais
# ===============================================================
total_consolidado = df_resultados["Produção Estimada (kg)"].sum()
total_linha = df_resultados.groupby("Work Center")["Produção Estimada (kg)"].sum().reset_index()
total_formula = df_resultados.groupby("Formulation")["Produção Estimada (kg)"].sum().reset_index()
total_formula_width = df_resultados.groupby(["Formulation", "Width"])["Produção Estimada (kg)"].sum().reset_index()

total_linha["Mix %"] = total_linha["Produção Estimada (kg)"] / total_consolidado
total_formula["Mix %"] = total_formula["Produção Estimada (kg)"] / total_consolidado
total_formula_width["Mix %"] = total_formula_width["Produção Estimada (kg)"] / total_consolidado

# ===============================================================
# 7. Mostrar Resultados (formatados)
# ===============================================================
st.subheader("📊 Resultados Detalhados")
df_resultados_fmt = df_resultados.copy()
df_resultados_fmt["Produção Estimada (kg)"] = df_resultados_fmt["Produção Estimada (kg)"].round(0).astype(int)
st.dataframe(df_resultados_fmt)

st.subheader("📈 Consolidados")
col1, col2 = st.columns(2)
with col1:
    st.metric("Produção Total Estimada (kg)", f"{total_consolidado:,.0f}")
with col2:
    st.metric("Uptime considerado", f"{uptime*100:.1f}%")

st.write("### Produção por Linha")
df_total_linha_fmt = total_linha.copy()
df_total_linha_fmt["Produção Estimada (kg)"] = df_total_linha_fmt["Produção Estimada (kg)"].round(0).astype(int)
df_total_linha_fmt["Mix %"] = (df_total_linha_fmt["Mix %"] * 100).round(1).astype(str) + "%"
st.dataframe(df_total_linha_fmt)

st.write("### Produção por Formulação")
df_total_formula_fmt = total_formula.copy()
df_total_formula_fmt["Produção Estimada (kg)"] = df_total_formula_fmt["Produção Estimada (kg)"].round(0).astype(int)
df_total_formula_fmt["Mix %"] = (df_total_formula_fmt["Mix %"] * 100).round(1).astype(str) + "%"
st.dataframe(df_total_formula_fmt)

st.write("### Produção por Formulação e Largura")
df_total_formula_width_fmt = total_formula_width.copy()
df_total_formula_width_fmt["Produção Estimada (kg)"] = df_total_formula_width_fmt["Produção Estimada (kg)"].round(0).astype(int)
df_total_formula_width_fmt["Mix %"] = (df_total_formula_width_fmt["Mix %"] * 100).round(1).astype(str) + "%"
st.dataframe(df_total_formula_width_fmt)

# ===============================================================
# 8. Gráficos Interativos (Altair)
# ===============================================================
st.subheader("📊 Visualizações")

# --- Produção por Linha ---
st.write("#### Produção por Linha (kg)")
chart_linha = alt.Chart(total_linha).mark_bar().encode(
    x=alt.X("Work Center:N", title="Linha"),
    y=alt.Y("Produção Estimada (kg):Q", title="Produção (kg)"),
    tooltip=["Work Center", alt.Tooltip("Produção Estimada (kg):Q", format=",")]
)
st.altair_chart(chart_linha, use_container_width=True)

# --- Mix por Formulação ---
st.write("#### Mix por Formulação (%)")
chart_formula = alt.Chart(total_formula).mark_bar().encode(
    x=alt.X("Formulation:N", title="Formulação"),
    y=alt.Y("Mix %:Q", title="Mix (%)", axis=alt.Axis(format=".1%")),
    tooltip=["Formulation", alt.Tooltip("Mix %:Q", format=".1%")]
)
st.altair_chart(chart_formula, use_container_width=True)

# --- Mix por Formulação e Largura ---
st.write("#### Mix por Formulação e Largura (%)")
total_formula_width["Form+Width"] = (
    total_formula_width["Formulation"].astype(str) + " - " + total_formula_width["Width"].astype(str)
)
chart_formula_width = alt.Chart(total_formula_width).mark_bar().encode(
    x=alt.X("Form+Width:N", title="Formulação + Largura"),
    y=alt.Y("Mix %:Q", title="Mix (%)", axis=alt.Axis(format=".1%")),
    tooltip=["Formulation", "Width", alt.Tooltip("Mix %:Q", format=".1%")]
).properties(width=600)
st.altair_chart(chart_formula_width, use_container_width=True)
