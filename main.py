# ===============================================================
#  main.py - Simulador de Capacidade de Extrusão
# ===============================================================
# Esse script lê uma base de dados (Excel), aplica cenários de mix
# de formulações (e opcionalmente larguras) por linha de extrusão
# e gera um relatório consolidado.
# ===============================================================

# ---- 1. Imports ----
import pandas as pd
import xlsxwriter
import os
from cenarios import cenario_com_larguras as CENARIO  # <- escolha aqui o cenário (ex: cenario_base, cenario_com_larguras)

# ---- 2. Carregar base de dados ----
file_path = r"data\base_dados_jan_jul2025.xlsx"

print("🚀 Script iniciado")
print("📂 Pasta atual:", os.getcwd())
print("🔎 Procurando arquivo:", file_path)

if not os.path.exists(file_path):
    print("❌ ERRO: Arquivo não encontrado. Verifique se está em /data e com o nome correto.")
    exit(1)

xls = pd.ExcelFile(file_path)
print("✅ Arquivo encontrado!")
print("📑 Abas encontradas:", xls.sheet_names)

if "Planilha1" in xls.sheet_names:
    df = pd.read_excel(file_path, sheet_name="Planilha1")
else:
    df = pd.read_excel(file_path, sheet_name=xls.sheet_names[0])

print(f"✅ Dados carregados: {df.shape}")
print(df.head())

# ---- 3. Calcular Run Rates médios ----
df_grouped = (
    df.groupby(["Work Center", "Formulation", "Width"], dropna=False)
      .agg({"Matl Produced, Wgt": "sum", "Run Time": "sum"})
      .reset_index()
)
df_grouped["Run Rate (kg/h)"] = df_grouped["Matl Produced, Wgt"] / df_grouped["Run Time"]

# ---- 4. Calcular mix de larguras ----
mix_raw = (
    df.groupby(["Work Center", "Formulation", "Width"], dropna=False)["Matl Produced, Wgt"]
      .sum()
      .reset_index()
)
mix_raw["Mix %"] = (
    mix_raw.groupby(["Work Center", "Formulation"])["Matl Produced, Wgt"]
           .transform(lambda x: x / x.sum())
)
mix = mix_raw.copy()

# ---- 5. Definições do cenário ----
uptime = 0.95
horas_mes = 24 * 30 * uptime
cenarios = CENARIO

producoes = []
for linha, formulas in cenarios.items():
    for formula, config in formulas.items():

        # Caso 1: apenas fração da formula
        if isinstance(config, (int, float)):
            frac_formula = config
            widths_override = None
        # Caso 2: dict com share_formula + larguras
        else:
            frac_formula = config.get("share_formula", 1.0)
            widths_override = config.get("widths", None)

        subset = df_grouped[(df_grouped["Work Center"] == linha) & (df_grouped["Formulation"] == formula)]
        mix_subset = mix[(mix["Work Center"] == linha) & (mix["Formulation"] == formula)]
        
        for _, row in subset.iterrows():
            largura = row["Width"]
            run_rate = row["Run Rate (kg/h)"]

            if widths_override and largura in widths_override:
                perc = widths_override[largura]
            else:
                if not mix_subset[mix_subset["Width"] == largura].empty:
                    perc = mix_subset.loc[mix_subset["Width"] == largura, "Mix %"].iloc[0]
                else:
                    perc = 0

            producao = run_rate * horas_mes * perc * frac_formula
            producoes.append([linha, formula, largura, producao])

df_resultados = pd.DataFrame(producoes, columns=["Work Center", "Formulation", "Width", "Produção Estimada (kg)"])

# ---- 6. Totais ----
total_consolidado = df_resultados["Produção Estimada (kg)"].sum()
total_linha = df_resultados.groupby("Work Center")["Produção Estimada (kg)"].sum().reset_index()
total_formula = df_resultados.groupby("Formulation")["Produção Estimada (kg)"].sum().reset_index()
total_formula_width = df_resultados.groupby(["Formulation", "Width"])["Produção Estimada (kg)"].sum().reset_index()

total_linha["Mix %"] = total_linha["Produção Estimada (kg)"] / total_consolidado
total_formula["Mix %"] = total_formula["Produção Estimada (kg)"] / total_consolidado
total_formula_width["Mix %"] = total_formula_width["Produção Estimada (kg)"] / total_consolidado
total_formula_width = total_formula_width[["Formulation", "Width", "Mix %", "Produção Estimada (kg)"]]

linha_total = pd.DataFrame({
    "Work Center": ["TOTAL 4 Linhas"],
    "Produção Estimada (kg)": [total_consolidado],
    "Mix %": [1.0]
})
total_linha = pd.concat([total_linha, linha_total], ignore_index=True)

print(f"\n📊 Produção total consolidada: {total_consolidado:,.1f} kg")

# ---- 7. Criar aba Premissas ----
premissas_data = [
    ["Premissas", ""],
    ["Uptime", f"{uptime*100:.1f}%"],
    ["Tempo de produção (30 dias)", f"{horas_mes:.1f} horas/linha"],
    ["Produção Total Estimada", f"{total_consolidado:,.0f} kg"],
    ["", ""],
    ["Cenário definido", ""],
]
for linha, formulas in cenarios.items():
    premissas_data.append([linha, str(formulas)])

df_premissas = pd.DataFrame(premissas_data, columns=["Item", "Valor"])

# ---- 8. Exportar resultados para Excel ----
output_path = "output/Relatorio_Extrusion_Capacidade.xlsx"

with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
    df_premissas.to_excel(writer, sheet_name="Premissas", index=False)
    df_grouped.to_excel(writer, sheet_name="RunRates", index=False)
    mix.to_excel(writer, sheet_name="Mix", index=False)
    df.to_excel(writer, sheet_name="Base", index=False)
    
    df_resultados.to_excel(writer, sheet_name="Resultados_Detalhados", index=False)
    total_linha.to_excel(writer, sheet_name="Resultados_Totais", index=False, startrow=0)
    total_formula.to_excel(writer, sheet_name="Resultados_Totais", index=False, startrow=len(total_linha)+3)
    total_formula_width.to_excel(writer, sheet_name="Resultados_Totais", index=False, startrow=len(total_linha)+len(total_formula)+6)

    workbook = writer.book
    ws = writer.sheets["Resultados_Totais"]
    header_fmt = workbook.add_format({"bold": True, "bg_color": "#D9E1F2"})
    num_fmt = workbook.add_format({"num_format": "#,##0"})
    perc_fmt = workbook.add_format({"num_format": "0.0%"})

    ws.set_column("A:A", 25)
    ws.set_column("B:B", 20, num_fmt)
    ws.set_column("C:C", 15, perc_fmt)
    if "D" in total_formula_width.columns:
        ws.set_column("D:D", 20, num_fmt)

    for col_num, value in enumerate(total_linha.columns.values):
        ws.write(0, col_num, value, header_fmt)

    # Gráfico Pizza
    chart_pie = workbook.add_chart({"type": "pie"})
    chart_pie.add_series({
        "name": "Mix por Formulação",
        "categories": ["Resultados_Totais", len(total_linha)+4, 0, len(total_linha)+len(total_formula)+3, 0],
        "values": ["Resultados_Totais", len(total_linha)+4, 1, len(total_linha)+len(total_formula)+3, 1],
        "data_labels": {"percentage": True}
    })
    chart_pie.set_title({"name": "Mix por Formulação (%)"})
    ws.insert_chart("F15", chart_pie)

    # Gráfico Barras
    chart_bar = workbook.add_chart({"type": "column"})
    chart_bar.add_series({
        "name": "Produção por Linha (kg)",
        "categories": ["Resultados_Totais", 1, 0, len(total_linha)-1, 0],
        "values": ["Resultados_Totais", 1, 1, len(total_linha)-1, 1],
        "data_labels": {"value": True}
    })
    chart_bar.add_series({
        "name": "Participação (%)",
        "categories": ["Resultados_Totais", 1, 0, len(total_linha)-1, 0],
        "values": ["Resultados_Totais", 1, 2, len(total_linha)-1, 2],
        "y2_axis": True,
        "data_labels": {"percentage": True}
    })
    chart_bar.set_title({"name": "Produção Estimada por Linha"})
    chart_bar.set_y_axis({"name": "Produção (kg)"})
    chart_bar.set_y2_axis({"name": "Share (%)"})
    ws.insert_chart("F2", chart_bar)

print(f"✅ Relatório gerado em: {os.path.abspath(output_path)}")
