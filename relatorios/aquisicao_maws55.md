# Aquisição dos Dados da MAWS55 até o Banco de Dados

Documento operacional sobre a aquisição direta dos arquivos da estação meteorológica MAWS55 e sua integração ao banco de dados SQLite do ProjetoIC.

## 1. Visão geral

O pipeline permite adquirir dados meteorológicos diretamente do servidor FTP da estação ou de uma pasta local.

```text
FTP da MAWS55 ──┐
                ├──> leitura --> tratamento --> meteorologia_15min
Pasta local ────┘                         └──> ingestao_arquivos
```

O pipeline:

- Seleciona arquivos `*_15m_AAAAMMDD_HHMM.txt`;
- Identifica automaticamente os layouts suportados;
- Converte o horário UTC dos arquivos para o horário local utilizado no banco;
- Aplica regras de qualidade meteorológica;
- Grava os dados em `meteorologia_15min`;
- Registra cada arquivo em `ingestao_arquivos`;
- Preserva cópias brutas, quando aplicável;
- Evita duplicações utilizando o histórico de ingestão e o hash do conteúdo.

## 2. Fontes suportadas

A aquisição possui duas fontes com a mesma interface:

- Servidor FTP da MAWS55;
- Pasta local contendo arquivos `.txt`.

### FTP

```powershell
python pipeline\aquisicao_maws55.py --config "C:\caminho\para\ProjetoIC\config.env"
```

### Pasta local

```powershell
python pipeline\aquisicao_maws55.py --fonte pasta --pasta "C:\dados\maws55"
```

A fonte local é útil para testes e processamento de arquivos previamente baixados.

## 3. Configuração

Copie:

```text
config.exemplo.env
```

para:

```text
config.env
```

O arquivo `config.env` real não deve ser versionado.

As principais configurações FTP são:

```text
FTP_HOST
FTP_USER
FTP_PASS
FTP_DIR
```

A porta e o TLS também podem ser configurados, quando suportados pelo servidor.

No ambiente Windows utilizado durante a validação do projeto, o caminho do `config.env` é informado explicitamente:

```powershell
python pipeline\aquisicao_maws55.py --config "C:\caminho\para\ProjetoIC\config.env"
```

A descoberta automática do `config.env` apresentou comportamento inconsistente nesse ambiente e permanece como uma dívida técnica. O uso explícito de `--config` é o procedimento operacional validado.

## 4. Uso

### Simulação

```powershell
python pipeline\aquisicao_maws55.py --simular --config "C:\caminho\para\ProjetoIC\config.env"
```

A simulação lê e trata os arquivos sem realizar a ingestão meteorológica normal.

### Arquivos recentes

```powershell
python pipeline\aquisicao_maws55.py --config "C:\caminho\para\ProjetoIC\config.env"
```

Sem o argumento `--periodo`, o programa seleciona os oito arquivos mais recentes.

### Período específico

Dia:

```powershell
python pipeline\aquisicao_maws55.py --periodo AAAAMMDD --config "C:\caminho\para\ProjetoIC\config.env"
```

Mês:

```powershell
python pipeline\aquisicao_maws55.py --periodo AAAAMM --confirmar --config "C:\caminho\para\ProjetoIC\config.env"
```

O argumento `--confirmar` protege contra cargas grandes iniciadas acidentalmente.

Os códigos de saída utilizados pelo pipeline permitem diferenciar execução normal, falhas de processamento ou conexão e erros de configuração ou utilização.

## 5. Formato dos arquivos

Os arquivos reais da MAWS55 não possuem cabeçalho.

Formato geral:

```text
local, frequência, data, hora UTC, valores...
```

Cada arquivo representa uma leitura.

O leitor identifica o layout pela quantidade de valores, e não apenas pela data.

### 5.1 Layout histórico de 52 valores

Os primeiros arquivos do histórico possuem 52 valores meteorológicos.

Esse formato não contém o grupo de quatro medições do sensor LPNET14 NTC.

O layout de 52 valores foi validado com arquivos reais da estação durante a carga histórica.

### 5.2 Layout de 56 valores

O layout posterior contém 56 valores meteorológicos, incluindo o grupo LPNET14 NTC.

O layout de 56 valores também foi validado com arquivos reais recentes, obtidos diretamente do FTP.

Arquivos com quantidades diferentes de 52 ou 56 valores são considerados incompatíveis com os layouts conhecidos e não devem ser interpretados silenciosamente.

## 6. Horário

Os arquivos utilizam UTC.

O pipeline converte o horário para o horário local utilizado na integração.

O banco mantém:

- `timestamp_original`: Horário original da leitura;
- `timestamp_15min`: Timestamp utilizado na integração em intervalos de 15 minutos.

O filtro `--periodo` considera o período UTC representado no nome dos arquivos.

Essa diferença deve ser considerada ao comparar contagens mensais com timestamps locais, principalmente nos limites entre dias e meses.

## 7. Tratamento e qualidade

As regras de qualidade são implementadas em:

```text
pipeline/aquisicao/tratamento.py
```

O catálogo das variáveis está em:

```text
app/catalogo_meteorologia.py
```

Quando existe uma regra validada para determinada variável:

- O valor tratado pode ser invalidado quando viola a regra;
- A flag correspondente registra essa invalidação.

Variáveis sem regras validadas permanecem como dados brutos e não recebem flags artificialmente.

Valores zero legítimos são preservados como zero. A ausência de valores é representada como `NULL`.

## 8. Idempotência e diário de ingestão

Cada arquivo processado é registrado em:

```text
ingestao_arquivos
```

O diário armazena informações como:

- Nome do arquivo;
- Hash do conteúdo;
- Status do processamento;
- Quantidade de linhas;
- Mensagem de diagnóstico.

Um arquivo com o mesmo nome e o mesmo conteúdo de outro previamente processado é ignorado.

Quando um arquivo com o mesmo nome apresenta conteúdo diferente, o hash permite identificar a alteração, e o pipeline pode processá-lo novamente.

Isso permite repetir cargas sem duplicar arquivos já concluídos.

## 9. Carga histórica

A carga histórica foi realizada mês a mês, a partir de 15/07/2022.

Foram validados durante esse processo:

- Layout de 52 valores;
- Layout de 56 valores;
- Transição entre os layouts;
- Retomada após interrupções;
- Idempotência;
- Lacunas reais da estação;
- Coerência entre `meteorologia_15min` e `ingestao_arquivos`.

Antes da ativação da aquisição contínua, a carga histórica foi validada com:

```text
122.515 registros meteorológicos
122.515 arquivos com status ok
0 erros persistentes no diário
```

Esse número representa o marco de validação da carga histórica, e não a contagem atual do banco.

Após esse marco, o banco passou a receber dados automaticamente, e sua contagem continua aumentando.

Lacunas encontradas nos arquivos da estação são preservadas. O pipeline não fabrica medições para preencher períodos ausentes.

## 10. Aquisição automática

No ambiente Windows utilizado durante o desenvolvimento, a aquisição é executada automaticamente a cada 15 minutos pelo Agendador de Tarefas.

Fluxo operacional:

```text
Agendador do Windows
        │
        ▼
wrapper .bat
        │
        ▼
pipeline/aquisicao_maws55.py
        │
        ├──> meteorologia_15min
        └──> ingestao_arquivos
```

A automação foi validada para:

- Disparo automático;
- Intervalos consecutivos de 15 minutos;
- Aquisição de novos arquivos;
- Arquivos previamente processados;
- Reinicialização do computador;
- Retomada após falhas temporárias de conexão.

A configuração específica do Agendador e os caminhos locais dependem da máquina utilizada e não constituem requisitos universais do repositório.

## 11. Recuperação após indisponibilidade

A execução normal seleciona os oito arquivos mais recentes, equivalentes a aproximadamente duas horas de dados.

Se o computador, a rede ou a tarefa permanecerem indisponíveis por um período maior, execute explicitamente a recuperação das datas UTC afetadas:

```powershell
python pipeline\aquisicao_maws55.py --periodo AAAAMMDD --config "C:\caminho\para\ProjetoIC\config.env"
```

A operação é idempotente: arquivos previamente processados são ignorados.

Durante a validação da Parte E, esse procedimento foi utilizado para recuperar uma lacuna causada por um período sem execução automática.

## 12. Falhas e recuperação

Foi realizado um teste controlado de indisponibilidade de conexão.

Durante a falha:

- A conexão falhou explicitamente;
- O processo retornou um código diferente de zero;
- Nenhuma nova leitura foi gravada.

Após a restauração da configuração e da conectividade:

- A execução seguinte foi concluída normalmente;
- Somente o arquivo novo foi inserido;
- Não houve duplicação;
- O diário permaneceu consistente.

Esse teste validou uma falha inicial de conexão.

Uma queda ocorrendo especificamente durante a transferência de um arquivo não foi reproduzida operacionalmente. Arquivos incompatíveis ou inválidos, entretanto, são tratados individualmente pelo pipeline.

## 13. Logs

No ambiente Windows atual, a rotina automática registra sua execução em:

```text
dados/aquisicao.log
```

Foi adotada uma rotação simples por tamanho.

Quando o arquivo ultrapassa aproximadamente 5 MB, o arquivo:

```text
aquisicao.log
```

é movido para:

```text
aquisicao.log.1
```

e um novo log é iniciado.

Ambos os arquivos são ignorados pelo Git.

## 14. Segurança

- `config.env` e outros arquivos `*.env` não devem ser versionados;
- Somente `config.exemplo.env`, sem credenciais reais, deve fazer parte do repositório;
- Credenciais não devem aparecer em código, documentação, commits ou logs;
- FTPS deve ser preferido caso o servidor ofereça suporte;
- Antes de realizar commits, verifique o resultado de `git status` e o conteúdo preparado para staging;
- Contas utilizadas por automações devem seguir o princípio do menor privilégio, quando houver suporte administrativo.

## 15. Limitações conhecidas

- Algumas unidades meteorológicas ainda dependem de confirmação documental;
- Várias variáveis permanecem como dados brutos por não possuírem regras de qualidade validadas;
- `lacuna_temporal` não é inferida automaticamente para todos os arquivos adquiridos diretamente;
- A recuperação automática padrão abrange somente os oito arquivos mais recentes;
- A descoberta automática do `config.env` apresentou comportamento inconsistente no ambiente Windows validado e atualmente é contornada com o uso explícito de `--config`;
- O agendamento automático atual foi validado no ambiente Windows utilizado durante o desenvolvimento e pode exigir adaptações em outras máquinas.

## 16. Arquivos relacionados

| Arquivo | Função |
|---|---|
| `pipeline/aquisicao_maws55.py` | Interface de linha de comando |
| `pipeline/aquisicao/config.py` | Configuração |
| `pipeline/aquisicao/fontes.py` | Fontes FTP e pasta local |
| `pipeline/aquisicao/leitor.py` | Leitura dos layouts de 52 e 56 valores |
| `pipeline/aquisicao/tratamento.py` | Regras de qualidade e transformação |
| `pipeline/aquisicao/ingestao.py` | Ingestão, cópia bruta e diário |
| `app/catalogo_meteorologia.py` | Catálogo das 56 variáveis |
| `app/consultas.py` | Persistência e consultas |
| `testes/test_aquisicao.py` | Testes da aquisição |
| `relatorios/dicionario_meteorologia.md` | Dicionário das variáveis |