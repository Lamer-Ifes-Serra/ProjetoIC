# Monitoramento Integrado de Energia do IFES Campus Serra

[English](README.md)

Projeto de pesquisa e software desenvolvido no IFES Campus Serra para integrar dados da usina fotovoltaica, da estação meteorológica MAWS55 e da microrrede inteligente do campus.

O projeto reúne componentes de aquisição, validação, armazenamento, integração, análise e visualização de dados, com ênfase em rastreabilidade e interoperabilidade entre os diferentes sistemas energéticos.

## Visão geral

O repositório integra atualmente dois domínios principais de dados:

- Dados operacionais da usina fotovoltaica exportados da plataforma de monitoramento;
- Dados meteorológicos adquiridos diretamente da estação MAWS55.

A integração da microrrede inteligente ainda está em investigação e desenvolvimento.

O sistema utiliza um banco de dados SQLite local como camada de integração entre os pipelines de aquisição, as rotinas analíticas e o dashboard Streamlit.

## Contexto da pesquisa

O projeto faz parte de uma atividade de Iniciação Científica no IFES Campus Serra, voltada à comunicação e à integração entre:

- A usina fotovoltaica do campus;
- A estação meteorológica MAWS55;
- A microrrede inteligente.

O objetivo de longo prazo é manter uma camada consistente de dados para monitoramento, estudos de interoperabilidade, análise de desempenho, diagnóstico e visualização integrada dos sistemas energéticos.

## Arquitetura do sistema

```text
Estação meteorológica MAWS55
        │
        │ FTP
        ▼
Pipeline de aquisição MAWS55 ─────────────┐
                                          │
Exportações da usina fotovoltaica         │
        │                                 │
        ▼                                 ▼
Pipeline de integração FV ─────────► Banco SQLite
                                          │
                                          ├── Consultas e análises
                                          ├── Performance Ratio
                                          ├── Qualidade dos dados
                                          └── Dashboard Streamlit

Microrrede inteligente
        │
        └── Integração em desenvolvimento
```

A principal separação arquitetural é:

- `pipeline/`: Aquisição, transformação e carga dos dados;
- `app/`: Acesso ao banco, consultas, análises e apresentação;
- `dados/`: Dados operacionais locais e referências;
- `testes/`: Validação automatizada;
- `relatorios/`: Documentação técnica e histórica.

## Fontes de dados

### Usina fotovoltaica

A usina fotovoltaica principal possui aproximadamente 140 kWp de potência instalada em módulos e 119 kW de potência nominal CA dos inversores.

O pipeline atualmente processa exportações da plataforma de monitoramento da usina e dos inversores, produzindo conjuntos de dados normalizados para o banco SQLite.

Limitações atuais:

- A cobertura dos dados elétricos disponíveis no banco ainda é significativamente menor que o histórico meteorológico;
- A comunicação direta automatizada com os equipamentos PHB continua em investigação;
- A integração Modbus/RS-485 depende da validação da topologia física, do mapa oficial de registradores e da realização de testes autorizados exclusivamente para leitura.

### Estação meteorológica MAWS55

A aquisição meteorológica está operacional.

O pipeline oferece suporte a:

- Aquisição direta via FTP;
- Leitura de pastas locais para testes offline;
- Layout histórico de 52 valores;
- Layout atual de 56 valores;
- Conversão de timestamps UTC para o horário local;
- Aplicação de regras de qualidade;
- Preservação dos arquivos brutos;
- Rastreamento de ingestão por SHA-256;
- Processamento idempotente;
- Aquisição automática a cada 15 minutos.

Os layouts de 52 e 56 valores foram validados com arquivos reais da estação.

A carga histórica inicial foi validada com 122.515 registros meteorológicos antes da ativação da aquisição automática contínua. O banco operacional continua sendo atualizado automaticamente.

Consulte [`relatorios/aquisicao_maws55.md`](relatorios/aquisicao_maws55.md) para obter detalhes operacionais.

### Microrrede inteligente

A integração da microrrede ainda não está concluída.

A investigação atual inclui:

- Equipamentos KSTAR e disponibilidade de dados;
- Interfaces locais de comunicação;
- Possibilidades de comunicação RS-485/Modbus;
- Acesso ao datalogger;
- Requisitos para integração ao banco de dados e ao dashboard.

Consulte [`relatorios/investigacao_comunicacao_atividade2.md`](relatorios/investigacao_comunicacao_atividade2.md).

## Banco de dados e migrações

O projeto utiliza SQLite.

O banco de dados operacional está localizado em:

```text
dados/leituras.db
```

Esse arquivo é armazenado localmente e ignorado pelo Git.

A estrutura do banco é criada e evoluída por meio de migrações versionadas em:

```text
app/migracoes/
```

Migrações já aplicadas não devem ser editadas. Alterações estruturais devem ser realizadas por meio de uma nova migração.

Principais estruturas:

- `leitura_15min`: Dados fotovoltaicos e dos inversores agregados em intervalos de 15 minutos;
- `meteorologia_15min`: 56 variáveis meteorológicas da MAWS55, acompanhadas de indicadores de qualidade;
- `vw_leitura_completa`: View utilizada em análises que combinam dados elétricos e meteorológicos;
- `ingestao_arquivos`: Registro de ingestão contendo identificação dos arquivos, hashes, status de processamento e informações de diagnóstico;
- `resumo_diario`: Indicadores diários;
- Tabelas de histórico anual da usina e dos inversores.

Medições ausentes são representadas como `NULL`, e não como zeros artificiais.

## Aquisição da MAWS55

A operação via FTP exige um arquivo de configuração.

Crie o arquivo:

```text
config.env
```

a partir de:

```text
config.exemplo.env
```

O arquivo `config.env` nunca deve ser versionado.

Simulação:

```powershell
python pipeline\aquisicao_maws55.py --simular --config "C:\caminho\para\ProjetoIC\config.env"
```

Aquisição real:

```powershell
python pipeline\aquisicao_maws55.py --config "C:\caminho\para\ProjetoIC\config.env"
```

Recuperação histórica ou de períodos com lacunas:

```powershell
python pipeline\aquisicao_maws55.py --periodo AAAAMMDD --config "C:\caminho\para\ProjetoIC\config.env"
```

A execução normal seleciona os oito arquivos mais recentes. Caso a aquisição fique indisponível por mais de aproximadamente duas horas, as datas UTC afetadas devem ser recuperadas explicitamente utilizando `--periodo`.

No ambiente Windows de desenvolvimento, a aquisição é executada automaticamente a cada 15 minutos por meio do Agendador de Tarefas e de um script auxiliar em lote.

O pipeline foi validado para:

- Execuções repetidas sem duplicação;
- Ingestão de novos arquivos;
- Reconexão após falhas temporárias de conexão;
- Recuperação de períodos sem execução;
- Carga histórica;
- Arquivos inválidos;
- Processamento independente por arquivo.

## Qualidade e rastreabilidade

Cada arquivo meteorológico processado é registrado em `ingestao_arquivos`.

São registrados:

- Nome do arquivo;
- Hash SHA-256;
- Status do processamento;
- Quantidade de linhas lidas e gravadas;
- Mensagens de diagnóstico.

Lacunas reais do histórico são mantidas como lacunas. O pipeline não inventa medições para preencher períodos ausentes.

As regras de qualidade são aplicadas somente às variáveis que possuem tratamentos explicitamente definidos. Variáveis sem regras validadas permanecem como dados brutos.

O catálogo atual está implementado em:

```text
app/catalogo_meteorologia.py
```

Consulte [`relatorios/dicionario_meteorologia.md`](relatorios/dicionario_meteorologia.md).

## Dashboard

O dashboard Streamlit pode ser iniciado com:

```powershell
streamlit run app/dashboard.py
```

O dashboard já foi executado com sucesso.

Atualmente, existem áreas para:

- Visão geral;
- Geração fotovoltaica;
- Comparação entre inversores;
- Histórico anual;
- Qualidade dos dados;
- Meteorologia versus geração;
- Alertas e diagnósticos.

O dashboard continua em evolução. A interface meteorológica será ampliada para utilizar todo o histórico de `meteorologia_15min`, independentemente da disponibilidade dos dados elétricos.

A integração da microrrede e a implementação de um histórico persistente de alarmes também fazem parte da evolução planejada.

## Instalação

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

## Configuração

Copie:

```text
config.exemplo.env
```

para:

```text
config.env
```

e configure localmente o acesso FTP.

Não armazene credenciais em:

- Código-fonte;
- Arquivos README;
- Relatórios;
- Commits;
- Capturas de tela;
- Logs.

## Uso

Pipeline de integração da usina:

```bash
python pipeline/integra_usina_meteorologia.py
```

Carga dos dados processados:

```bash
python pipeline/carrega_banco.py
```

Simulação da aquisição MAWS55:

```bash
python pipeline/aquisicao_maws55.py --simular --config "caminho\para\config.env"
```

Aquisição real da MAWS55:

```bash
python pipeline/aquisicao_maws55.py --config "caminho\para\config.env"
```

Inicialização do dashboard:

```bash
streamlit run app/dashboard.py
```

## Testes

O projeto utiliza o framework `unittest`, disponibilizado pela biblioteca padrão do Python.

Execute:

```bash
python -m unittest discover -s testes -p "test_*.py" -v
```

A suíte de testes abrange, entre outros aspectos:

- Migrações do banco de dados;
- Consistência do schema;
- Layouts MAWS55 de 52 e 56 valores;
- Tratamento dos dados meteorológicos;
- Comportamento das fontes FTP;
- Configuração;
- Idempotência da ingestão;
- Arquivos inválidos;
- Integração com o banco de dados.

Alguns testes de comparação com arquivos XLSX de referência são ignorados quando esses arquivos locais não estão disponíveis.

## Estrutura do repositório

```text
ProjetoIC/
├── app/
│   ├── banco.py
│   ├── consultas.py
│   ├── catalogo_meteorologia.py
│   ├── dashboard.py
│   ├── performance_ratio.py
│   └── migracoes/
├── pipeline/
│   ├── aquisicao/
│   ├── aquisicao_maws55.py
│   ├── carrega_banco.py
│   ├── integra_usina_meteorologia.py
│   └── legado/
├── dados/
│   ├── referencia_meteorologia/
│   ├── brutos/
│   └── processados/
├── testes/
├── relatorios/
├── config.exemplo.env
├── requirements.txt
├── README.md
└── README.pt-BR.md
```

O banco de dados operacional, as credenciais, as aquisições brutas da MAWS55, os backups e os logs não fazem parte do versionamento normal.

## Limitações atuais

- A cobertura histórica dos dados elétricos ainda é limitada em relação ao histórico meteorológico;
- A comunicação direta com os equipamentos PHB continua em investigação;
- Os equipamentos KSTAR e a microrrede ainda não estão integrados ao banco de dados central;
- Algumas unidades e definições semânticas dos sensores meteorológicos ainda dependem de confirmação documental;
- Algumas variáveis meteorológicas permanecem como dados brutos por não possuírem regras de qualidade validadas;
- Os cálculos de Performance Ratio já estão implementados, mas a metodologia ainda necessita de validação científica adicional, especialmente quanto à seleção da irradiância e à utilização de GHI versus irradiância no plano dos módulos;
- O dashboard está operacional, mas continua em revisão técnica e analítica.

## Segurança

- `config.env` é ignorado pelo Git;
- `dados/leituras.db` é ignorado pelo Git;
- Os logs de aquisição da MAWS55 são ignorados pelo Git;
- Credenciais não devem ser armazenadas no código-fonte ou na documentação;
- O acesso aos equipamentos de produção deve respeitar as autorizações e o princípio do menor privilégio;
- Experimentos de comunicação direta com inversores devem permanecer exclusivamente em modo de leitura até que a topologia de comunicação e as informações do protocolo oficial sejam validadas.

## Roteiro da pesquisa

As prioridades atuais de desenvolvimento incluem:

1. Manter a aquisição contínua de dados da MAWS55;
2. Fortalecer a aquisição e a comunicação dos dados fotovoltaicos;
3. Validar as possibilidades de comunicação com os equipamentos PHB;
4. Mapear e integrar a microrrede inteligente;
5. Ampliar as análises integradas entre meteorologia e geração;
6. Implementar um histórico persistente de alarmes;
7. Aprimorar a visualização da qualidade dos dados;
8. Validar as metodologias de Performance Ratio e de estimativa da geração esperada;
9. Testar a interoperabilidade entre todas as fontes de dados;
10. Preparar a implantação e, posteriormente, estabelecer um domínio público estável.