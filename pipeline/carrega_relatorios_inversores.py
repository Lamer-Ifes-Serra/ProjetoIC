"""Load normalized PHB and KSTAR CSV reports into their source tables."""

import csv
from datetime import datetime


PHB_COLUNAS = (
    "ts_utc", "ts_local", "potencia_w", "energia_intervalo_kwh",
    "i_ac_1_a", "i_ac_2_a", "i_ac_3_a", "temperatura_c",
    "inversores_ativos", "inversores_total", "modo_texto", "qualidade", "arquivo",
)
KSTAR_COLUNAS = (
    "ts_utc", "ts_local", "potencia_w", "energia_total_kwh", "energia_intervalo_kwh",
    "pv1_w", "pv2_w", "pv3_w", "pv1_v", "pv2_v", "pv3_v",
    "pv1_a", "pv2_a", "pv3_a", "temp_radiador_c", "modo", "modo_original",
    "modo_inferido", "hora_corrigida", "qualidade", "arquivo",
)

PHB_REAIS = (
    "potencia_w", "energia_intervalo_kwh", "i_ac_1_a", "i_ac_2_a", "i_ac_3_a",
    "temperatura_c",
)
PHB_INTEIROS = ("inversores_ativos", "inversores_total")
KSTAR_REAIS = (
    "potencia_w", "energia_total_kwh", "energia_intervalo_kwh", "pv1_w", "pv2_w",
    "pv3_w", "pv1_v", "pv2_v", "pv3_v", "pv1_a", "pv2_a", "pv3_a",
    "temp_radiador_c",
)
KSTAR_FLAGS = ("modo_inferido", "hora_corrigida")


def _texto_opcional(valor):
    valor = "" if valor is None else str(valor).strip()
    return valor or None


def _real_opcional(valor, coluna):
    texto = _texto_opcional(valor)
    if texto is None:
        return None
    try:
        return float(texto)
    except ValueError as exc:
        raise ValueError(f"Valor numerico invalido em {coluna}: {texto!r}") from exc


def _inteiro_opcional(valor, coluna):
    texto = _texto_opcional(valor)
    if texto is None:
        return None
    try:
        return int(texto)
    except ValueError as exc:
        raise ValueError(f"Valor inteiro invalido em {coluna}: {texto!r}") from exc


def _flag_opcional(valor, coluna):
    texto = _texto_opcional(valor)
    if texto is None:
        return None
    normalizado = texto.casefold()
    if normalizado in ("true", "1"):
        return 1
    if normalizado in ("false", "0"):
        return 0
    raise ValueError(f"Booleano invalido em {coluna}: {texto!r}; esperado True/False ou 1/0")


def _timestamp(valor, coluna):
    texto = _texto_opcional(valor)
    if texto is None:
        raise ValueError(f"Timestamp obrigatorio vazio: {coluna}")
    try:
        instante = datetime.strptime(texto, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError(
            f"Timestamp invalido em {coluna}: {texto!r}; esperado YYYY-MM-DD HH:MM:SS"
        ) from exc
    return instante.strftime("%Y-%m-%d %H:%M:%S")


def _validar_cabecalho(reader, caminho, colunas):
    cabecalho = reader.fieldnames
    if not cabecalho:
        raise ValueError(f"CSV vazio ou sem cabecalho: {caminho}")
    if len(cabecalho) != len(set(cabecalho)):
        raise ValueError(f"Cabecalho com colunas repetidas: {caminho}")
    faltando = sorted(set(colunas) - set(cabecalho))
    extras = sorted(set(cabecalho) - set(colunas))
    if faltando or extras:
        raise ValueError(f"Cabecalho inesperado em {caminho}; faltando={faltando}, extras={extras}")


def _carregar_csv(caminho, conn, tabela, colunas, converter):
    caminho = str(caminho)
    sql = (
        f"INSERT INTO {tabela} ({', '.join(colunas)}) "
        f"VALUES ({', '.join('?' for _ in colunas)}) "
        "ON CONFLICT(ts_utc) DO NOTHING"
    )
    lidas = 0
    inseridas = 0
    with open(caminho, "r", encoding="utf-8-sig", newline="") as arquivo:
        reader = csv.DictReader(arquivo)
        _validar_cabecalho(reader, caminho, colunas)
        with conn:
            for numero_linha, row in enumerate(reader, start=2):
                lidas += 1
                if None in row:
                    raise ValueError(f"Linha {numero_linha} tem campos extras em {caminho}")
                try:
                    valores = converter(row)
                    cursor = conn.execute(sql, valores)
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Erro na linha {numero_linha} de {caminho}: {exc}") from exc
                inseridas += max(cursor.rowcount, 0)
    return {
        "linhas_lidas": lidas,
        "linhas_inseridas": inseridas,
        "linhas_ignoradas": lidas - inseridas,
    }


def _converter_phb(row):
    ts_utc = _timestamp(row.get("ts_utc"), "ts_utc")
    ts_local = _timestamp(row.get("ts_local"), "ts_local")
    potencia = _real_opcional(row.get("potencia_w"), "potencia_w")
    energia = _real_opcional(row.get("energia_intervalo_kwh"), "energia_intervalo_kwh")
    inversores_ativos = _inteiro_opcional(row.get("inversores_ativos"), "inversores_ativos")
    if (ts_utc[:4] < "2025" and inversores_ativos == 0
            and potencia is None and energia is None):
        inversores_ativos = None

    valores = {
        "ts_utc": ts_utc,
        "ts_local": ts_local,
        "potencia_w": potencia,
        "energia_intervalo_kwh": energia,
        "i_ac_1_a": _real_opcional(row.get("i_ac_1_a"), "i_ac_1_a"),
        "i_ac_2_a": _real_opcional(row.get("i_ac_2_a"), "i_ac_2_a"),
        "i_ac_3_a": _real_opcional(row.get("i_ac_3_a"), "i_ac_3_a"),
        "temperatura_c": _real_opcional(row.get("temperatura_c"), "temperatura_c"),
        "inversores_ativos": inversores_ativos,
        "inversores_total": _inteiro_opcional(row.get("inversores_total"), "inversores_total"),
        "modo_texto": _texto_opcional(row.get("modo_texto")),
        "qualidade": _texto_opcional(row.get("qualidade")),
        "arquivo": _texto_opcional(row.get("arquivo")),
    }
    return tuple(valores[coluna] for coluna in PHB_COLUNAS)


def _converter_kstar(row):
    valores = {"ts_utc": _timestamp(row.get("ts_utc"), "ts_utc")}
    valores["ts_local"] = _timestamp(row.get("ts_local"), "ts_local")
    for coluna in KSTAR_REAIS:
        valores[coluna] = _real_opcional(row.get(coluna), coluna)
    for coluna in KSTAR_FLAGS:
        valores[coluna] = _flag_opcional(row.get(coluna), coluna)
    for coluna in ("modo", "modo_original", "qualidade", "arquivo"):
        valores[coluna] = _texto_opcional(row.get(coluna))
    return tuple(valores[coluna] for coluna in KSTAR_COLUNAS)


def carregar_phb(caminho_csv, conn):
    """Load PHB rows, nulling pre-2025 zero inverter counts with no power/energy."""
    return _carregar_csv(caminho_csv, conn, "phb_leitura", PHB_COLUNAS, _converter_phb)


def carregar_kstar(caminho_csv, conn):
    """Load KSTAR rows at their original cadence and preserve individual MPPTs."""
    return _carregar_csv(caminho_csv, conn, "kstar_leitura", KSTAR_COLUNAS, _converter_kstar)
