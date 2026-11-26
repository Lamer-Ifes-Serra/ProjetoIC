"""
dashboard.py - camada de apresentação sobre o leituras.db.

Este arquivo só LÊ o banco (via consultas.py) e desenha a interface. Toda a
lógica de query fica em consultas.py, e o cálculo de PR fica isolado em
performance_ratio.py -- de propósito, pra não virar um arquivo gigante com
tudo misturado.

Rodar com:  streamlit run dashboard.py
"""

import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import banco
import catalogo_meteorologia as catalogo
import consultas
import performance_ratio as pr

st.set_page_config(page_title="Monitoramento IFES Serra", layout="wide")

INVERSORES = ["INV01", "INV02", "INV03", "INV04"]
CORES_INVERSORES = {
    "INV01": "#1f77b4",
    "INV02": "#2ca02c",
    "INV03": "#d62728",  # vermelho de propósito - é o inversor do achado
    "INV04": "#9467bd",
}


# ------------------------------------------------------------------
# Conexão e dados base (com cache, pra não reabrir o banco a cada clique)
# ------------------------------------------------------------------

@st.cache_data(ttl=300)
def carregar_dados():
    with banco.conectar() as conn:
        return {
            "datas": consultas.datas_disponiveis(conn),
            "resumo": consultas.resumo_diario(conn),
            "hist_inv": consultas.historico_anual_inversores(conn),
            "hist_inv_long": consultas.historico_anual_inversores_long(conn),
            "hist_usina": consultas.historico_anual_usina(conn),
            "cobertura": consultas.cobertura_geral(conn),
        }


@st.cache_data(ttl=300)
def carregar_dia(data_iso):
    with banco.conectar() as conn:
        return consultas.leitura_15min_do_dia(conn, data_iso)


RELATORIOS_DB_ENV = "PROJETOIC_RELATORIOS_DB_PATH"


def _conectar_banco_relatorios(caminho):
    if not os.path.isfile(caminho):
        raise FileNotFoundError(f"Banco de historicos nao encontrado: {caminho}")
    uri = Path(caminho).resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


@st.cache_data(ttl=300)
def carregar_resumo_phb_pagina(caminho):
    conn = _conectar_banco_relatorios(caminho)
    try:
        return consultas.datas_phb(conn), consultas.resumo_phb(conn)
    finally:
        conn.close()


@st.cache_data(ttl=300)
def carregar_resumo_historicos(caminho):
    conn = _conectar_banco_relatorios(caminho)
    try:
        return consultas.resumo_phb(conn), consultas.resumo_kstar(conn)
    finally:
        conn.close()


@st.cache_data(ttl=300)
def carregar_phb_pagina(caminho, inicio, fim):
    conn = _conectar_banco_relatorios(caminho)
    try:
        return consultas.phb_periodo(conn, inicio, fim)
    finally:
        conn.close()


@st.cache_data(ttl=300)
def carregar_resumo_kstar_pagina(caminho):
    conn = _conectar_banco_relatorios(caminho)
    try:
        return consultas.datas_kstar(conn), consultas.resumo_kstar(conn)
    finally:
        conn.close()


@st.cache_data(ttl=300)
def carregar_kstar_pagina(caminho, inicio, fim):
    conn = _conectar_banco_relatorios(caminho)
    try:
        return consultas.kstar_periodo(conn, inicio, fim)
    finally:
        conn.close()


@st.cache_data(ttl=300)
def carregar_resumo_meteorologia_dashboard():
    with banco.conectar() as conn:
        return consultas.resumo_meteorologia(conn), consultas.datas_meteorologia(conn)


@st.cache_data(ttl=300)
def carregar_meteorologia_agregada_dashboard(variavel, modo, inicio, fim):
    with banco.conectar() as conn:
        return consultas.meteorologia_agregada(conn, variavel, modo, inicio, fim)


@st.cache_data(ttl=300)
def carregar_resumo_variavel_meteorologica_dashboard(coluna):
    with banco.conectar() as conn:
        return consultas.resumo_variavel_meteorologica(conn, coluna)


@st.cache_data(ttl=300)
def carregar_resumo_lacunas_meteorologia_dashboard():
    with banco.conectar() as conn:
        return consultas.resumo_lacunas_meteorologia(conn)


@st.cache_data(ttl=300)
def carregar_lacunas_meteorologia_dashboard():
    with banco.conectar() as conn:
        return consultas.lacunas_meteorologia(conn)


@st.cache_data(ttl=300)
def carregar_resumo_ingestao_meteorologia_dashboard():
    with banco.conectar() as conn:
        return consultas.resumo_ingestao_meteorologia(conn)


@st.cache_data(ttl=300)
def carregar_ingestao_meteorologia_dashboard(limite=50):
    with banco.conectar() as conn:
        return consultas.ingestao_meteorologia_periodo(conn, limite=limite)


def _formatar_data_ingestao(valor, incluir_hora=False):
    if not valor:
        return "?"
    try:
        data_hora = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        formato = "%d/%m/%Y %H:%M" if incluir_hora else "%d/%m/%Y"
        return data_hora.strftime(formato)
    except ValueError:
        return str(valor)


def _formatar_numero_meteorologico(valor):
    if valor is None:
        return "—"
    return f"{valor:,.2f}".translate(str.maketrans({",": ".", ".": ","}))



def _formatar_duracao_minutos(minutos):
    dias, resto = divmod(int(minutos), 1440)
    horas, minutos = divmod(resto, 60)
    partes = []
    if dias:
        partes.append(f"{dias} d")
    if horas:
        partes.append(f"{horas} h")
    if minutos or not partes:
        partes.append(f"{minutos} min")
    return " ".join(partes)

# ------------------------------------------------------------------
# Navegacao

pagina = st.sidebar.radio(
    "Seção",
    [
        "Visão geral",
        "Geração da usina",
        "Comparação entre inversores",
        "Histórico 2020–2026",
        "Qualidade dos dados",
        "Meteorologia × Geração",
        "Meteorologia",
        "Alertas e diagnóstico",
        "Histórico PHB",
        "Histórico KSTAR",
    ],
)

if pagina != "Meteorologia":
    try:
        dados = carregar_dados()
    except banco.BancoNaoEncontrado as erro:
        st.error(str(erro))
        st.stop()

    if not dados["datas"]:
        st.warning("O banco existe mas está vazio (nenhum dia em leitura_15min). "
                   "Rode o pipeline (pipeline/integra_usina_meteorologia.py) e depois "
                   "pipeline/carrega_banco.py antes de usar o dashboard.")
        st.stop()



st.sidebar.markdown("---")
st.sidebar.caption(
    "Usina FV de 119 kW AC / 140 kWp — IFES Campus Serra. "
    "Dados de 2 dias de exemplo (22/09/2025 e 22/09/2026); mais dias entram "
    "automaticamente assim que novos relatórios forem processados pelo "
    "pipeline."
)


# ------------------------------------------------------------------
# 1. Visão geral
# ------------------------------------------------------------------

if pagina == "Visão geral":
    st.title("Visão geral — Usina Fotovoltaica IFES Campus Serra")

    cobertura = dados["cobertura"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Dias na base", len(dados["datas"]))
    col2.metric("Registros de 15min", cobertura["total_registros_15min"])
    col3.metric("Com meteorologia", f'{cobertura["pct_meteorologia"]}%')
    col4.metric("Com os 4 inversores", f'{cobertura["pct_4_inversores"]}%')

    if cobertura["timestamps_duplicados"] > 0:
        st.error(f'{cobertura["timestamps_duplicados"]} timestamp(s) duplicado(s) '
                  f'encontrados no banco — isso não deveria acontecer, verificar o pipeline.')
    else:
        st.success("Nenhum timestamp duplicado no banco (checado a cada carregamento).")

    st.subheader("Resumo por dia processado")
    st.dataframe(dados["resumo"], use_container_width=True)

    st.caption(
        "Esta tabela vem direto da tabela `resumo_diario`, gerada pelo pipeline de integração "
        "(um registro por dia processado pelo pipeline)."
    )


# ------------------------------------------------------------------
    st.divider()
    st.subheader("Históricos carregados")
    caminho_relatorios = os.environ.get(RELATORIOS_DB_ENV, banco.DB_PATH)
    try:
        resumo_phb_hist, resumo_kstar_hist = carregar_resumo_historicos(caminho_relatorios)
    except (FileNotFoundError, sqlite3.Error) as erro:
        st.info(f"Não foi possível consultar os históricos PHB/KSTAR: {erro}")
    else:
        st.markdown("**PHB**")
        phb_cols = st.columns(3)
        phb_cols[0].metric("Primeira data", resumo_phb_hist["primeira_data"] or "—")
        phb_cols[1].metric("Última data", resumo_phb_hist["ultima_data"] or "—")
        phb_cols[2].metric("Registros", f'{resumo_phb_hist["total_registros"]:,}'.replace(",", "."))

        st.markdown("**KSTAR**")
        kstar_cols = st.columns(3)
        kstar_cols[0].metric("Primeira data", resumo_kstar_hist["primeira_data"] or "—")
        kstar_cols[1].metric("Última data", resumo_kstar_hist["ultima_data"] or "—")
        kstar_cols[2].metric("Registros", f'{resumo_kstar_hist["total_registros"]:,}'.replace(",", "."))

        total_relatorios = resumo_phb_hist["total_registros"] + resumo_kstar_hist["total_registros"]
        st.metric("Total de registros dos relatórios", f"{total_relatorios:,}".replace(",", "."))


# 2. Geração da usina
# ------------------------------------------------------------------

elif pagina == "Geração da usina":
    st.title("Geração da usina — potência ao longo do dia")

    data_escolhida = st.selectbox("Escolha o dia", dados["datas"])
    df_dia = carregar_dia(data_escolhida)

    if df_dia.empty:
        st.warning("Não há dados de 15min para esse dia.")
    else:
        series_disponiveis = st.multiselect(
            "Séries a mostrar",
            ["Usina (potência total)"] + INVERSORES,
            default=["Usina (potência total)"] + INVERSORES,
        )

        fig = go.Figure()
        if "Usina (potência total)" in series_disponiveis:
            fig.add_trace(go.Scatter(
                x=df_dia["timestamp_15min"], y=df_dia["potencia_fv_kw"],
                name="Usina (medida)", mode="lines", line=dict(width=3, color="black"),
            ))
        for inv in INVERSORES:
            if inv in series_disponiveis:
                fig.add_trace(go.Scatter(
                    x=df_dia["timestamp_15min"], y=df_dia[inv],
                    name=inv, mode="lines", line=dict(color=CORES_INVERSORES[inv]),
                ))
        fig.update_layout(
            xaxis_title="Horário", yaxis_title="Potência (kW)",
            legend_title="Série", height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Usina medida × soma dos inversores")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df_dia["timestamp_15min"], y=df_dia["potencia_fv_kw"],
            name="Usina (medida)", mode="lines",
        ))
        fig2.add_trace(go.Scatter(
            x=df_dia["timestamp_15min"], y=df_dia["potencia_inversores_soma_kw"],
            name="Soma dos 4 inversores", mode="lines", line=dict(dash="dash"),
        ))
        fig2.update_layout(xaxis_title="Horário", yaxis_title="Potência (kW)", height=400)
        st.plotly_chart(fig2, use_container_width=True)

        with banco.conectar() as conn:
            resumo_dia = consultas.resumo_do_dia(conn, data_escolhida)
        if resumo_dia is not None and pd.notna(resumo_dia["correlacao_usina_vs_soma_inversores"]):
            st.metric(
                "Correlação usina × soma dos inversores neste dia",
                f'{resumo_dia["correlacao_usina_vs_soma_inversores"]:.6f}',
            )
        st.caption(
            "As duas curvas quase se sobrepõem quando os 4 inversores têm dado "
            "no mesmo instante — é a validação cruzada feita no pipeline de integração."
        )


# ------------------------------------------------------------------
# 3. Comparação entre inversores
# ------------------------------------------------------------------

elif pagina == "Comparação entre inversores":
    st.title("Comparação entre inversores")

    data_escolhida = st.selectbox("Dia de referência", dados["datas"], key="cmp_dia")
    df_dia = carregar_dia(data_escolhida)

    if not df_dia.empty:
        maximos = {inv: df_dia[inv].max() for inv in INVERSORES}
        cols = st.columns(4)
        for col, inv in zip(cols, INVERSORES):
            valor = maximos[inv]
            texto = f"{valor:.2f} kW" if pd.notna(valor) else "sem dado"
            col.metric(f"Pico {inv}", texto)

        st.info(
            "⚠️ **INV03** aparece com valores bem mais baixos de geração histórica "
            "(veja a seção Histórico 2020–2026) — não é erro de leitura deste dia, "
            "é um padrão que se repete ano após ano."
        )

    st.subheader("Participação na geração anual (2026, ano em curso)")
    df_hist = dados["hist_inv"]
    if not df_hist.empty and "2026" in df_hist.columns:
        fig = px.pie(
            df_hist, names="inversor", values="2026",
            color="inversor", color_discrete_map=CORES_INVERSORES,
            title="Participação de cada inversor na geração de 2026 (parcial)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "2026 é um ano ainda em curso no momento da extração dos dados "
            "(o relatório 'estatístico ALL' cobre até a data em que foi baixado) "
            "— os valores não representam o ano fechado."
        )


# ------------------------------------------------------------------
# 4. Histórico 2020–2026
# ------------------------------------------------------------------

elif pagina == "Histórico 2020–2026":
    st.title("Histórico de geração anual (2020–2026)")

    df_long = dados["hist_inv_long"]
    if df_long.empty:
        st.warning("Sem dados de histórico anual no banco.")
    else:
        fig = px.bar(
            df_long, x="ano", y="geracao_kwh", color="inversor", barmode="group",
            color_discrete_map=CORES_INVERSORES,
            labels={"geracao_kwh": "Geração (kWh)", "ano": "Ano"},
            title="Geração anual por inversor",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.error(
            "**INV03 — achado de diagnóstico:** geração igual a 0 kWh entre 2020 "
            "e 2024 (5 anos seguidos), voltando a gerar em 2025. A causa não foi "
            "determinada a partir dos dados analisados até aqui — fica registrado "
            "como algo a confirmar com quem opera a usina, não como falha do pipeline."
        )

        st.subheader("Tabela completa")
        st.dataframe(dados["hist_inv"], use_container_width=True)
        st.dataframe(dados["hist_usina"], use_container_width=True)


# ------------------------------------------------------------------
# 5. Qualidade dos dados
# ------------------------------------------------------------------

elif pagina == "Qualidade dos dados":
    st.title("Qualidade e cobertura dos dados")

    cobertura = dados["cobertura"]
    col1, col2, col3 = st.columns(3)
    col1.metric("Registros de 15min", cobertura["total_registros_15min"])
    col2.metric("Com meteorologia", f'{cobertura["com_meteorologia"]} ({cobertura["pct_meteorologia"]}%)')
    col3.metric("Com 4 inversores", f'{cobertura["com_4_inversores"]} ({cobertura["pct_4_inversores"]}%)')

    st.subheader("Correlação usina × soma dos inversores, por dia")
    st.dataframe(
        dados["resumo"][["data", "correlacao_usina_vs_soma_inversores",
                          "registros_com_meteorologia", "registros_15min"]],
        use_container_width=True,
    )

    st.subheader("Timestamps duplicados")
    if cobertura["timestamps_duplicados"] == 0:
        st.success("0 timestamps duplicados em `leitura_15min` (testado a cada carregamento do dashboard).")
    else:
        st.error(f'{cobertura["timestamps_duplicados"]} timestamps duplicados encontrados.')

    st.caption(
        "Esta página existe porque o diferencial do projeto não é só mostrar "
        "geração — é mostrar o quanto se pode confiar no dado que está sendo mostrado."
    )


# ------------------------------------------------------------------
    st.divider()
    st.subheader("Cobertura dos históricos carregados")
    caminho_relatorios = os.environ.get(RELATORIOS_DB_ENV, banco.DB_PATH)
    try:
        resumo_phb_hist, resumo_kstar_hist = carregar_resumo_historicos(caminho_relatorios)
    except (FileNotFoundError, sqlite3.Error) as erro:
        st.info(f"Não foi possível consultar a cobertura PHB/KSTAR: {erro}")
    else:
        cobertura_hist = pd.DataFrame([
            {
                "Fonte": "PHB",
                "Início": resumo_phb_hist["primeira_data"] or "—",
                "Fim": resumo_phb_hist["ultima_data"] or "—",
                "Registros": resumo_phb_hist["total_registros"],
            },
            {
                "Fonte": "KSTAR",
                "Início": resumo_kstar_hist["primeira_data"] or "—",
                "Fim": resumo_kstar_hist["ultima_data"] or "—",
                "Registros": resumo_kstar_hist["total_registros"],
            },
        ])
        st.dataframe(cobertura_hist, use_container_width=True, hide_index=True)
        qualidade_cols = st.columns(3)
        qualidade_cols[0].metric(
            "PHB com temperatura",
            f'{resumo_phb_hist["registros_com_temperatura"]:,}'.replace(",", "."),
        )
        qualidade_cols[1].metric("KSTAR hora corrigida", f'{resumo_kstar_hist["pct_hora_corrigida"]}%')
        qualidade_cols[2].metric("KSTAR modo inferido", f'{resumo_kstar_hist["pct_modo_inferido"]}%')


# 6. Meteorologia × Geração
# ------------------------------------------------------------------

elif pagina == "Meteorologia × Geração":
    st.title("Meteorologia × Geração")

    data_escolhida = st.selectbox("Dia", dados["datas"], key="meteo_dia")
    df_dia = carregar_dia(data_escolhida)

    if df_dia.empty or not df_dia["meteorologia_disponivel"].any():
        st.warning(
            f"Não há dados meteorológicos integrados disponíveis para {data_escolhida}. "
            "O dashboard não calcula o Performance Ratio sem dados meteorológicos "
            "correspondentes."
        )
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_dia["timestamp_15min"], y=df_dia["ghi_lppyra02_w_m2"],
            name="Irradiância LPPYRA02 (W/m²)", yaxis="y1",
        ))
        fig.add_trace(go.Scatter(
            x=df_dia["timestamp_15min"], y=df_dia["ghi_lpnet14_w_m2"],
            name="Irradiância LPNET14 (W/m²)", yaxis="y1",
        ))
        fig.add_trace(go.Scatter(
            x=df_dia["timestamp_15min"], y=df_dia["potencia_fv_kw"],
            name="Potência da usina (kW)", yaxis="y2", line=dict(color="black"),
        ))
        fig.update_layout(
            xaxis_title="Horário",
            yaxis=dict(title="Irradiância (W/m²)"),
            yaxis2=dict(title="Potência (kW)", overlaying="y", side="right"),
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Performance Ratio (PR)")
        resultado_pr = pr.calcular_pr(df_dia)
        if resultado_pr is None:
            st.warning(
                "PR não calculado para este dia: nem todos os registros de 15min "
                "têm irradiância disponível (o cálculo exige cobertura completa "
                "pra não distorcer o resultado)."
            )
        else:
            colp1, colp2, colp3 = st.columns(3)
            colp1.metric("PR do dia", resultado_pr["pr"])
            colp2.metric("Energia gerada (kWh)", resultado_pr["energia_ac_kwh"])
            colp3.metric("Horas de sol pleno (Yr)", resultado_pr["yr_horas_sol_pleno"])
            with st.expander("Como esse PR foi calculado (fórmula e premissas)"):
                st.markdown(f"""
- **Fórmula (IEC 61724):** `PR = Yf / Yr`, onde `Yf = Energia_AC / P_nominal` e
  `Yr = Insolação (kWh/m²) / 1 kW/m²`.
- **P_nominal usado:** {resultado_pr['p_nominal_kwp_usado']} kWp (potência DC
  nominal dos módulos — não confundir com os 119 kW AC, que é o limite de
  saída dos inversores).
- **Irradiância:** média entre os dois sensores da MAWS55 (LPPYRA02 e
  LPNET14), por não ter informação de calibração de qual é mais confiável.
- **Registros usados:** {resultado_pr['registros_usados']} de 96 possíveis
  (só calculamos quando 100% dos intervalos do dia têm irradiância).
- **Limitação:** PR de 1 dia é sensível a nuvens passageiras e não substitui
  uma análise de período mais longo (mês/ano).
""")


# ------------------------------------------------------------------
# 7. Alertas e diagnóstico
# ------------------------------------------------------------------

elif pagina == "Alertas e diagnóstico":
    st.title("Alertas e diagnóstico")

    st.error(
        "**INV03 — geração zero por 5 anos.** Histórico indica geração igual "
        "a 0 kWh entre 2020 e 2024. Causa não determinada pelos dados "
        "analisados — a confirmar com os responsáveis pela operação da usina."
    )

    st.warning(
        "**INV04 — potência nominal assumida.** A análise usa 14 kW como "
        "potência nominal do INV04 (os outros três são 35 kW cada). Esse "
        "valor ainda depende de confirmação documental — a evidência a favor "
        "é que 35+35+35+14 = 119 kW, batendo exatamente com a potência AC "
        "total da usina, mas isso não é uma prova definitiva."
    )

    st.info(
        "**Cobertura meteorológica.** A base operacional da MAWS55 recebe dados "
        "diretamente do FTP e é atualizada automaticamente. A disponibilidade "
        "meteorológica nas análises integradas depende da correspondência temporal "
        "com os dados elétricos; períodos ausentes não são preenchidos artificialmente."
    )

    st.info(
        "**Strings desconectadas (INV01).** As entradas PV-2, PV-5, PV-8 e PV-11 "
        "do INV01 aparecem com corrente 0,00 A de forma consistente — interpretado "
        "como entrada sem string física conectada, não como falha."
    )

    st.info(
        "**Espaço Energia (KSTAR, 3 kWp).** O histórico de relatórios está "
        "carregado e disponível nas páginas Histórico PHB e Histórico KSTAR."
    )

    st.caption(
        "Esta página reúne achados derivados dos dados processados pelo pipeline. "
        "Os diagnósticos devem ser interpretados no contexto da fonte e do período "
        "analisado; causas operacionais exigem confirmação em campo."
    )

# ------------------------------------------------------------------
# 8. Historico PHB
# ------------------------------------------------------------------

elif pagina == "Histórico PHB":
    st.title("Histórico PHB")
    caminho_relatorios = os.environ.get(RELATORIOS_DB_ENV, banco.DB_PATH)

    try:
        datas_hist, resumo_hist = carregar_resumo_phb_pagina(caminho_relatorios)
    except (FileNotFoundError, sqlite3.Error) as erro:
        st.error(f"Nao foi possivel consultar o historico PHB: {erro}")
        st.caption(
            "O banco selecionado precisa conter as tabelas e views PHB. "
            f"Para usar outro banco, configure {RELATORIOS_DB_ENV}."
        )
    else:
        if not datas_hist:
            st.info("Ainda nao ha leituras PHB neste banco.")
        else:
            st.caption(
                f"Periodo disponivel: {datas_hist[0][:4]} a {datas_hist[-1][:4]}. "
                "Os indicadores resumem todo o historico; o filtro controla os graficos."
            )
            c1, c2, c3 = st.columns(3)
            c1.metric("Primeira data", resumo_hist["primeira_data"])
            c2.metric("Ultima data", resumo_hist["ultima_data"])
            c3.metric("Registros", f"{resumo_hist['total_registros']:,}".replace(",", "."))
            c4, c5, c6 = st.columns(3)
            c4.metric("Dias com potencia", resumo_hist["dias_com_potencia"])
            c5.metric("Dias com energia", resumo_hist["dias_com_energia"])
            c6.metric("Dias com temperatura", resumo_hist["dias_com_temperatura"])

            inicio_disp = date.fromisoformat(datas_hist[0])
            fim_disp = date.fromisoformat(datas_hist[-1])
            periodo = st.date_input(
                "Periodo local dos graficos",
                value=(inicio_disp, fim_disp),
                min_value=inicio_disp,
                max_value=fim_disp,
                key="historico_phb_periodo",
            )
            if not isinstance(periodo, (tuple, list)) or len(periodo) != 2:
                st.info("Selecione as datas inicial e final para exibir os graficos.")
            else:
                inicio, fim = (valor.isoformat() for valor in periodo)
                try:
                    df_hist = carregar_phb_pagina(caminho_relatorios, inicio, fim)
                except (FileNotFoundError, sqlite3.Error) as erro:
                    st.error(f"Falha ao carregar o periodo PHB: {erro}")
                else:
                    if df_hist.empty:
                        st.info("Nao ha registros PHB no intervalo selecionado.")
                    else:
                        st.caption(f"{len(df_hist):,} leituras no intervalo.".replace(",", "."))
                        graficos = [
                            ("potencia_w", "Potencia (W)"),
                            ("energia_intervalo_kwh", "Energia do intervalo (kWh)"),
                            ("temperatura_c", "Temperatura (C)"),
                            ("inversores_ativos", "Inversores ativos"),
                        ]
                        for pos in range(0, len(graficos), 2):
                            colunas = st.columns(2)
                            for coluna, (campo, rotulo) in zip(colunas, graficos[pos:pos + 2]):
                                if df_hist[campo].notna().any():
                                    figura = px.line(
                                        df_hist, x="ts_local", y=campo, title=rotulo,
                                        labels={"ts_local": "Data/hora local", campo: rotulo},
                                    )
                                    coluna.plotly_chart(figura, width="stretch")
                                else:
                                    coluna.info(f"Sem valores de {rotulo.lower()} neste intervalo.")


# ------------------------------------------------------------------
# 9. Historico KSTAR
# ------------------------------------------------------------------

elif pagina == "Histórico KSTAR":
    st.title("Histórico KSTAR")
    caminho_relatorios = os.environ.get(RELATORIOS_DB_ENV, banco.DB_PATH)

    try:
        datas_hist, resumo_hist = carregar_resumo_kstar_pagina(caminho_relatorios)
    except (FileNotFoundError, sqlite3.Error) as erro:
        st.error(f"Nao foi possivel consultar o historico KSTAR: {erro}")
        st.caption(
            "O banco selecionado precisa conter as tabelas e views KSTAR. "
            f"Para usar outro banco, configure {RELATORIOS_DB_ENV}."
        )
    else:
        if not datas_hist:
            st.info("Ainda nao ha leituras KSTAR neste banco.")
        else:
            st.caption(
                f"Periodo disponivel: {datas_hist[0][:4]} a {datas_hist[-1][:4]}. "
                "Os indicadores resumem todo o historico; o filtro controla os graficos."
            )
            c1, c2, c3 = st.columns(3)
            c1.metric("Primeira data", resumo_hist["primeira_data"])
            c2.metric("Ultima data", resumo_hist["ultima_data"])
            c3.metric("Registros", f"{resumo_hist['total_registros']:,}".replace(",", "."))
            c4, c5 = st.columns(2)
            c4.metric("Horario corrigido", f"{resumo_hist['pct_hora_corrigida']}%")
            c5.metric("Modo inferido", f"{resumo_hist['pct_modo_inferido']}%")

            inicio_disp = date.fromisoformat(datas_hist[0])
            fim_disp = date.fromisoformat(datas_hist[-1])
            periodo = st.date_input(
                "Periodo local dos graficos",
                value=(inicio_disp, fim_disp),
                min_value=inicio_disp,
                max_value=fim_disp,
                key="historico_kstar_periodo",
            )
            if not isinstance(periodo, (tuple, list)) or len(periodo) != 2:
                st.info("Selecione as datas inicial e final para exibir os graficos.")
            else:
                inicio, fim = (valor.isoformat() for valor in periodo)
                try:
                    df_hist = carregar_kstar_pagina(caminho_relatorios, inicio, fim)
                except (FileNotFoundError, sqlite3.Error) as erro:
                    st.error(f"Falha ao carregar o periodo KSTAR: {erro}")
                else:
                    if df_hist.empty:
                        st.info("Nao ha registros KSTAR no intervalo selecionado.")
                    else:
                        st.caption(f"{len(df_hist):,} leituras no intervalo.".replace(",", "."))
                        figura = px.line(
                            df_hist,
                            x="ts_local",
                            y=["potencia_w", "pv1_w", "pv2_w", "pv3_w"],
                            title="Potencia total e canais PV",
                            labels={
                                "ts_local": "Data/hora local",
                                "value": "Potencia (W)",
                                "variable": "Serie",
                            },
                        )
                        st.plotly_chart(figura, width="stretch")

# ------------------------------------------------------------------
# 10. Meteorologia independente
# ------------------------------------------------------------------

elif pagina == "Meteorologia":
    st.title("Meteorologia")
    try:
        resumo_meteo, datas_meteo = carregar_resumo_meteorologia_dashboard()
        resumo_lacunas = carregar_resumo_lacunas_meteorologia_dashboard()
    except (banco.BancoNaoEncontrado, sqlite3.Error) as erro:
        st.error(f"Não foi possível consultar meteorologia_15min: {erro}")
    else:
        indicadores = st.columns(5)
        primeira_data = (
            date.fromisoformat(resumo_meteo["primeira_data"]).strftime("%d/%m/%Y")
            if resumo_meteo["primeira_data"] else "—"
        )
        ultima_data = (
            date.fromisoformat(resumo_meteo["ultima_data"]).strftime("%d/%m/%Y")
            if resumo_meteo["ultima_data"] else "—"
        )
        indicadores[0].metric("Primeiro registro", primeira_data)
        indicadores[1].metric("Último registro", ultima_data)
        indicadores[2].metric("Registros", f'{resumo_meteo["total_registros"]:,}'.replace(",", "."))
        indicadores[3].metric("Dias", resumo_meteo["total_dias"])
        indicadores[4].metric(
            "Maior lacuna",
            _formatar_duracao_minutos(resumo_lacunas["maior_lacuna_min"]),
        )
        indicadores_lacunas = st.columns(2)
        indicadores_lacunas[0].metric(
            "Quantidade de lacunas", resumo_lacunas["quantidade_lacunas"]
        )
        indicadores_lacunas[1].metric(
            "Registros ausentes", resumo_lacunas["total_registros_ausentes"]
        )

        if not datas_meteo:
            st.info("A tabela meteorologia_15min ainda nao tem registros.")
        else:
            st.subheader("10 maiores lacunas")
            df_lacunas = carregar_lacunas_meteorologia_dashboard()
            if df_lacunas.empty:
                st.info("Nenhuma lacuna de 15 minutos foi encontrada.")
            else:
                df_lacunas_top = (
                    df_lacunas.sort_values(
                        ["minutos_ausentes", "registros_ausentes"], ascending=False
                    )
                    .head(10)
                    .rename(columns={
                        "inicio": "Início",
                        "fim": "Fim",
                        "minutos_ausentes": "Minutos ausentes",
                        "registros_ausentes": "Registros ausentes",
                    })
                )
                st.dataframe(df_lacunas_top, use_container_width=True, hide_index=True)

            data_minima = date.fromisoformat(datas_meteo[0])
            data_maxima = date.fromisoformat(datas_meteo[-1])
            variaveis = catalogo.variaveis_da_tabela_meteorologia()
            opcoes_variaveis = {
                f"{variavel.descricao} ({variavel.unidade}) — {variavel.coluna}": variavel.coluna
                for variavel in variaveis
            }
            filtros = st.columns([1, 1, 3])
            data_inicio = filtros[0].date_input(
                "Data inicial", value=data_minima, min_value=data_minima, max_value=data_maxima,
                key="meteorologia_data_inicio",
            )
            data_fim = filtros[1].date_input(
                "Data final", value=data_maxima, min_value=data_minima, max_value=data_maxima,
                key="meteorologia_data_fim",
            )
            rotulo_variavel = filtros[2].selectbox(
                "Variável meteorológica", list(opcoes_variaveis), key="meteorologia_variavel"
            )
            coluna = opcoes_variaveis[rotulo_variavel]
            periodo_visualizacao = st.radio(
                "Escala temporal",
                ["Dia", "Mês", "Ano", "Todos"],
                horizontal=True,
                key="meteorologia_escala_temporal",
            )
            metadados_variavel = next(v for v in variaveis if v.coluna == coluna)
            if coluna in catalogo.VARIAVEIS_ACUMULATIVAS:
                nome_variavel = f"{metadados_variavel.grupo} acumulada"
            else:
                nome_variavel = metadados_variavel.descricao.split(" (", 1)[0]

            st.subheader("Estatísticas da variável")
            st.caption("Estatísticas calculadas sobre todos os registros meteorológicos; o período filtra o gráfico.")
            try:
                estatisticas = carregar_resumo_variavel_meteorologica_dashboard(coluna)
            except sqlite3.Error as erro:
                st.error(f"Falha ao calcular estatísticas em meteorologia_15min: {erro}")
            else:
                estatisticas_1 = st.columns(4)
                estatisticas_1[0].metric("Mínimo", _formatar_numero_meteorologico(estatisticas["minimo"]))
                estatisticas_1[1].metric("Máximo", _formatar_numero_meteorologico(estatisticas["maximo"]))
                estatisticas_1[2].metric("Média", _formatar_numero_meteorologico(estatisticas["media"]))
                estatisticas_1[3].metric("Mediana", _formatar_numero_meteorologico(estatisticas["mediana"]))
                estatisticas_2 = st.columns(3)
                estatisticas_2[0].metric("Válidos", f'{estatisticas["nao_nulos"]:,}'.replace(",", "."))
                estatisticas_2[1].metric("Nulos", f'{estatisticas["nulos"]:,}'.replace(",", "."))
                percentual = f'{estatisticas["percentual_valido"]:.1f}'.replace(".", ",")
                estatisticas_2[2].metric("Percentual válido", f"{percentual}%")

            if data_inicio > data_fim:
                st.warning("A data inicial deve ser anterior ou igual à data final.")
            else:
                try:
                    df_meteo = carregar_meteorologia_agregada_dashboard(
                        coluna,
                        periodo_visualizacao,
                        data_inicio.isoformat(),
                        data_fim.isoformat(),
                    )
                except sqlite3.Error as erro:
                    st.error(f"Falha ao carregar meteorologia_15min: {erro}")
                else:
                    df_grafico = df_meteo[["timestamp_15min", coluna]].dropna(subset=[coluna])
                    if df_grafico.empty:
                        st.info("Não há valores válidos desta variável no intervalo selecionado.")
                    else:
                        figura = px.line(
                            df_grafico,
                            x="timestamp_15min",
                            y=coluna,
                            title=f"{nome_variavel} — {periodo_visualizacao}",
                            labels={
                                "timestamp_15min": "Data/hora",
                                coluna: nome_variavel,
                            },
                        )
                        st.caption(
                            f"{len(df_grafico):,} pontos na escala {periodo_visualizacao}.".replace(",", ".")
                        )
                        st.plotly_chart(figura, width="stretch")

        st.divider()
        st.subheader("Diário de ingestão")
        try:
            resumo_ingestao = carregar_resumo_ingestao_meteorologia_dashboard()
            eventos_ingestao = carregar_ingestao_meteorologia_dashboard(limite=50)
        except sqlite3.Error as erro:
            st.error(f"Falha ao consultar o diário de ingestão: {erro}")
        else:
            if resumo_ingestao["ultima_aquisicao"] is None:
                st.info("Nenhum registro de ingestão encontrado.")
            indicadores_ingestao = st.columns(4)
            indicadores_ingestao[0].metric(
                "Última aquisição",
                _formatar_data_ingestao(resumo_ingestao["ultima_aquisicao"], incluir_hora=True),
            )
            indicadores_ingestao[1].metric("Arquivos OK", resumo_ingestao["arquivos_ok"])
            indicadores_ingestao[2].metric("Arquivos com erro", resumo_ingestao["arquivos_erro"])
            primeiro_registro = _formatar_data_ingestao(resumo_ingestao["primeiro_registro"])
            ultimo_registro = _formatar_data_ingestao(resumo_ingestao["ultimo_registro"])
            indicadores_ingestao[3].metric(
                "Período coberto",
                f"{primeiro_registro} → {ultimo_registro}"
                if primeiro_registro != "—" or ultimo_registro != "—" else "—",
            )
            if not eventos_ingestao.empty:
                eventos_visiveis = eventos_ingestao.rename(columns={
                    "data_hora": "Data/Hora",
                    "arquivo": "Arquivo",
                    "status": "Status",
                    "mensagem": "Mensagem",
                }).copy()
                eventos_visiveis["Data/Hora"] = eventos_visiveis["Data/Hora"].map(
                    lambda valor: _formatar_data_ingestao(valor, incluir_hora=True)
                )
                st.dataframe(eventos_visiveis, use_container_width=True, hide_index=True)
