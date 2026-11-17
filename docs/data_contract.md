
# Data Contract — FT03 Data Engineering Pipeline

## 1. Objetivo

Definir os contratos de dados das fontes REST Countries API
e World Bank API, estabelecendo regras de estrutura,
tipagem, integridade, padronização e relacionamento.

## 2. Fontes de dados

### 2.1 REST Countries API

- Domínio: informações geográficas e demográficas.
- Formato de origem: JSON.
- Registros extraídos: 254.
- Identificador de relacionamento: codes.alpha_3.

### 2.2 World Bank API

- Domínio: indicadores econômicos e demográficos.
- Formato de origem: JSON.
- Registros extraídos: 6.650.
- Indicadores: 5.
- Período: 2020–2024.
- Identificador de relacionamento: country_iso3.

## 3. Contrato REST Countries

| Campo de origem | Campo destino | Tipo | Regra |
|---|---|---|---|
| codes.alpha_3 | country_iso3 | VARCHAR | Obrigatório, 3 letras |
| codes.alpha_2 | country_iso2 | VARCHAR | Opcional, 2 letras |
| names.common | country_name | VARCHAR | Obrigatório |
| names.official | official_name | VARCHAR | Opcional |
| region | region | VARCHAR | Opcional |
| subregion | subregion | VARCHAR | Opcional |
| population | population | BIGINT | Não negativo |
| area.kilometers | area_km2 | DOUBLE | Não negativo |
| coordinates.lat | latitude | DOUBLE | Entre -90 e 90 |
| coordinates.lng | longitude | DOUBLE | Entre -180 e 180 |

### Estruturas aninhadas

As seguintes estruturas deverão ser desaninhadas via SQL:

- capitals: nome e coordenadas das capitais.
- languages: nome, nome nativo e códigos linguísticos.
- currencies: código, nome e símbolo da moeda.

Cada estrutura será disponibilizada em uma tabela própria.

## 4. Contrato World Bank

| Campo de origem | Campo destino | Tipo | Regra |
|---|---|---|---|
| countryiso3code | country_iso3 | VARCHAR | 3 letras |
| country.value | country_name | VARCHAR | Opcional |
| indicator_name | indicator_name | VARCHAR | Obrigatório |
| indicator_code | indicator_code | VARCHAR | Obrigatório |
| date | year | INTEGER | 2020 a 2024 |
| value | value | DOUBLE | Nulo permitido |
| unit | unit | VARCHAR | Opcional |
| source_note | source_note | VARCHAR | Nulo permitido |

### Indicadores utilizados

| Indicador | Código |
|---|---|
| GDP | NY.GDP.MKTP.CD |
| GDP_PER_CAPITA | NY.GDP.PCAP.CD |
| POPULATION | SP.POP.TOTL |
| LIFE_EXPECTANCY | SP.DYN.LE00.IN |
| INFLATION | FP.CPI.TOTL.ZG |

## 5. Regras de transformação

1. Padronizar códigos ISO em letras maiúsculas.
2. Converter valores numéricos para seus tipos adequados.
3. Converter ano para INTEGER.
4. Converter valores ausentes para NULL.
5. Identificar e tratar strings vazias.
6. Validar códigos ISO3.
7. Remover duplicidades exatas.
8. Identificar duplicidades conflitantes.
9. Desaninhar arrays e objetos JSON via DuckDB SQL.
10. Cruzar as fontes utilizando country_iso3.
11. Preservar separadamente as populações das duas fontes.
12. Criar data de referência utilizando o ano do indicador.

## 6. Regras de integridade

- country_iso3 deve possuir três letras maiúsculas.
- country_iso3 deve ser único na dimensão de países.
- country_iso3 + indicator_code + year deve identificar
  uma observação econômica.
- year deve estar entre 2020 e 2024.
- population não pode ser negativo.
- area_km2 não pode ser negativo.
- latitude deve estar entre -90 e 90.
- longitude deve estar entre -180 e 180.

## 7. Tratamento de valores ausentes

- Campos obrigatórios ausentes devem ser identificados.
- Países sem ISO3 válido não participam do JOIN.
- Registros sem valor econômico são preservados na
  tabela de observações, com value NULL.
- source_note, por estar totalmente nulo nesta extração,
  não será disponibilizado na camada analítica final.
- Campos opcionais podem permanecer nulos.

## 8. Modelo de dados final

### Dimensão

countries:
- country_iso3
- country_iso2
- country_name
- official_name
- region
- subregion
- population
- area_km2
- latitude
- longitude

### Tabelas auxiliares

country_capitals:
- country_iso3
- capital_name
- latitude
- longitude

country_languages:
- country_iso3
- language_name
- native_name
- language_code

country_currencies:
- country_iso3
- currency_code
- currency_name
- currency_symbol

### Fato econômica

fact_economic_indicator:
- country_iso3
- indicator_name
- indicator_code
- year
- value
- unit

### Dataset analítico consolidado

country_economic_data:
- country_iso3
- country_name
- region
- subregion
- rest_population
- year
- gdp
- gdp_per_capita
- wb_population
- life_expectancy
- inflation
- reference_date

Granularidade: uma linha por país e ano.

## 9. Estratégia de particionamento

A tabela `fact_economic_indicator` é exportada para
arquivos Parquet, particionados pelo campo `year`.

Estrutura de saída:

output/parquet/fact_economic_indicator/year=2020/
output/parquet/fact_economic_indicator/year=2021/
output/parquet/fact_economic_indicator/year=2022/
output/parquet/fact_economic_indicator/year=2023/
output/parquet/fact_economic_indicator/year=2024/

Formato: Parquet.
Compressão: Snappy.

A exportação é realizada inicialmente em um diretório
temporário. Após a validação das contagens por ano e
da compressão, os arquivos são publicados no diretório
definitivo, com mecanismo de backup e recuperação.

## 10. Governança e auditoria

A execução deverá gerar relatório de Data Quality
contendo:

- Quantidade de registros de origem.
- Quantidade de registros processados.
- Quantidade de registros rejeitados.
- Quantidade de duplicidades.
- Percentual de valores nulos.
- Resultado das validações de schema.
- Resultado dos testes de unicidade.
- Resultado dos testes de intervalo.
- Quantidade de registros resultantes do JOIN.
- Data e hora da execução.
