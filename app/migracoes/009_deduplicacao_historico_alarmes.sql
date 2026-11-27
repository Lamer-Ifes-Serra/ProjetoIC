-- 009_deduplicacao_historico_alarmes.sql
-- Impede que o mesmo evento com referência seja persistido novamente.

CREATE UNIQUE INDEX ux_historico_alarmes_deduplicacao
    ON historico_alarmes(origem, codigo, referencia)
    WHERE referencia IS NOT NULL;
