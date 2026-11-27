# Fase 7.1 — Taxonomia e desenho funcional do histórico de alarmes

**Status:** desenho funcional. Nenhuma tabela, migração ou página foi criada nesta fase.

## 1. Definição de evento

Um alarme é um evento ocorrido em um instante ou intervalo identificável que registra falha, lacuna, inconsistência ou estado operacional anormal. Não se deve gravar estatísticas, médias ou descrições permanentes como alarmes. Um indicador agregado só gera evento quando uma regra explícita detecta uma condição anormal; o evento deve guardar o período e a evidência que dispararam a regra.

Alarmes derivados de dados devem ser reproduzíveis e idempotentes. A implementação futura deve evitar criar novamente o mesmo evento a cada reprocessamento, usando como referência a origem, o código, o instante/período afetado e a entidade ou arquivo relacionado.

## 2. Categorias e fontes

`origem` identifica o subsistema responsável pelo evento. O detalhe da fonte física ou do artefato fica em `referencia` e/ou `descricao`, sem adicionar um campo `fonte` nesta proposta mínima.

| Origem | Fonte(s) | Códigos previstos | Severidade inicial | Observação |
| --- | --- | --- | --- | --- |
| `aquisicao` | MAWS55, FTP e pipeline | `ftp_falha`, `arquivo_nao_baixado`, `layout_desconhecido`, `arquivo_corrompido`, `arquivo_vazio`, `processamento_falhou` | `erro` | Só registrar ausência de arquivo quando a janela de aquisição esperada tiver sido confirmada. |
| `meteorologia` | `meteorologia_15min`, catálogo e validação | `lacuna_dados`, `sensor_sem_leitura`, `variavel_ausente`, `percentual_valido_baixo` | `aviso` | Referenciar o intervalo ou a variável. Não preencher nem inferir leituras ausentes. O limite de percentual válido depende de regra operacional a definir. |
| `phb` | `phb_leitura` e relatórios PHB | `energia_diverge_da_potencia`, `inversores_ativos_3`, `inversores_ativos_2`, `sem_potencia`, `sem_energia` | `aviso` | Quantidade de inversores ativos reduzida é observação, não falha confirmada. A tolerância de divergência de energia deve ser definida antes da automação. |
| `kstar` | `kstar_leitura` e relatórios KSTAR | `hora_corrigida`, `modo_inferido`, `offline_provavel` | `informacao` para correções/inferências; `aviso` para offline provável | Correção de hora e inferência de modo são transformações bem-sucedidas, não falhas. Só declarar offline após regra de ausência temporal confirmada. |
| `qualidade` | consultas de validação do banco e pipeline | `timestamp_duplicado`, `registro_incompleto`, `campo_obrigatorio_nulo` | `aviso` ou `erro` | `erro` quando inviabiliza ingestão ou uso confiável; `aviso` quando o dado permanece utilizável com limitação documentada. |
| `modbus` | integração futura com inversores | `falha_comunicacao`, `alarme_inversor`, `equipamento_offline` | `erro` ou `critico`, conforme impacto | Fonte futura; não há implementação nesta fase. |

`critico` fica reservado para evento com impacto amplo ou risco de perda/corrupção do banco, por exemplo `banco_corrompido`. Não usar severidade crítica apenas por uma leitura ausente.

## 3. Severidades

A coluna `severidade` aceita somente estes quatro valores canônicos:

| Valor | Uso |
| --- | --- |
| `informacao` | Evento informativo ou transformação concluída sem falha, como `hora_corrigida` e `modo_inferido`. |
| `aviso` | Condição que merece acompanhamento, mas não comprova falha física ou interrupção do serviço. |
| `erro` | Falha confirmada de aquisição, processamento, comunicação ou qualidade que impede ou compromete a operação esperada. |
| `critico` | Falha grave com impacto sistêmico, perda/corrupção de dados ou necessidade de ação imediata. |

Os valores são armazenados sem acentos para manter um conjunto estável de códigos e facilitar filtros.

## 4. Campos lógicos da futura tabela

| Campo | Finalidade |
| --- | --- |
| `id` | Identificador único do evento. |
| `timestamp_evento` | Instante ou início do período em que o evento ocorreu, preservando a referência temporal da fonte. |
| `origem` | Subsistema da taxonomia: `aquisicao`, `meteorologia`, `phb`, `kstar`, `qualidade` ou `modbus`. |
| `codigo` | Código estável e legível por máquina, listado na seção de categorias. |
| `severidade` | Um dos quatro níveis canônicos. |
| `titulo` | Resumo curto para exibição no dashboard. |
| `descricao` | Contexto, evidência e consequência observada; sem afirmar causa não comprovada. |
| `referencia` | Identificador relacionado, como nome de arquivo, variável, equipamento ou timestamp do registro afetado. |
| `criado_em` | Instante em que o evento foi persistido, distinto de `timestamp_evento`. |

`origem` e `codigo` devem ser dados estruturados, não texto livre. `titulo` e `descricao` são para leitura humana. `referencia` pode ser nula quando o evento não tiver um item específico associado.

### Exemplo lógico

```text
origem: kstar
codigo: hora_corrigida
severidade: informacao
titulo: Hora corrigida automaticamente
descricao: Amostra proveniente do período com deslocamento de +3 h.
referencia: 2025-09-22 14:15:00
```

## 5. Regras de registro e limites conhecidos

- Uma lacuna deve ser representada pelo intervalo observado que a delimita; não criar um alarme por cada slot ausente.
- Alarmes meteorológicos, PHB e KSTAR devem apontar a janela ou registro de origem em `referencia`/`descricao`.
- Não inferir falha física a partir de `inversores_ativos_3`, divergência sem tolerância aprovada ou modo inferido.
- `offline_provavel` só pode ser produzido com limite de inatividade e fonte de monitoramento definidos. O último timestamp conhecido, isoladamente, não confirma que o equipamento está offline.
- A regra de deduplicação precisa ser respeitada em cargas repetidas e reprocessamentos.
- Formato e fuso horário de `timestamp_evento` devem preservar a convenção da fonte; `criado_em` deve usar uma convenção única definida na implementação da migração.

## 6. Sequenciamento das migrações

O plano que cita `006_historico_alarmes.sql` estava defasado: as migrações 006 e 007 já existiam. A tabela de alarmes foi criada na 008 e a deduplicação foi acrescentada na 009. O próximo número livre é 010; migrações anteriores não devem ser renomeadas nem alteradas.

## 7. Critério de encerramento da Fase 7.1

- Categorias e fontes iniciais documentadas.
- Códigos e severidades iniciais definidos.
- Modelo lógico dos campos documentado.
- Limites e regras ainda dependentes de decisão operacional explicitados.
- Nenhuma migração, tabela ou página do dashboard criada.

# Fase 7.2 — Schema lógico de `historico_alarmes`

**Status:** proposta de schema definida; migração e código de geração ainda não criados.

## 1. Tabela

```sql
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
```

`timestamp_evento` registra quando o evento ocorreu; `criado_em` registra quando foi persistido. Ambos são `TEXT NOT NULL`. Tanto `timestamp_evento` quanto `criado_em` usam `YYYY-MM-DD HH:MM:SS` em UTC para armazenamento. A interface converte para UTC−3 ao exibir. Os timestamps de origem devem ser convertidos para UTC antes de persistir em `timestamp_evento`; quando necessário, a referência original permanece em `referencia`. `descricao` e `referencia` podem ser nulos quando não houver detalhe adicional.

A restrição de `origem` cobre as fontes atuais definidas na Fase 7.1. `modbus` permanece fora da lista até existir integração; sua inclusão futura exigirá evolução explícita do schema. `codigo` permanece aberto a novos códigos dentro das origens aprovadas, evitando migração a cada alarme novo.

## 2. Índices

```sql
CREATE INDEX idx_historico_alarmes_evento
    ON historico_alarmes(timestamp_evento);

CREATE INDEX idx_historico_alarmes_origem
    ON historico_alarmes(origem);

CREATE INDEX idx_historico_alarmes_codigo
    ON historico_alarmes(codigo);
```

O primeiro índice atende a listagem dos eventos recentes e consultas por período; os demais atendem filtros por origem e código. A ordenação da consulta recente deve incluir desempate por `id DESC` quando timestamps coincidirem.

## 3. Campos fora do escopo

Não incluir `status` (`aberto`/`fechado`), `responsavel` nem `equipamento_id`. Não há fluxo de atendimento nem cadastro formal de ativos definido; a tabela é um histórico imutável de eventos, não um sistema de tickets.

## 4. Exemplos de classificação

| Evento | Origem | Código | Severidade |
| --- | --- | --- | --- |
| Falha de FTP | `aquisicao` | `ftp_falha` | `erro` |
| Lacuna meteorológica | `meteorologia` | `lacuna_dados` | `aviso` |
| Divergência de energia PHB | `phb` | `energia_diverge_da_potencia` | `aviso` |
| Hora corrigida KSTAR | `kstar` | `hora_corrigida` | `informacao` |

## 5. Consultas previstas para a Fase 7.4

- `ultimos_alarmes()` — eventos mais recentes, com desempate determinístico por `id`.
- `alarmes_por_origem()` — filtro pela origem.
- `alarmes_por_severidade()` — filtro pela severidade.
- `alarmes_periodo()` — intervalo inclusivo entre timestamps.

A tabela e os índices suportam essas consultas sem alteração estrutural prevista. A política de deduplicação dos eventos continua sendo responsabilidade da futura camada de geração/inserção; esta proposta não adiciona unicidade que possa apagar ocorrências legítimas repetidas.

## 6. Critério de encerramento da Fase 7.2

- Tabela e tipos definidos.
- Valores aceitos de origem e severidade restringidos por `CHECK`.
- Índices de timestamp, origem e código definidos.
- Campos de ticket e cadastro de ativo excluídos deliberadamente.
- Nenhuma migração nem código de geração criado.


# Fase 7.5 — Geração inicial de alarmes

A implementação está em `app/alarmes.py` e usa exclusivamente regras previamente documentadas:

- Uma ocorrência `lacuna_dados` por lacuna de `meteorologia_15min`; os timestamps locais da MAWS55 são convertidos para UTC no evento.
- Um `energia_diverge_da_potencia` por dia UTC que tenha essa marca de qualidade no PHB.
- Um único evento histórico `hora_corrigida` resumindo o intervalo observado de amostras KSTAR corrigidas, sem afirmar que não existem lacunas dentro dele.

A migração 009 cria o índice único parcial por `origem`, `codigo` e `referencia`; todos os geradores fornecem referência não nula e usam `INSERT OR IGNORE`. Os geradores não são chamados automaticamente pelo dashboard nem pelo pipeline.

A validação com o ZIP normalizado e timestamps meteorológicos reais foi feita em banco temporário: 104 eventos (101 meteorologia, 2 PHB, 1 KSTAR) na primeira execução e zero novos eventos na segunda. O banco operacional permaneceu intacto; ele ainda está na versão 7 e suas tabelas PHB/KSTAR estão vazias.
