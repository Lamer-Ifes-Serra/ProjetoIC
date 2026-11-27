"""Geração idempotente dos alarmes sustentados por critérios já definidos.

As funções recebem uma conexão SQLite já aberta e confirmam (commit) somente
os alarmes novos. Nenhuma função é chamada automaticamente pelo dashboard ou
pelo pipeline.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import consultas

UTC = timezone.utc
FUSO_METEOROLOGIA = ZoneInfo("America/Sao_Paulo")


def _timestamp_utc(valor, timestamp_local=False):
    """Normalize a source timestamp to the schema's naive UTC text format."""
    instante = datetime.fromisoformat(str(valor))
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=FUSO_METEOROLOGIA if timestamp_local else UTC)
    instante = instante.astimezone(UTC).replace(tzinfo=None)
    return instante.strftime("%Y-%m-%d %H:%M:%S")


def _criado_em_utc():
    return datetime.now(UTC).replace(microsecond=0, tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


def _inserir_eventos(conn, eventos):
    eventos = list(eventos)
    if not eventos:
        return 0
    try:
        cursor = conn.executemany(
            """INSERT OR IGNORE INTO historico_alarmes
               (timestamp_evento, origem, codigo, severidade, titulo,
                descricao, referencia, criado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            eventos,
        )
        inseridos = int(cursor.rowcount)
        conn.commit()
        return inseridos
    except Exception:
        conn.rollback()
        raise


def gerar_alarmes_meteorologia(conn):
    """Create one warning per detected meteorological gap."""
    eventos = []
    for linha in consultas.lacunas_meteorologia(conn).to_dict("records"):
        inicio_local = datetime.fromisoformat(str(linha["inicio"]))
        fim_local = datetime.fromisoformat(str(linha["fim"]))
        primeiro_slot_ausente = inicio_local + timedelta(minutes=15)
        inicio_utc = _timestamp_utc(inicio_local, timestamp_local=True)
        fim_utc = _timestamp_utc(fim_local, timestamp_local=True)
        timestamp_evento = _timestamp_utc(primeiro_slot_ausente, timestamp_local=True)
        minutos = int(linha["minutos_ausentes"])
        registros = int(linha["registros_ausentes"])
        referencia = f"{inicio_utc}/{fim_utc}"
        descricao = (
            f"Faltaram {registros} registros de 15 minutos ({minutos} min) "
            f"entre os horários observados {inicio_utc} e {fim_utc} UTC."
        )
        eventos.append((
            timestamp_evento,
            "meteorologia",
            "lacuna_dados",
            "aviso",
            "Lacuna meteorológica detectada",
            descricao,
            referencia,
            _criado_em_utc(),
        ))
    return _inserir_eventos(conn, eventos)


def gerar_alarmes_phb(conn):
    """Create one warning per UTC date carrying the validated PHB quality flag."""
    linhas = conn.execute(
        """SELECT DATE(ts_utc) AS dia_utc, MIN(ts_utc), COUNT(*),
                  GROUP_CONCAT(DISTINCT arquivo)
           FROM phb_leitura
           WHERE instr(COALESCE(qualidade, ''), 'energia_diverge_da_potencia') > 0
             AND ts_utc IS NOT NULL
           GROUP BY DATE(ts_utc)
           ORDER BY DATE(ts_utc)"""
    ).fetchall()
    eventos = []
    for dia_utc, primeiro_ts, quantidade, arquivos in linhas:
        descricao = (
            f"{quantidade} registros PHB neste dia foram marcados pelo normalizador "
            "com energia divergente da potência."
        )
        if arquivos:
            descricao += f" Arquivo(s): {arquivos}."
        eventos.append((
            _timestamp_utc(primeiro_ts),
            "phb",
            "energia_diverge_da_potencia",
            "aviso",
            "Divergência entre energia e potência no PHB",
            descricao,
            dia_utc,
            _criado_em_utc(),
        ))
    return _inserir_eventos(conn, eventos)


def gerar_alarmes_kstar(conn):
    """Create one historical summary event for all available corrected samples.

    A single event summarizes the observed correction interval, rather than
    creating one alarm per sample. The interval may contain gaps in source data.
    """
    linha = conn.execute(
        """SELECT MIN(ts_utc), MAX(ts_utc), COUNT(*),
                  GROUP_CONCAT(DISTINCT qualidade)
           FROM kstar_leitura
           WHERE hora_corrigida = 1 AND ts_utc IS NOT NULL"""
    ).fetchone()
    primeiro_ts, ultimo_ts, quantidade, qualidades = linha
    if not quantidade:
        return 0

    inicio_utc = _timestamp_utc(primeiro_ts)
    fim_utc = _timestamp_utc(ultimo_ts)
    descricao = (
        f"{quantidade} amostras KSTAR foram marcadas como hora corrigida. "
        f"Intervalo observado: {inicio_utc} a {fim_utc} UTC; o intervalo pode conter "
        "lacunas de dados."
    )
    if qualidades:
        descricao += f" Qualidade registrada: {qualidades}."
    referencia = f"{inicio_utc}/{fim_utc}"
    evento = (
        inicio_utc,
        "kstar",
        "hora_corrigida",
        "informacao",
        "Período histórico com hora corrigida",
        descricao,
        referencia,
        _criado_em_utc(),
    )
    return _inserir_eventos(conn, [evento])


def gerar_alarmes(conn):
    """Generate the currently approved meteorology, PHB, and KSTAR alarms."""
    resultado = {
        "meteorologia": gerar_alarmes_meteorologia(conn),
        "phb": gerar_alarmes_phb(conn),
        "kstar": gerar_alarmes_kstar(conn),
    }
    resultado["total"] = sum(resultado.values())
    return resultado
