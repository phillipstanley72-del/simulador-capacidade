# main.py - Simulador de Capacidade de Extrusão (Streamlit)
import pandas as pd
import streamlit as st

# ===============================================================
# 1. Configuração da página
# ===============================================================
st.set_page_config(page_title="Simulador de Capacidade", layout="wide")
st.title("📊 Simulador de Capacidade de Extrusão")
st.markdown("Carregue a base de dados e ajuste os cenários interativamente")

# ===============================================================
# 2. Upload do Excel
# ===============================================================
uploaded_file = st.file_uploader("📂 Carregue a base de dados (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    # ---- Leitura ----
    xls = pd.ExcelFile(uploaded_file)
    if "Planilha1" in xls.sheet_names:
        df = pd.read_excel(uploaded_file, sheet_name="Planilha1")
    else:
        df = pd.read_excel(uploaded_file, sheet_name=xls.sheet_names[0])

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
# 4. Configuração Interativa do Cenário (apenas Bag Extrusion)
# ===============================================================
st.subheader("🎛️ Configuração do Cenário")

# Filtrar apenas os Work Centers de extrusão
linhas = [l for l in df_grouped["Work Center"].unique() if "EXBA" in l]
cenarios_interativos = {}

for linha in linhas:
    st.markdown(f"## 🔹 Linha {linha}")
    formulas = df_grouped[df_grouped["Work Center"] == linha]["Formulation"].unique()
    cenarios_interativos[linha] = {}

    for formula in formulas:
        st.markdown(f"**Formulação {formula}**")
        share_formula = st.slider(
            f"% da formulação {formula} em {linha}",
            0.0, 1.0, 1.0, 0.05, key=f"{linha}_{formula}_share"
        )
        cenarios_interativos[linha][formula] = {"share_formula": share_formula, "widths": {}}

        widths = df_grouped[
            (df_grouped["Work Center"] == linha) & 
            (df_grouped["Formulation"] == formula)
        ]["Width"].unique()

        for largura in widths:
            perc_width = st.slider(
                f"% da largura {largura} mm ({formula}) em {linha}",
                0.0, 1.0, 0.25, 0.05, key=f"{linha}_{formula}_{largura}"
            )
            cenarios_interativos[linha][formula]["widths"][largura] = perc_width

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
    # 7. Mostrar Resultados
    # ===============================================================
    st.subheader("📊 Resultados Detalhados")
    st.dataframe(df_resultados)

    st.subheader("📈 Consolidados")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Produção Total Estimada (kg)", f"{total_consolidado:,.0f}")
    with col2:
        st.metric("Uptime considerado", f"{uptime*100:.1f}%")

    st.write("### Produção por Linha")
    st.dataframe(total_linha)

    st.write("### Produção por Formulação")
    st.dataframe(total_formula)

    st.write("### Produção por Formulação e Largura")
    st.dataframe(total_formula_width)

    # ===============================================================
    # 8. Gráficos Interativos
    # ===============================================================
    st.subheader("📊 Visualizações")

    st.write("#### Produção por Linha (kg)")
    st.bar_chart(total_linha.set_index("Work Center")["Produção Estimada (kg)"])

    st.write("#### Mix por Formulação (%)")
    st.bar_chart(total_formula.set_index("Formulation")["Mix %"])

    st.write("#### Mix por Formulação e Largura (%)")
    total_formula_width["Form+Width"] = total_formula_width["Formulation"].astype(str) + " - " + total_formula_width["Width"].astype(str)
    st.bar_chart(total_formula_width.set_index("Form+Width")["Mix %"])

else:
    st.info("⬆️ Faça upload de um arquivo Excel para começar a simulação")

