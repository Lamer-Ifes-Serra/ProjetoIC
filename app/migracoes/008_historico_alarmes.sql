-- 008_historico_alarmes.sql
-- Estrutura para persistir eventos operacionais e de qualidade.

CREATE TABLE historico_alarmes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_evento TEXT NOT NULL,
    origem TEXT NOT NULL CHECK (
        origem IN ('aquisicao', 'meteorologia', 'phb', 'kstar', 'qualidade')
    ),
    codigo TEXT NOT NULL,
    severidade TEXT NOT NULL CHECK (
        severidade IN ('informacao', 'aviso', 'erro', 'critico')
    ),
    titulo TEXT NOT NULL,
    descricao TEXT,
    referencia TEXT,
    criado_em TEXT NOT NULL
);

CREATE INDEX idx_historico_alarmes_evento
    ON historico_alarmes(timestamp_evento);

CREATE INDEX idx_historico_alarmes_origem
    ON historico_alarmes(origem);

CREATE INDEX idx_historico_alarmes_codigo
    ON historico_alarmes(codigo);
