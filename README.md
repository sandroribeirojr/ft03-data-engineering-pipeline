# FT03 — Data Engineering Pipeline

Pipeline de engenharia de dados desenvolvido em Python e SQL para integrar informações geográficas, demográficas e econômicas provenientes de duas APIs públicas.

O projeto implementa um fluxo automatizado de extração, transformação, validação de qualidade e persistência de dados analíticos.

## 1. Objetivo

Construir um pipeline de dados reproduzível que:

- Consuma duas APIs públicas de domínios distintos.
- Armazene os dados brutos em formato JSON.
- Realize transformações utilizando Python e DuckDB SQL.
- Desaninhe estruturas JSON e integre informações por código ISO3.
- Execute validações de Data Quality e gere relatórios de auditoria.
- Exporte os dados finais em Parquet, com compressão Snappy e particionamento por ano.
- Permita executar todas as etapas por meio de um único comando.

## 2. Fontes de dados

### REST Countries API

Fonte de informações geográficas e demográficas dos países, incluindo nomes, códigos ISO, população, localização, capitais, idiomas e moedas.

### World Bank API

Fonte de indicadores econômicos e demográficos, considerando o período de 2020 a 2024.

Indicadores utilizados:

| Indicador | Código |
|---|---|
| PIB | `NY.GDP.MKTP.CD` |
| PIB per capita | `NY.GDP.PCAP.CD` |
| População | `SP.POP.TOTL` |
| Expectativa de vida | `SP.DYN.LE00.IN` |
| Inflação | `FP.CPI.TOTL.ZG` |

As fontes são integradas por meio do código ISO3 dos países.

## 3. Arquitetura do pipeline

O pipeline segue um fluxo ETL (Extract, Transform, Load), com extração de dados de APIs públicas, transformação utilizando Python e DuckDB SQL e publicação dos resultados em Parquet.

```text
REST Countries API       World Bank API
        |                       |
        v                       v
    Extração                Extração
        |                       |
        v                       v
    JSON bruto              JSON bruto
        |                       |
        +-----------+-----------+
                    |
                    v
          Preparação dos dados
                    |
                    v
         Transformações DuckDB
                    |
                    v
        Validações Data Quality
                    |
                    v
        Exportação Parquet (tmp)
                    |
                    v
       Validação de contagens
          e compressão Snappy
                    |
                    v
         Publicação definitiva
                    |
                    v
       Parquet particionado por ano
```

A execução é coordenada por `src/run_pipeline.py`, responsável por gerar um identificador único (`run_id`) e utilizá-lo nas etapas de extração, transformação e auditoria.

### Estrutura do projeto

```text
ft03-data-engineering-pipeline/
├── data/
│   ├── raw/                  # JSONs extraídos das APIs
│   └── processed/            # Banco DuckDB
├── docs/
│   └── data_contract.md      # Contratos e regras dos dados
├── output/
│   ├── parquet/              # Dados finais particionados
│   └── reports/              # Relatório de Data Quality
├── sql/
│   ├── dimensions.sql
│   ├── economic_indicators.sql
│   ├── data_quality.sql
│   └── export_parquet.sql
├── src/
│   ├── extraction/           # Clientes HTTP e extrações
│   ├── transformation/       # Preparação e transformações
│   ├── quality/              # Validações e auditoria
│   └── run_pipeline.py       # Orquestrador principal
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

As consultas SQL são mantidas em arquivos separados do código Python, facilitando a manutenção e a compreensão das transformações.

Os dados brutos e o banco DuckDB são gerados durante a execução. Os resultados finais são publicados em `output/parquet/fact_economic_indicator/`, particionados pelo campo `year`.

## 4. Instalação e configuração

### Pré-requisitos

- Python 3.10 ou superior.
- Git.
- Acesso à internet para consultar as APIs públicas.

### Criar o ambiente virtual

No PowerShell, na raiz do projeto:

```powershell
python -m venv .venv
```

Ativar o ambiente virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Instalar as dependências

```powershell
pip install -r requirements.txt
```

O projeto utiliza principalmente:

- `requests`: requisições HTTP às APIs.
- `pandas`: preparação e padronização dos dados.
- `duckdb`: transformações SQL e consultas analíticas.
- `pyarrow`: suporte ao formato Parquet.
- `python-dotenv`: carregamento das configurações.
- `tenacity`: tentativas automáticas em caso de falhas nas requisições.

### Configurar as variáveis de ambiente

Crie o arquivo `.env` a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

As configurações disponíveis incluem:

| Variável | Finalidade |
|---|---|
| `REST_COUNTRIES_API_KEY` | Chave de API, caso necessária |
| `WORLD_BANK_API_KEY` | Chave de API, caso necessária |
| `REQUEST_TIMEOUT` | Tempo limite das requisições HTTP |
| `MAX_RETRIES` | Número máximo de tentativas |
| `RATE_LIMIT_SECONDS` | Intervalo mínimo entre requisições |
| `LOG_LEVEL` | Nível de detalhamento dos logs |

As APIs utilizadas são públicas. O arquivo `.env` não deve ser versionado no Git.

## 5. Execução do pipeline

Com o ambiente virtual ativado e as dependências instaladas, execute na raiz do projeto:

```powershell
python -m src.run_pipeline
```

Esse comando realiza automaticamente:

1. Extração dos dados da REST Countries API.
2. Extração dos indicadores da World Bank API.
3. Armazenamento dos dados brutos em JSON.
4. Preparação e transformação dos dados no DuckDB.
5. Execução das validações de Data Quality.
6. Geração do relatório de auditoria.
7. Exportação temporária dos arquivos Parquet.
8. Validação dos registros e da compressão Snappy.
9. Publicação definitiva dos arquivos particionados por ano.

Cada execução recebe um `run_id` único, utilizado para identificar os arquivos de origem e o relatório de qualidade.

### Executar somente as transformações

Também é possível executar a transformação utilizando arquivos JSON de uma extração anterior:

```powershell
python -m src.transformation.transform_data --run-id <RUN_ID>
```

Substitua `<RUN_ID>` pelo identificador de uma execução existente.

### Arquivos gerados

Os principais resultados são:

- `data/raw/`: arquivos JSON das duas fontes.
- `data/processed/ft03.duckdb`: banco de dados analítico.
- `output/reports/data_quality_report.json`: relatório de qualidade e auditoria.
- `output/parquet/fact_economic_indicator/`: arquivos Parquet finais, particionados por ano e comprimidos com Snappy.

## 6. Transformações de dados

As transformações combinam preparação em Python com consultas SQL executadas pelo DuckDB.

Os arquivos SQL ficam separados do código Python, no diretório `sql/`.

### Preparação e padronização

As principais operações incluem:

1. Padronização dos códigos ISO3 dos países.
2. Conversão de campos numéricos e temporais.
3. Identificação e tratamento de valores ausentes.
4. Remoção de registros com identificadores inválidos.
5. Identificação de duplicidades exatas e chaves conflitantes.
6. Integração das duas fontes pelo campo `country_iso3`.

Os valores econômicos ausentes são preservados como `NULL`, evitando a criação de valores artificiais.

### Desaninhamento de estruturas JSON

O arquivo `sql/dimensions.sql` utiliza funções JSON do DuckDB para transformar estruturas aninhadas da REST Countries em tabelas relacionais.

São produzidas as seguintes tabelas:

| Tabela | Descrição |
|---|---|
| `countries` | Informações geográficas e demográficas dos países |
| `country_capitals` | Capitais e suas coordenadas |
| `country_languages` | Idiomas associados aos países |
| `country_currencies` | Moedas utilizadas pelos países |

### Transformações econômicas

O arquivo `sql/economic_indicators.sql` organiza os indicadores do World Bank e realiza a integração com os dados dos países.

| Tabela | Descrição |
|---|---|
| `economic_indicators` | Indicadores econômicos preparados |
| `country_economic_data` | Dataset consolidado por país e ano |
| `fact_economic_indicator` | Tabela fato com indicadores associados aos países |
| `economic_unmatched` | Registros econômicos sem correspondência na dimensão de países |

O dataset `country_economic_data` apresenta os cinco indicadores em colunas, com granularidade de país e ano.

A tabela `fact_economic_indicator` possui granularidade de país, indicador e ano, sendo utilizada para a exportação final em Parquet.

Os registros sem correspondência são mantidos separadamente para auditoria, em vez de serem descartados silenciosamente.

## 7. Data Quality e auditoria

O pipeline executa validações automáticas após as transformações SQL e antes da publicação dos arquivos Parquet.

As verificações incluem:

- **Schema:** presença das colunas obrigatórias.
- **Unicidade:** identificação de duplicatas nas chaves dos datasets.
- **Valores nulos:** cálculo do percentual de valores ausentes por coluna.
- **Intervalos:** validação de anos, população e coordenadas geográficas.
- **Integridade referencial:** identificação de registros órfãos após a integração das fontes.
- **Reconciliação:** conferência das quantidades de registros correspondentes e não correspondentes.
- **Auditoria das extrações:** registro das quantidades extraídas, preparadas e excluídas.

### Resultados da execução validada

A execução de referência foi identificada pelo `run_id`:

`20261117T193454346737Z`

| Métrica | Resultado |
|---|---:|
| Países extraídos | 254 |
| Países preparados | 250 |
| Registros World Bank extraídos | 6.650 |
| Registros econômicos preparados | 6.525 |
| Registros na tabela fato | 5.375 |
| Registros econômicos sem correspondência | 1.150 |
| Registros órfãos | 0 |
| Diferença de reconciliação | 0 |
| Datasets auditados | 7 |
| Status geral | `PASSED` |

A reconciliação dos registros econômicos preparados foi:

```text
6.525 = 5.375 + 1.150
```

### Tratamento de registros excluídos

Durante a preparação dos dados:

- 4 registros REST Countries foram excluídos por código ISO3 inválido.
- 125 registros World Bank foram excluídos por código ISO3 inválido.

Essas exclusões são registradas no relatório de auditoria.

Os registros econômicos sem correspondência na dimensão de países são mantidos na tabela `economic_unmatched`.

### Tratamento de valores nulos

Valores econômicos ausentes são preservados como `NULL`.

Na execução de referência, a coluna `value` da tabela `fact_economic_indicator` apresentou **5,43% de valores nulos**.

Esse percentual é documentado no relatório e não é tratado automaticamente como falha, conforme as regras implementadas.

### Relatório de qualidade

O relatório é gerado em:

```text
output/reports/data_quality_report.json
```

O arquivo contém o identificador da execução, a data e hora, os resultados das verificações e o status geral.

Caso alguma validação obrigatória falhe, o pipeline interrompe a execução antes da publicação dos arquivos Parquet.

## 8. Persistência e publicação em Parquet

O pipeline utiliza o DuckDB para exportar a tabela `fact_economic_indicator` em formato Parquet, com compressão Snappy e particionamento temporal pelo campo `year`.

### Estrutura dos arquivos

```text
output/
└── parquet/
    └── fact_economic_indicator/
        ├── year=2020/
        │   └── data_0.parquet
        ├── year=2021/
        │   └── data_0.parquet
        ├── year=2022/
        │   └── data_0.parquet
        ├── year=2023/
        │   └── data_0.parquet
        └── year=2024/
            └── data_0.parquet
```

Na execução de referência, foram publicados cinco arquivos Parquet, contendo 5.375 registros no total, distribuídos igualmente entre os anos de 2020 e 2024.

### Estratégia de publicação

A publicação utiliza três etapas:

1. **Exportação temporária:** os dados são exportados inicialmente para `fact_economic_indicator_tmp`.
2. **Validação:** o pipeline compara a quantidade de registros por ano com a tabela DuckDB e verifica a compressão Snappy.
3. **Publicação definitiva:** após a validação, o diretório temporário substitui o diretório final.

Durante a substituição, o diretório anterior é renomeado para backup. Se ocorrer uma falha na promoção dos arquivos temporários, o pipeline tenta restaurar o diretório anterior.

Após a publicação bem-sucedida, o backup é removido.

### Consultando os arquivos Parquet

Os arquivos publicados podem ser consultados diretamente pelo DuckDB, sem necessidade de importá-los para um banco de dados.

Exemplo em Python:

```python
import duckdb

with duckdb.connect() as connection:
    result = connection.execute("""
        SELECT year, COUNT(*) AS total
        FROM read_parquet(
            'output/parquet/fact_economic_indicator/**/*.parquet',
            hive_partitioning=true
        )
        GROUP BY year
        ORDER BY year
    """).fetchall()

    for year, total in result:
        print(year, total)
```

A estrutura particionada permite consultar os dados por ano e facilita o processamento analítico.