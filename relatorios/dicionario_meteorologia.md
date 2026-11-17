# Dicionário das variáveis meteorológicas — MAWS55

Este documento descreve as variáveis meteorológicas armazenadas pelo ProjetoIC.

A tabela das 56 variáveis é gerada a partir de `app/catalogo_meteorologia.py`, que é a referência de nomenclatura, unidade, tratamento e flags.

Se o catálogo, este documento e o banco divergirem, o catálogo e o schema versionado do banco devem ser verificados primeiro. A suíte de testes valida a consistência entre essas estruturas.

## Estrutura meteorológica no banco

- **`meteorologia_15min`**: armazena `timestamp_15min`, `timestamp_original`, `lacuna_temporal`, as 56 variáveis meteorológicas e suas flags de qualidade.
- **`leitura_15min`**: mantém os dados elétricos e algumas colunas meteorológicas históricas por compatibilidade; a fonte principal da meteorologia é `meteorologia_15min`.
- **`vw_leitura_completa`**: integra os dados elétricos e meteorológicos para consultas e análises.
- **`ingestao_arquivos`**: registra os arquivos meteorológicos processados, seus hashes, status e mensagens de diagnóstico.
- Valores ausentes são representados como **`NULL`**, e não como zero.
- **Flag 1** indica que o valor foi invalidado pela respectiva regra de qualidade.
- Flag vazia indica que a variável não foi avaliada por uma regra de qualidade.
- Variáveis sem tratamento validado permanecem armazenadas como dados brutos.
- Unidades marcadas como inferidas ainda dependem de confirmação documental.

## Fonte dos dados

O banco operacional recebe os dados diretamente dos arquivos da estação MAWS55.

São suportados dois layouts reais:

- **52 valores**: layout histórico, sem o grupo LPNET14 NTC;
- **56 valores**: layout completo posterior.

Os dois layouts foram validados com arquivos reais da estação.

A aquisição contínua é realizada pelo pipeline `pipeline/aquisicao_maws55.py`. Para detalhes sobre formatos, tratamento, idempotência e automação, consulte `relatorios/aquisicao_maws55.md`.

## Tabela das 56 variáveis

| Coluna no banco | Onde fica | Unidade (inferida) | Descrição | Tratada na referência | Flag |
|---|---|---|---|---|---|
| `ghi_lppyra02_w_m2` | `meteorologia_15min` | W/m² | Radiação global, sensor LPPYRA02 (instantâneo) | sim | `flag_ghi_lppyra02_w_m2` |
| `ghi_lpnet14_w_m2` | `meteorologia_15min` | W/m² | Radiação global, sensor LPNET14 (instantâneo) | sim | `flag_ghi_lpnet14_w_m2` |
| `temperatura_c` | `meteorologia_15min` | °C | Temperatura do ar (instantâneo) | sim | `flag_temperatura_c` |
| `vento_m_s` | `meteorologia_15min` | m/s | Velocidade do vento (média) | sim | `flag_vento_m_s` |
| `precipitacao` | `meteorologia_15min` | mm | Precipitação no intervalo | sim | `flag_precipitacao` |
| `umidade_relativa_inst_pct` | `meteorologia_15min` | % | Umidade relativa do ar (instantâneo) | sim | `flag_umidade_relativa_inst_pct` |
| `umidade_relativa_med_pct` | `meteorologia_15min` | % | Umidade relativa do ar (média) | sim | `flag_umidade_relativa_med_pct` |
| `umidade_relativa_max_pct` | `meteorologia_15min` | % | Umidade relativa do ar (máximo) | sim | `flag_umidade_relativa_max_pct` |
| `umidade_relativa_min_pct` | `meteorologia_15min` | % | Umidade relativa do ar (mínimo) | sim | `flag_umidade_relativa_min_pct` |
| `vento_dir_med_graus` | `meteorologia_15min` | graus | Direção do vento (média) | sim | `flag_vento_dir_med_graus` |
| `vento_dir_max_graus` | `meteorologia_15min` | graus | Direção do vento (máximo) | sim | `flag_vento_dir_max_graus` |
| `vento_dir_min_graus` | `meteorologia_15min` | graus | Direção do vento (mínimo) | sim | `flag_vento_dir_min_graus` |
| `vento_vel_max_m_s` | `meteorologia_15min` | m/s | Velocidade do vento (máximo) | sim | `flag_vento_vel_max_m_s` |
| `vento_vel_min_m_s` | `meteorologia_15min` | m/s | Velocidade do vento (mínimo) | sim | `flag_vento_vel_min_m_s` |
| `ghi_lppyra02_med_w_m2` | `meteorologia_15min` | W/m² | Radiação global, sensor LPPYRA02 (média) | sim | `flag_ghi_lppyra02_med_w_m2` |
| `ghi_lppyra02_max_w_m2` | `meteorologia_15min` | W/m² | Radiação global, sensor LPPYRA02 (máximo) | sim | `flag_ghi_lppyra02_max_w_m2` |
| `ghi_lppyra02_min_w_m2` | `meteorologia_15min` | W/m² | Radiação global, sensor LPPYRA02 (mínimo) | sim | `flag_ghi_lppyra02_min_w_m2` |
| `ghi_lpnet14_med_w_m2` | `meteorologia_15min` | W/m² | Radiação global, sensor LPNET14 (média) | sim | `flag_ghi_lpnet14_med_w_m2` |
| `ghi_lpnet14_max_w_m2` | `meteorologia_15min` | W/m² | Radiação global, sensor LPNET14 (máximo) | sim | `flag_ghi_lpnet14_max_w_m2` |
| `ghi_lpnet14_min_w_m2` | `meteorologia_15min` | W/m² | Radiação global, sensor LPNET14 (mínimo) | sim | `flag_ghi_lpnet14_min_w_m2` |
| `umid_solo_inst` | `meteorologia_15min` | a confirmar | Umidade do solo (instantâneo) | sim | `flag_umid_solo_inst` |
| `umid_solo_med` | `meteorologia_15min` | a confirmar | Umidade do solo (média) | sim | `flag_umid_solo_med` |
| `umid_solo_max` | `meteorologia_15min` | a confirmar | Umidade do solo (máximo) | sim | `flag_umid_solo_max` |
| `umid_solo_min` | `meteorologia_15min` | a confirmar | Umidade do solo (mínimo) | sim | `flag_umid_solo_min` |
| `pressao_inst_hpa` | `meteorologia_15min` | hPa | Pressão atmosférica (instantâneo) | não (dado bruto) | — |
| `pressao_med_hpa` | `meteorologia_15min` | hPa | Pressão atmosférica (média) | não (dado bruto) | — |
| `pressao_max_hpa` | `meteorologia_15min` | hPa | Pressão atmosférica (máximo) | não (dado bruto) | — |
| `pressao_min_hpa` | `meteorologia_15min` | hPa | Pressão atmosférica (mínimo) | não (dado bruto) | — |
| `temp_int_c` | `meteorologia_15min` | °C | Temp int (definição a confirmar) | não (dado bruto) | — |
| `temperatura_med_c` | `meteorologia_15min` | °C | Temperatura do ar (média) | não (dado bruto) | — |
| `temperatura_max_c` | `meteorologia_15min` | °C | Temperatura do ar (máximo) | não (dado bruto) | — |
| `temperatura_min_c` | `meteorologia_15min` | °C | Temperatura do ar (mínimo) | não (dado bruto) | — |
| `rad_refletida_inst_w_m2` | `meteorologia_15min` | W/m² | Radiação solar refletida (instantâneo) | não (dado bruto) | — |
| `rad_refletida_med_w_m2` | `meteorologia_15min` | W/m² | Radiação solar refletida (média) | não (dado bruto) | — |
| `rad_refletida_max_w_m2` | `meteorologia_15min` | W/m² | Radiação solar refletida (máximo) | não (dado bruto) | — |
| `rad_refletida_min_w_m2` | `meteorologia_15min` | W/m² | Radiação solar refletida (mínimo) | não (dado bruto) | — |
| `rad_iv_inst_w_m2` | `meteorologia_15min` | W/m² | Radiação infravermelha (IV) (instantâneo) | não (dado bruto) | — |
| `rad_iv_med_w_m2` | `meteorologia_15min` | W/m² | Radiação infravermelha (IV) (média) | não (dado bruto) | — |
| `rad_iv_max_w_m2` | `meteorologia_15min` | W/m² | Radiação infravermelha (IV) (máximo) | não (dado bruto) | — |
| `rad_iv_min_w_m2` | `meteorologia_15min` | W/m² | Radiação infravermelha (IV) (mínimo) | não (dado bruto) | — |
| `rad_spf_inst_w_m2` | `meteorologia_15min` | W/m² | Radiação SPF (significado a confirmar) (instantâneo) | não (dado bruto) | — |
| `rad_spf_med_w_m2` | `meteorologia_15min` | W/m² | Radiação SPF (significado a confirmar) (média) | não (dado bruto) | — |
| `rad_spf_max_w_m2` | `meteorologia_15min` | W/m² | Radiação SPF (significado a confirmar) (máximo) | não (dado bruto) | — |
| `rad_spf_min_w_m2` | `meteorologia_15min` | W/m² | Radiação SPF (significado a confirmar) (mínimo) | não (dado bruto) | — |
| `rad_liquida_inst_w_m2` | `meteorologia_15min` | W/m² | Radiação solar líquida (instantâneo) | não (dado bruto) | — |
| `rad_liquida_med_w_m2` | `meteorologia_15min` | W/m² | Radiação solar líquida (média) | não (dado bruto) | — |
| `rad_liquida_max_w_m2` | `meteorologia_15min` | W/m² | Radiação solar líquida (máximo) | não (dado bruto) | — |
| `rad_liquida_min_w_m2` | `meteorologia_15min` | W/m² | Radiação solar líquida (mínimo) | não (dado bruto) | — |
| `temp_ntc_lpnet14_inst_c` | `meteorologia_15min` | °C | Temperatura do sensor LPNET14 (NTC) (instantâneo) | não (dado bruto) | — |
| `temp_ntc_lpnet14_med_c` | `meteorologia_15min` | °C | Temperatura do sensor LPNET14 (NTC) (média) | não (dado bruto) | — |
| `temp_ntc_lpnet14_max_c` | `meteorologia_15min` | °C | Temperatura do sensor LPNET14 (NTC) (máximo) | não (dado bruto) | — |
| `temp_ntc_lpnet14_min_c` | `meteorologia_15min` | °C | Temperatura do sensor LPNET14 (NTC) (mínimo) | não (dado bruto) | — |
| `temp_solo_inst` | `meteorologia_15min` | a confirmar | Temperatura do solo (instantâneo) | não (dado bruto) | — |
| `temp_solo_med` | `meteorologia_15min` | a confirmar | Temperatura do solo (média) | não (dado bruto) | — |
| `temp_solo_max` | `meteorologia_15min` | a confirmar | Temperatura do solo (máximo) | não (dado bruto) | — |
| `temp_solo_min` | `meteorologia_15min` | a confirmar | Temperatura do solo (mínimo) | não (dado bruto) | — |



**

## Observações da referência meteorológica histórica

As observações abaixo foram levantadas durante a análise do arquivo meteorológico tratado de referência utilizado nas etapas iniciais do projeto.

Esse arquivo possuía 111.555 registros e cobertura até 31/07/2026. Esses valores descrevem especificamente a referência histórica analisada e não representam a cobertura atual do banco operacional.

Posteriormente, o histórico foi carregado diretamente a partir dos arquivos da estação e a aquisição da MAWS55 passou a ser executada automaticamente. Por isso, o banco operacional possui dados posteriores ao limite do arquivo tratado de referência.

| Variável | O que aparece | Pergunta |
|---|---|---|
| `temperatura_med_c`, `_max_c`, `_min_c` | Mínimo de ****-40,0 °C**** (em `inst` o tratamento já invalidou 6 valores) | Valor travado do sensor? Vai ser tratado? |
| `temp_ntc_lpnet14_*_c` | Máximo de ****360**** em `inst`, `med` e `max` | ****Explicado (24/10/2026):**** vem das 3.653 linhas de 15/07 a 22/08/2022, em que o xlsx tem nomes de colunas deslocados e esse campo traz a direção do vento. Não é erro do sensor. Ver `aquisicao_maws55.md`, seção 4.2 |
| `umid_solo_*` | Valores de ****-0,4 a 1,0**** | Qual a unidade (fração? índice?) e o que significa negativo? |
| `temp_solo_*` | Mínimo de 0,43 e máximo de 35 | Unidade e faixa válida? |
| `rad_iv_*`, `rad_spf_*` | Valores ****negativos**** (IV até -145; SPF de -86 a 88) | Negativo é esperado nesses sensores? O que é "SPF"? |
| `vento_vel_max_m_s` | Máximo de 37,7 | Unidade é m/s mesmo? (a média geral é 3,6) |
| `temp_int_c` | Entre 14,1 e 38,1 | É a temperatura interna de quê? |
| `timestamp_original` | Segundos 07 ou 08 (ex.: 16:00:07) | O registro marca o ****começo ou o fim**** do intervalo de 15 min? |
| `lacuna_temporal` | 51 lacunas no arquivo; ~30.257 registros ausentes estimados. Nos dados que chegam pela aquisição direta (FTP), esta coluna fica ****vazia (desconhecida)**** | Quais ficam vazios e quais são interpolados? |
| Cobertura do arquivo de referência | Termina em 31/07/2026 | Limitação específica da referência histórica; o banco operacional recebe dados posteriores diretamente da estação |
| `umid_solo_*` (regra de tratamento) | A regra do tratamento marca valor ****igual a -400****, mas a coluna só tem valores de -0,4 a 1,0 (a regra nunca dispara) | O código de erro é -0,4 (valor já dividido por 1000)? |
