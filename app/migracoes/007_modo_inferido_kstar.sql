-- 007_modo_inferido_kstar.sql
-- Acrescenta a contagem de modos inferidos as views KSTAR existentes.

DROP VIEW IF EXISTS vw_kstar_resumo_diario;
CREATE VIEW vw_kstar_resumo_diario AS
SELECT
    DATE(ts_local) AS data,
    COUNT(*) AS registros,
    SUM(energia_intervalo_kwh) AS energia_intervalo_kwh,
    MAX(potencia_w) AS potencia_max_w,
    MAX(pv1_w) AS pv1_max_w,
    MAX(pv2_w) AS pv2_max_w,
    MAX(pv3_w) AS pv3_max_w,
    SUM(CASE WHEN hora_corrigida = 1 THEN 1 ELSE 0 END) AS hora_corrigida,
    SUM(CASE WHEN modo_inferido = 1 THEN 1 ELSE 0 END) AS modo_inferido
FROM kstar_leitura
GROUP BY DATE(ts_local);

DROP VIEW IF EXISTS vw_kstar_15min;
CREATE VIEW vw_kstar_15min AS
SELECT
    strftime('%Y-%m-%d %H:', ts_local) ||
        printf('%02d:00', (CAST(strftime('%M', ts_local) AS INTEGER) / 15) * 15)
        AS timestamp_15min,
    COUNT(*) AS registros,
    SUM(energia_intervalo_kwh) AS energia_intervalo_kwh,
    AVG(potencia_w) AS potencia_media_w,
    MAX(potencia_w) AS potencia_max_w,
    MAX(pv1_w) AS pv1_max_w,
    MAX(pv2_w) AS pv2_max_w,
    MAX(pv3_w) AS pv3_max_w,
    AVG(temp_radiador_c) AS temp_radiador_media_c,
    SUM(CASE WHEN hora_corrigida = 1 THEN 1 ELSE 0 END) AS hora_corrigida,
    SUM(CASE WHEN modo_inferido = 1 THEN 1 ELSE 0 END) AS modo_inferido
FROM kstar_leitura
GROUP BY timestamp_15min;
