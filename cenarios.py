# ===============================================================
#  cenarios.py - Definição dos cenários de simulação
# ===============================================================
# Agora você pode definir:
# - Apenas formulações (com porcentagem por linha)
# - Formulações + larguras (com distribuição manual de % por largura)
# ===============================================================

# Cenário 1: Apenas formulações (formato simples)
cenario_base = {
    "4027/EXBA01": {"YB206": 1.0},   # 100% YB206
    "4027/EXBA02": {"YB206": 1.0, "YL206N": 0.0},  # 50/50
    "4027/EXBA03": {"YB206": 1.0},
    "4027/EXBA04": {"YB206": 1.0},
}

# Cenário 2: Formulações + larguras (formato detalhado)
cenario_com_larguras = {
    "4027/EXBA01": {
        "YB206": {
            "share_formula": 1.0,
            "widths": {
                200: 0.4,   # 
                220: 0.6,    # 
                240: 0.0,
                260: 0.0,
            }
        }
    },
    "4027/EXBA02": {
        "YB206": {
            "share_formula": 1.0,
            "widths": {
                280: 0.4,
                310: 0.4,
                340: 0.2,
                370: 0.0,
            }
        },
        "YL206N": {
            "share_formula": 0.0,
            "widths": {
                300: 0.0  # 100% dessa formulação só em 300 mm
            }
        }
    },
    "4027/EXBA03": {
        "YB206": {
            "share_formula": 1.0,
            "widths": {
                340: 0.0,
                370: 0.0,
                400: 0.2,   # 
                430: 0.8,   # 
                460: 0.0,
                490: 0.0,
                530: 0.0,
            }
        }
    },
    "4027/EXBA04": {
        "YB206": {
            "share_formula": 1.0,
            "widths": {
                220: 0.0,
                240: 0.4,   # 
                260: 0.6,   # 
                280: 0.0,
                310: 0.0,   
            }
        }
    }
}
