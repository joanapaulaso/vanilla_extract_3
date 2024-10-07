import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
from io import BytesIO

CUSTO_POR_MUDA = 0.85  # US$
PRECO_EXTRATO_POR_TONELADA = 135435.20  # US$


def calcular_produtividade_baunilha(num_mudas, ano):
    producao_por_hectare = {
        3: 500,
        4: 1000,
        5: 1600,
        6: 2500,
    }

    hectares = num_mudas / 4000

    if ano < 3:
        producao = 0
    elif ano <= 6:
        producao = producao_por_hectare[ano] * hectares
    else:
        producao = 2500 * hectares  # Produção estabiliza no nível do ano 6

    producao_kg = producao

    # Cálculo do número de favas
    favas_por_pe_max = 30
    fator_producao = min(1, producao_kg / (2500 * hectares))
    favas_por_pe = favas_por_pe_max * fator_producao
    numero_favas = favas_por_pe * num_mudas

    # Cálculo do peso das favas
    peso_favas_verdes = numero_favas * 20 / 1000  # em kg
    peso_favas_curadas = numero_favas * 4 / 1000  # em kg

    # Cálculo do volume de extrato
    volume_extrato = peso_favas_curadas / 0.25  # kg de extrato (25% de favas)

    return {
        "producao_kg": producao_kg,
        "numero_favas": numero_favas,
        "peso_favas_verdes": peso_favas_verdes,
        "peso_favas_curadas": peso_favas_curadas,
        "volume_extrato": volume_extrato,
    }


def calcular_cumulativo(num_mudas, anos, usar_modelo_linear=False):
    resultados_cumulativos = {
        "Produção Total (kg)": 0,
        "Número de Favas": 0,
        "Peso Favas Verdes (kg)": 0,
        "Peso Favas Curadas (kg)": 0,
        "Valor Favas Verdes (US$)": 0,
        "Valor Favas Curadas (US$)": 0,
        "Valor Extrato (US$)": 0,
        "Volume Extrato (kg)": 0,
        "Faturamento Bruto (US$)": 0,
        "Custo Inicial Mudas (US$)": num_mudas * CUSTO_POR_MUDA,
    }
    resultados_anuais = []

    for ano in range(1, anos + 1):
        res = calcular_produtividade_baunilha(num_mudas, ano, usar_modelo_linear)
        faturamento_bruto = res["valor_extrato"]
        lucro_bruto = faturamento_bruto * 0.2130  # 21.30% do faturamento bruto
        custo_inicial_mudas = num_mudas * CUSTO_POR_MUDA if ano == 1 else 0
        lucro_liquido = lucro_bruto - custo_inicial_mudas

        resultados_anuais.append(
            {
                "Ano": ano,
                "Produção Total (kg)": res["producao_kg"],
                "Número de Favas": res["numero_favas"],
                "Peso Favas Verdes (kg)": res["peso_favas_verdes"],
                "Peso Favas Curadas (kg)": res["peso_favas_curadas"],
                "Valor Favas Verdes (US$)": res["valor_favas_verdes"],
                "Valor Favas Curadas (US$)": res["valor_favas_curadas"],
                "Valor Extrato (US$)": res["valor_extrato"],
                "Volume Extrato (kg)": res["volume_extrato"],
                "Faturamento Bruto (US$)": faturamento_bruto,
                "Faturamento Líquido (US$)": lucro_liquido,
            }
        )

        for key in resultados_cumulativos:
            if key != "Custo Inicial Mudas (US$)":
                resultados_cumulativos[key] += resultados_anuais[-1][key]

    # Calcular o faturamento líquido cumulativo
    faturamento_bruto_total = resultados_cumulativos["Faturamento Bruto (US$)"]
    custo_inicial_mudas = resultados_cumulativos["Custo Inicial Mudas (US$)"]
    lucro_bruto = faturamento_bruto_total * 0.2130  # 21.30% do faturamento bruto
    lucro_liquido = lucro_bruto - custo_inicial_mudas

    resultados_cumulativos["Faturamento Líquido (US$)"] = lucro_liquido

    return resultados_cumulativos, resultados_anuais


def calcular_area_necessaria(num_mudas, sistema):
    if sistema == "SAF":
        return (num_mudas * 4) / 10000  # 4m² por muda no SAF
    else:  # Semi-intensivo
        return (num_mudas * 2.5) / 10000  # 2.5m² por muda no semi-intensivo


def gerar_excel(resultados_anuais, resultados_cumulativos):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="openpyxl")

    df_anuais = pd.DataFrame(resultados_anuais)
    df_cumulativos = pd.DataFrame([resultados_cumulativos])

    df_anuais.to_excel(writer, sheet_name="Anuais", index=False)
    df_cumulativos.to_excel(writer, sheet_name="Cumulativos", index=False)

    writer.close()
    output.seek(0)

    return output


def calcular_plano_acao(num_mudas_inicial, num_mudas_total, anos, sistema, ano_inicio):
    # Calcular a taxa de crescimento necessária
    taxa_crescimento = (num_mudas_total / num_mudas_inicial) ** (1 / (anos - 1))

    # Distribuir as mudas ao longo dos anos
    mudas_por_ano = [num_mudas_inicial]
    for _ in range(1, anos):
        mudas_por_ano.append(
            min(int(mudas_por_ano[-1] * taxa_crescimento), num_mudas_total)
        )

    # Adicionar 3 anos extras mantendo o número máximo de mudas
    for _ in range(15):
        mudas_por_ano.append(num_mudas_total)

    # Inicializar estruturas de dados para rastrear as implementações
    implementacoes = []
    resultados_plano = []
    resultados_detalhados = []
    faturamento_acumulado = 0
    area_total_maxima = calcular_area_necessaria(num_mudas_total, sistema)

    # Definir margem de lucro líquida conforme o sistema de cultivo selecionado
    if sistema == "SAF":
        margem_lucro_liquido = 0.125  # 12.5% para SAF
    else:
        margem_lucro_liquido = 0.34  # 34% para semi-intensivo

    for ano_relativo in range(1, anos + 15 + 1):
        ano_real = ano_inicio + ano_relativo - 1
        faturamento_bruto_anual = 0
        faturamento_liquido_anual = 0
        numero_favas_total = 0
        peso_favas_verdes_total = 0
        peso_favas_curadas_total = 0
        volume_extrato_total = 0

        # Adicionar nova implementação
        if ano_relativo <= anos:
            novas_mudas = mudas_por_ano[ano_relativo - 1] - (
                mudas_por_ano[ano_relativo - 2] if ano_relativo > 1 else 0
            )
            implementacoes.append(
                {"ano_inicio": ano_relativo, "num_mudas": novas_mudas}
            )

        # Calcular produção para cada implementação
        for impl in implementacoes:
            ano_produtivo = ano_relativo - impl["ano_inicio"] + 1
            resultado = calcular_produtividade_baunilha(
                impl["num_mudas"], ano_produtivo
            )

            valor_extrato = resultado["volume_extrato"] * (
                PRECO_EXTRATO_POR_TONELADA / 1000
            )

            # Define a margem de lucro líquida conforme o sistema de cultivo
            if sistema == "SAF":
                margem_lucro_liquido = 0.125  # 12.5% para SAF
            else:
                margem_lucro_liquido = 0.34  # 34% para semi-intensivo

            faturamento_bruto_anual += valor_extrato
            faturamento_liquido_anual += valor_extrato * margem_lucro_liquido

            numero_favas_total += resultado["numero_favas"]
            peso_favas_verdes_total += resultado["peso_favas_verdes"]
            peso_favas_curadas_total += resultado["peso_favas_curadas"]
            volume_extrato_total += resultado["volume_extrato"]

            resultados_detalhados.append(
                {
                    "Ano de Implementação": ano_inicio + impl["ano_inicio"] - 1,
                    "Ano": ano_real,
                    "Número de Mudas": impl["num_mudas"],
                    "Faturamento Bruto (US$)": valor_extrato,
                    "Faturamento Líquido (US$)": valor_extrato * margem_lucro_liquido,
                    "Área Necessária (ha)": calcular_area_necessaria(
                        impl["num_mudas"], sistema
                    ),
                    "Número de Favas": resultado["numero_favas"],
                    "Peso Favas Verdes (kg)": resultado["peso_favas_verdes"],
                    "Peso Favas Curadas (kg)": resultado["peso_favas_curadas"],
                    "Volume Extrato (kg)": resultado["volume_extrato"],
                }
            )

        faturamento_acumulado += faturamento_liquido_anual
        resultados_plano.append(
            {
                "Ano": ano_real,
                "Número de Mudas": mudas_por_ano[ano_relativo - 1],
                "Faturamento Bruto (US$)": faturamento_bruto_anual,
                "Faturamento Líquido (US$)": faturamento_liquido_anual,
                "Faturamento Acumulado (US$)": faturamento_acumulado,
                "Área Total Necessária (ha)": min(
                    area_total_maxima,
                    calcular_area_necessaria(mudas_por_ano[ano_relativo - 1], sistema),
                ),
                "Número Total de Favas": numero_favas_total,
                "Peso Total Favas Verdes (kg)": peso_favas_verdes_total,
                "Peso Total Favas Curadas (kg)": peso_favas_curadas_total,
                "Volume Total Extrato (kg)": volume_extrato_total,
            }
        )

    # Calcular número inicial de mudas para atingir faturamentos específicos
    faturamento_atual = faturamento_acumulado
    fator_20m = (20000000 / faturamento_atual) ** (1 / (anos + 3))
    fator_100m = (100000000 / faturamento_atual) ** (1 / (anos + 3))

    mudas_iniciais_20m = int(num_mudas_inicial * fator_20m)
    mudas_iniciais_100m = int(num_mudas_inicial * fator_100m)

    return (
        pd.DataFrame(resultados_plano),
        pd.DataFrame(resultados_detalhados),
        taxa_crescimento,
        {
            "mudas_iniciais_20m": mudas_iniciais_20m,
            "mudas_iniciais_100m": mudas_iniciais_100m,
        },
    )


# Configuração da página Streamlit
st.set_page_config(
    page_title="Calculadora de Produtividade de Baunilha", page_icon="🌿", layout="wide"
)

# Título principal
st.title("Calculadora de Produtividade de Baunilha 🌿")

# Layout em duas colunas
col1, col2 = st.columns(2)

# Coluna 1: Parâmetros de entrada
with col1:
    st.subheader("Parâmetros de Entrada")
    num_mudas_inicial = st.number_input(
        "Número Inicial de Mudas", min_value=1000, value=4000, step=100
    )
    num_mudas_total = st.number_input(
        "Número Total de Mudas", min_value=num_mudas_inicial, value=100000, step=1000
    )
    anos_projecao = st.slider("Anos de Projeção", min_value=1, max_value=15, value=6)
    ano_inicio = st.number_input(
        "Ano de Início do Cultivo", min_value=2000, value=2024, step=1
    )
    sistema = st.radio("Sistema de Cultivo", ["SAF", "Semi-intensivo"])
    usar_modelo_linear = st.checkbox("Usar modelo linear para anos 1 e 2", value=True)

    # Definir margem de lucro conforme o sistema de cultivo selecionado
    if sistema == "SAF":
        margem_lucro_liquido = 0.125  # 12.5% para SAF
    else:
        margem_lucro_liquido = 0.34  # 34% para semi-intensivo

# Coluna 2: Informações de mercado
with col2:
    st.subheader("Informações de Mercado")
    st.write("Preços de referência:")
    st.write("- Fava verde: US$ 35/kg")
    st.write("- Fava verde (unidade): US$ 0.70")
    st.write("- Fava curada: US$ 139.75/kg")
    st.write("- Fava curada (unidade): US$ 0.56")
    st.write("- Extrato de baunilha: US$ 135,435.20 por tonelada")
    st.write(
        f"- Margem de lucro: {margem_lucro_liquido * 100:.2f}% do faturamento bruto"
    )


# Botão para gerar o plano de ação
if st.button("Gerar Plano de Ação"):
    plano_acao, resultados_detalhados, taxa_crescimento, info = calcular_plano_acao(
        num_mudas_inicial, num_mudas_total, anos_projecao, sistema, ano_inicio
    )

    st.success(
        f"Plano de ação gerado de {num_mudas_inicial} a {num_mudas_total} mudas em {anos_projecao} anos, iniciando em {ano_inicio}."
    )
    st.info(
        f"Taxa de crescimento anual necessária: {(taxa_crescimento - 1) * 100:.2f}%"
    )

    # Exibir tabelas de resultados
    st.subheader("Plano de Ação")
    st.dataframe(
        plano_acao.style.format(
            {
                "Faturamento Bruto (US$)": "${:,.2f}",
                "Faturamento Líquido (US$)": "${:,.2f}",
                "Faturamento Acumulado (US$)": "${:,.2f}",
                "Área Total Necessária (ha)": "{:,.2f}",
                "Número Total de Favas": "{:,.0f}",
                "Peso Total Favas Verdes (kg)": "{:,.2f}",
                "Peso Total Favas Curadas (kg)": "{:,.2f}",
                "Volume Total Extrato (kg)": "{:,.2f}",
            }
        )
    )

    st.subheader("Resultados Detalhados")
    st.dataframe(
        resultados_detalhados.style.format(
            {
                "Faturamento Bruto (US$)": "${:,.2f}",
                "Faturamento Líquido (US$)": "${:,.2f}",
                "Área Necessária (ha)": "{:,.2f}",
                "Número de Favas": "{:,.0f}",
                "Peso Favas Verdes (kg)": "{:,.2f}",
                "Peso Favas Curadas (kg)": "{:,.2f}",
                "Volume Extrato (kg)": "{:,.2f}",
            }
        )
    )
    # Gráfico de crescimento do número de mudas
    chart_mudas = (
        alt.Chart(plano_acao)
        .mark_line()
        .encode(
            x="Ano", y="Número de Mudas", tooltip=["Ano", "Número de Mudas"]
        )
        .properties(
            title="Crescimento do Número de Mudas", width=600, height=400
        )
    )
    st.altair_chart(chart_mudas, use_container_width=True)

    # Gráfico de faturamento acumulado
    chart_faturamento = (
        alt.Chart(plano_acao)
        .mark_line()
        .encode(
            x="Ano",
            y="Faturamento Acumulado (US$)",
            tooltip=["Ano", "Faturamento Acumulado (US$)"],
        )
        .properties(title="Faturamento Acumulado", width=600, height=400)
    )
    st.altair_chart(chart_faturamento, use_container_width=True)

    # Botões de download
    if st.button("Gerar Tabela Excel"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            plano_acao.to_excel(writer, sheet_name="Plano de Ação", index=False)
            resultados_detalhados.to_excel(
                writer, sheet_name="Resultados Detalhados", index=False
            )

        st.download_button(
            label="Baixar Tabela Excel",
            data=output.getvalue(),
            file_name="plano_acao_baunilha.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # Botões para baixar CSV
    st.download_button(
        label="Baixar Plano de Ação (CSV)",
        data=plano_acao.to_csv(index=False).encode("utf-8"),
        file_name="plano_acao.csv",
        mime="text/csv",
    )

    st.download_button(
        label="Baixar Resultados Detalhados (CSV)",
        data=resultados_detalhados.to_csv(index=False).encode("utf-8"),
        file_name="resultados_detalhados.csv",
        mime="text/csv",
    )

    # Gráfico de detalhamento do plano de ação
    st.header("Gráfico de Detalhamento do Plano de Ação")
    chart_detalhado = (
        alt.Chart(resultados_detalhados)
        .mark_line()
        .encode(
            x="Ano",
            y="Faturamento Líquido (US$)",
            color="Ano de Implementação:N",
            tooltip=["Ano de Implementação", "Ano", "Faturamento Líquido (US$)"],
        )
        .properties(
            title="Faturamento Líquido por Ano de Implementação", width=600, height=400
        )
    )
    st.altair_chart(chart_detalhado, use_container_width=True)

# Informações sobre a cultura da baunilheira
st.header("Sobre a Cultura da Baunilheira")
st.write(
    """
- A baunilha fica produtiva durante 15 anos, chegando à máxima produção depois de seis anos.
- Em um sistema de produção semi intensivo, com 4000 mudas por hectare, os seguintes rendimentos podem ser esperados:
  - Ano 3: 500 kilos
  - Ano 4: 1 tonelada
  - Ano 5: 1.6 tonelada
  - Ano 6: 2.5 toneladas
  - Demais anos: Entre 2.5 e 3 toneladas
- A produtividade média sugerida é de 0.5 a 1 kilo por pé de baunilha.
- Para os anos 1 e 2, um modelo linear é usado para estimar a produção, assumindo um crescimento gradual até o ano 3.
- Uma muda na produtividade mais alta (aos 6 anos) produz aproximadamente 30 favas.
- Cada fava verde tem cerca de 20g.
- Cada fava curada tem cerca de 4g.
- No sistema agroflorestal (SAF), cada muda ocupa 4m².
- No sistema semi-intensivo, cada muda ocupa 2.5m².
- Preços de referência (sujeitos a variações de mercado):
  - Fava verde: US$ 35/kg
  - Fava curada: US$ 139.75/kg
  - Extrato de baunilha: US$ 135,435.20 por tonelada
- O extrato de baunilha é feito com 25% de favas curadas.
"""
)
