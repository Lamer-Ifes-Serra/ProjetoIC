-- 006_views_relatorios_inversores.sql
-- Agregacoes reutilizaveis dos historicos PHB e KSTAR.

CREATE VIEW vw_phb_resumo_diario AS
SELECT
    DATE(ts_local) AS data,
    COUNT(*) AS registros,
    SUM(energia_intervalo_kwh) AS energia_kwh,
    MAX(potencia_w) AS potencia_max_w,
    AVG(potencia_w) AS potencia_media_w,
    AVG(temperatura_c) AS temperatura_media_c,
    AVG(inversores_ativos) AS inversores_ativos_medio
FROM phb_leitura
GROUP BY DATE(ts_local);

CREATE VIEW vw_kstar_resumo_diario AS
SELECT
    DATE(ts_local) AS data,
    COUNT(*) AS registros,
    SUM(energia_intervalo_kwh) AS energia_intervalo_kwh,
    MAX(potencia_w) AS potencia_max_w,
    MAX(pv1_w) AS pv1_max_w,
    MAX(pv2_w) AS pv2_max_w,
    MAX(pv3_w) AS pv3_max_w,
    SUM(CASE WHEN hora_corrigida = 1 THEN 1 ELSE 0 END) AS hora_corrigida
FROM kstar_leitura
GROUP BY DATE(ts_local);

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
    SUM(CASE WHEN hora_corrigida = 1 THEN 1 ELSE 0 END) AS hora_corrigida
FROM kstar_leitura
GROUP BY timestamp_15min;
