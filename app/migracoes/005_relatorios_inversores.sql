-- 005_relatorios_inversores.sql
-- Armazena leituras originais dos relatorios PHB e KSTAR sem agrega-las.

CREATE TABLE IF NOT EXISTS phb_leitura (
    ts_utc TEXT PRIMARY KEY NOT NULL,
    ts_local TEXT NOT NULL,
    potencia_w REAL,
    energia_intervalo_kwh REAL,
    i_ac_1_a REAL,
    i_ac_2_a REAL,
    i_ac_3_a REAL,
    temperatura_c REAL,
    inversores_ativos INTEGER,
    inversores_total INTEGER,
    modo_texto TEXT,
    qualidade TEXT,
    arquivo TEXT
);

CREATE INDEX IF NOT EXISTS idx_phb_ts_local
    ON phb_leitura (ts_local);

CREATE TABLE IF NOT EXISTS kstar_leitura (
    ts_utc TEXT PRIMARY KEY NOT NULL,
    ts_local TEXT NOT NULL,
    potencia_w REAL,
    energia_total_kwh REAL,
    energia_intervalo_kwh REAL,
    pv1_w REAL,
    pv2_w REAL,
    pv3_w REAL,
    pv1_v REAL,
    pv2_v REAL,
    pv3_v REAL,
    pv1_a REAL,
    pv2_a REAL,
    pv3_a REAL,
    temp_radiador_c REAL,
    modo TEXT,
    modo_original TEXT,
    modo_inferido INTEGER CHECK (modo_inferido IN (0, 1)),
    hora_corrigida INTEGER CHECK (hora_corrigida IN (0, 1)),
    qualidade TEXT,
    arquivo TEXT
);

CREATE INDEX IF NOT EXISTS idx_kstar_ts_local
    ON kstar_leitura (ts_local);
