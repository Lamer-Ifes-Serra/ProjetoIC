# IFES Campus Serra Integrated Energy Monitoring

[Português](README.pt-BR.md)

Research and software project developed at IFES Campus Serra to integrate data from the photovoltaic plant, the MAWS55 weather station, and the campus smart microgrid.

The project provides data acquisition, validation, storage, integration, analysis, and visualization components, with an emphasis on traceability and interoperability between different energy systems.

## Overview

The repository currently integrates two main data domains:

- Photovoltaic plant operational data exported from the monitoring platform;
- Meteorological data acquired directly from the MAWS55 weather station.

Smart microgrid integration is still under investigation and development.

The system uses a local SQLite database as the integration layer between acquisition pipelines, analytical routines, and the Streamlit dashboard.

## Research Context

The project is part of a scientific initiation activity at IFES Campus Serra focused on communication and integration between:

- The campus photovoltaic plant;
- The MAWS55 weather station;
- The smart microgrid.

The long-term objective is to create a consistent data layer for monitoring, interoperability studies, performance analysis, diagnostics, and integrated energy system visualization.

## System Architecture

```text
MAWS55 weather station
        │
        │ FTP
        ▼
MAWS55 acquisition pipeline ──────────────┐
                                          │
Photovoltaic monitoring exports           │
        │                                 │
        ▼                                 ▼
PV integration pipeline ───────────► SQLite database
                                          │
                                          ├── Queries and analytics
                                          ├── Performance Ratio
                                          ├── Data quality checks
                                          └── Streamlit dashboard

Smart microgrid
        │
        └── Integration under development
```

The main architectural separation is:

- `pipeline/`: Acquisition, transformation, and data-loading routines;
- `app/`: Database access, queries, analyses, and presentation;
- `dados/`: Local operational and reference data;
- `testes/`: Automated validation;
- `relatorios/`: Technical and historical project documentation.

## Data Sources

### Photovoltaic Plant

The main photovoltaic plant has approximately 140 kWp of installed module capacity and 119 kW of nominal AC inverter capacity.

The current pipeline processes monitoring platform exports containing plant and inverter measurements and produces normalized datasets for the SQLite database.

Current limitations:

- The electrical data currently available in the database cover a much shorter period than the meteorological history;
- Direct automated communication with the PHB equipment is still under investigation;
- Modbus/RS-485 integration requires validation of the physical topology, official register map, and authorized read-only tests.

### MAWS55 Weather Station

Meteorological data acquisition is operational.

The pipeline supports:

- Direct FTP acquisition;
- Local-folder acquisition for offline testing;
- The historical 52-value layout;
- The current 56-value layout;
- UTC-to-local timestamp conversion;
- Data quality rules;
- Raw file preservation;
- SHA-256-based ingestion tracking;
- Idempotent processing;
- Automatic acquisition every 15 minutes.

Both the 52-value and 56-value layouts have been validated using real station files.

The historical load was validated with 122,515 meteorological records before continuous automatic acquisition was enabled. The operational database continues to grow automatically.

See [`relatorios/aquisicao_maws55.md`](relatorios/aquisicao_maws55.md) for operational details.

### Smart Microgrid

Smart microgrid integration is not yet complete.

Current investigations include:

- KSTAR equipment and data availability;
- Local communication interfaces;
- RS-485/Modbus possibilities;
- Data logger access;
- Integration requirements for the database and dashboard.

See [`relatorios/investigacao_comunicacao_atividade2.md`](relatorios/investigacao_comunicacao_atividade2.md).

## Database and Migrations

The project uses SQLite.

The operational database is:

```text
dados/leituras.db
```

This file is stored locally and ignored by Git. The database structure is created and evolved through versioned migrations under:

```text
app/migracoes/
```

Already-applied migrations must not be edited. Structural changes must be introduced through new migrations.

Important structures include:

- `leitura_15min`: Photovoltaic and inverter data aggregated into 15-minute intervals;
- `meteorologia_15min`: 56 MAWS55 meteorological variables, together with quality flags;
- `vw_leitura_completa`: Integrated view used by analyses combining electrical and meteorological data;
- `ingestao_arquivos`: Ingestion journal containing file identification, hashes, processing status, and diagnostic information;
- `resumo_diario`: Daily indicators;
- Annual plant and inverter history tables.

Missing measurements are represented as `NULL`, not as artificial zeros.

## MAWS55 Data Acquisition

A configuration file is required for FTP operation.

Create it by copying:

```text
config.exemplo.env
```

to:

```text
config.env
```

The `config.env` file must never be committed to Git.

Example:

```powershell
python pipeline\aquisicao_maws55.py --simular --config "C:\path\to\ProjetoIC\config.env"
```

Real acquisition:

```powershell
python pipeline\aquisicao_maws55.py --config "C:\path\to\ProjetoIC\config.env"
```

Historical or recovery acquisition:

```powershell
python pipeline\aquisicao_maws55.py --periodo AAAAMMDD --config "C:\path\to\ProjetoIC\config.env"
```

Normal execution selects the eight most recent files. If acquisition is interrupted for more than approximately two hours, the affected UTC dates should be recovered explicitly using `--periodo`.

The Windows development environment currently runs the acquisition process every 15 minutes through Task Scheduler and a batch wrapper.

The acquisition pipeline has been validated for:

- Repeated executions without duplication;
- New file ingestion;
- Reconnection after temporary connection failures;
- Interrupted acquisition periods;
- Historical backfilling;
- Malformed files;
- Independent file processing.

## Data Quality and Traceability

Meteorological ingestion records each processed file in `ingestao_arquivos`.

The ingestion process tracks:

- File name;
- SHA-256 hash;
- Processing status;
- Number of rows read and stored;
- Diagnostic messages.

Known gaps in the station history are preserved as gaps. The pipeline does not fabricate measurements to fill missing periods.

Quality rules are applied only when explicitly defined. Variables without validated treatment rules remain as raw measurements rather than being silently modified.

The current catalog is implemented in:

```text
app/catalogo_meteorologia.py
```

See [`relatorios/dicionario_meteorologia.md`](relatorios/dicionario_meteorologia.md).

## Dashboard

The repository contains a Streamlit dashboard:

```powershell
streamlit run app/dashboard.py
```

The dashboard has been executed successfully.

Current functionality includes views for:

- General monitoring;
- Photovoltaic generation;
- Inverter comparison;
- Annual history;
- Data quality;
- Meteorology versus generation;
- Alerts and diagnostics.

The dashboard is still evolving. In particular, the meteorological interface will be expanded to use the complete historical `meteorologia_15min` dataset independently of electrical data availability.

Future dashboard development will also include smart microgrid integration and a persistent alarm history model.

## Installation

Recommended environment:

- Python 3;
- Dependencies listed in `requirements.txt`;
- SQLite;
- Streamlit for the dashboard.

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Configuration

Copy:

```text
config.exemplo.env
```

to:

```text
config.env
```

and provide the required local FTP configuration.

Do not store credentials in:

- Source files;
- README files;
- Reports;
- Commits;
- Screenshots;
- Logs.

## Usage

Run the plant integration pipeline:

```bash
python pipeline/integra_usina_meteorologia.py
```

Load processed plant data:

```bash
python pipeline/carrega_banco.py
```

Simulate MAWS55 acquisition:

```bash
python pipeline/aquisicao_maws55.py --simular --config "path\to\config.env"
```

Run real MAWS55 acquisition:

```bash
python pipeline/aquisicao_maws55.py --config "path\to\config.env"
```

Start the dashboard:

```bash
streamlit run app/dashboard.py
```

## Tests

The project uses Python's built-in `unittest` framework.

Run:

```bash
python -m unittest discover -s testes -p "test_*.py" -v
```

The tests cover:

- Database migrations;
- Schema consistency;
- MAWS55 52-value and 56-value layouts;
- Meteorological data treatment;
- FTP source behavior;
- Configuration;
- Ingestion idempotency;
- Malformed input;
- Database integration.

Some reference data comparison tests are skipped when the large local XLSX reference files are unavailable.

## Repository Structure

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
└── README.md
```

Operational databases, FTP credentials, MAWS55 raw acquisitions, backups, and acquisition logs are intentionally kept outside Git tracking.

## Current Limitations

- Photovoltaic historical coverage in the integrated database is still limited compared with the MAWS55 meteorological history;
- Direct PHB communication is still under investigation;
- KSTAR and smart microgrid data acquisition are not yet integrated into the central database;
- Some meteorological units and sensor semantics still require documentary confirmation;
- Several meteorological variables are stored as raw values because validated quality rules are not yet available;
- Performance Ratio calculations are implemented, but their methodology still requires further scientific validation, particularly regarding irradiance selection and GHI versus plane-of-array irradiance;
- The dashboard is operational but remains under active technical and analytical revision.

## Security

- `config.env` is ignored by Git;
- Operational SQLite databases are ignored by Git;
- MAWS55 acquisition logs are ignored by Git;
- Credentials must not be stored in source code or documentation;
- Access to production equipment must follow authorization and least-privilege principles;
- Direct inverter communication experiments must remain read-only until the communication topology and official protocol information have been validated.

## Research Roadmap

Current development priorities include:

1. Maintaining continuous MAWS55 data acquisition;
2. Strengthening photovoltaic data acquisition and communication;
3. Validating PHB communication options;
4. Mapping and integrating the smart microgrid;
5. Expanding integrated meteorological and electrical analyses;
6. Implementing persistent alarm history;
7. Improving data quality visualization;
8. Validating Performance Ratio and expected generation methodologies;
9. Testing interoperability between all data sources;
10. Preparing for deployment and, eventually, establishing a stable public domain.