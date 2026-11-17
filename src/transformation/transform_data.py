
import json
import logging

from pathlib import Path

import duckdb
import pandas as pd

from src.quality.data_quality import (
    audit_rest_countries,
    audit_world_bank,
    generate_quality_report,
    validate_pipeline_tables,
)

# ==================================================
# CONFIGURACOES
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REST_COUNTRIES_DIR = (
    PROJECT_ROOT / "data" / "raw" / "rest_countries"
)

WORLD_BANK_DIR = (
    PROJECT_ROOT / "data" / "raw" / "world_bank"
)

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

DATABASE_PATH = PROCESSED_DIR / "ft03.duckdb"

logger = logging.getLogger(__name__)


# ==================================================
# LOCALIZAR ARQUIVOS
# ==================================================

def get_run_file(directory: Path, prefix: str, run_id: str) -> Path:
    """Localiza o JSON de uma fonte para a execução informada."""
    if not run_id or not run_id.isascii() or not run_id.isalnum():
        raise ValueError("run_id invalido.")

    path = directory / f"{prefix}_{run_id}.json"

    if not path.is_file():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")

    return path


# ==================================================
# CARREGAR JSON
# ==================================================

def load_json(file_path: Path) -> dict:
    """Carrega um arquivo JSON."""

    logger.info("Carregando arquivo: %s", file_path)

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


# ==================================================
# PREPARAR DADOS DOS PAISES
# ==================================================

def prepare_countries(records: list) -> pd.DataFrame:
    """Normaliza os dados principais dos países."""

    rows = []

    for record in records:

        names = record.get("names") or {}
        codes = record.get("codes") or {}
        area = record.get("area") or {}
        coordinates = record.get("coordinates") or {}

        rows.append({

            "country_iso3": (
                codes.get("alpha_3") or ""
            ).strip().upper(),

            "country_iso2": (
                codes.get("alpha_2") or ""
            ).strip().upper(),

            "country_name": names.get("common"),

            "official_name": names.get("official"),

            "region": record.get("region"),

            "subregion": record.get("subregion"),

            "population": record.get("population"),

            "area_km2": area.get("kilometers"),

            "latitude": coordinates.get("lat"),

            "longitude": coordinates.get("lng"),

            "capitals_json": json.dumps(
                record.get("capitals") or [],
                ensure_ascii=False
            ),

            "languages_json": json.dumps(
                record.get("languages") or [],
                ensure_ascii=False
            ),

            "currencies_json": json.dumps(
                record.get("currencies") or [],
                ensure_ascii=False
            )
        })

    df = pd.DataFrame(rows)

    # Padronizacao dos tipos
    df["country_iso3"] = df["country_iso3"].astype("string")

    df["country_name"] = df["country_name"].astype("string")

    df["population"] = pd.to_numeric(
        df["population"],
        errors="coerce"
    )

    df["area_km2"] = pd.to_numeric(
        df["area_km2"],
        errors="coerce"
    )

    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    )

    # Remover registros sem codigo ISO3 valido
    df = df[
        df["country_iso3"].str.fullmatch(
            r"[A-Z]{3}",
            na=False
        )
    ].copy()

    # Remover duplicidades
    df = df.drop_duplicates(
        subset=["country_iso3"],
        keep="first"
    )

    return df


# ==================================================
# PREPARAR INDICADORES ECONOMICOS
# ==================================================

def prepare_economic_data(records: list) -> pd.DataFrame:
    """Normaliza os indicadores do Banco Mundial."""

    df = pd.DataFrame(records)

    df["country_iso3"] = (
        df["country_iso3"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce"
    )

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce"
    )

    df = df[
        df["country_iso3"].str.fullmatch(
            r"[A-Z]{3}",
            na=False
        )
        & df["year"].between(2020, 2024)
    ].copy()

    df["year"] = df["year"].astype("int64")

    return df


# ==================================================
# TRANSFORMACOES SQL
# ==================================================

def execute_sql_transformations(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    """Executa os scripts SQL em uma unica transacao."""
    sql_dir = PROJECT_ROOT / "sql"
    scripts = ("dimensions.sql", "economic_indicators.sql")

    connection.begin()
    try:
        for filename in scripts:
            script = (sql_dir / filename).read_text(encoding="utf-8")
            connection.execute(script)
            logger.info("SQL executado: %s", filename)
        connection.commit()
    except Exception:
        connection.rollback()
        logger.exception("Falha na transformacao SQL. Rollback realizado.")
        raise


# ==================================================
# EXECUCAO PRINCIPAL
# ==================================================


def export_parquet(connection: duckdb.DuckDBPyConnection) -> None:
    """Exporta a tabela fato para um diretorio temporario."""
    output_dir = PROJECT_ROOT / "output" / "parquet"
    output_dir.mkdir(parents=True, exist_ok=True)

    temp_dir = output_dir / "fact_economic_indicator_tmp"

    if temp_dir.exists():
        raise FileExistsError(
            f"Diretorio temporario ja existe: {temp_dir}"
        )

    sql_path = PROJECT_ROOT / "sql" / "export_parquet.sql"
    sql = sql_path.read_text(encoding="utf-8")
    sql = sql.replace("{output_path}", temp_dir.as_posix())

    connection.execute(sql)
    logger.info("Exportacao temporaria concluida: %s", temp_dir)




def validate_parquet_export(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    """Compara os registros exportados com a tabela original."""
    parquet_path = (
        PROJECT_ROOT
        / "output"
        / "parquet"
        / "fact_economic_indicator_tmp"
        / "**"
        / "*.parquet"
    )

    source = connection.execute("""
        SELECT year, COUNT(*)
        FROM fact_economic_indicator
        GROUP BY year
        ORDER BY year
    """).fetchall()

    exported = connection.execute(
        """
        SELECT year, COUNT(*)
        FROM read_parquet(?, hive_partitioning=true)
        GROUP BY year
        ORDER BY year
        """,
        [parquet_path.as_posix()],
    ).fetchall()

    if source != exported:
        raise ValueError("Divergencia entre DuckDB e Parquet exportado.")

    compressions = connection.execute(
        "SELECT DISTINCT compression FROM parquet_metadata(?)",
        [parquet_path.as_posix()],
    ).fetchall()

    if compressions != [("SNAPPY",)]:
        raise ValueError(f"Compressao Parquet inesperada: {compressions}")

    logger.info("Validacao Parquet aprovada: %s registros.", sum(
        count for _, count in exported
    ))




def publish_parquet() -> None:
    """Publica o Parquet temporario com backup e recuperacao."""
    base = PROJECT_ROOT / "output" / "parquet"
    final = base / "fact_economic_indicator"
    temp = base / "fact_economic_indicator_tmp"
    backup = base / "fact_economic_indicator_backup"

    if not temp.is_dir():
        raise FileNotFoundError(f"Exportacao temporaria ausente: {temp}")

    if backup.exists():
        raise FileExistsError(f"Backup anterior ainda existe: {backup}")

    if final.exists():
        final.rename(backup)

    try:
        temp.rename(final)
    except Exception:
        if backup.exists():
            backup.rename(final)
        raise

    if backup.exists():
        import shutil
        shutil.rmtree(backup)

    logger.info("Parquet publicado: %s", final)



def main(run_id: str) -> None:

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Localizar arquivos da mesma execucao
    rest_file = get_run_file(
        REST_COUNTRIES_DIR, "countries", run_id
    )
    world_file = get_run_file(
        WORLD_BANK_DIR, "world_bank", run_id
    )

    # Carregar JSON
    rest_data = load_json(rest_file)

    world_data = load_json(world_file)

    for source, data in (
        ("REST Countries", rest_data),
        ("World Bank", world_data),
    ):
        if data.get("metadata", {}).get("run_id") != run_id:
            raise ValueError(f"run_id inconsistente em {source}.")

    # Preparar DataFrames
    countries_df = prepare_countries(
        rest_data["records"]
    )

    economic_df = prepare_economic_data(
        world_data["records"]
    )

    logger.info(
        "Paises com ISO3 valido: %s",
        len(countries_df)
    )

    logger.info(
        "Registros economicos validos: %s",
        len(economic_df)
    )

    # Conectar ao DuckDB
    with duckdb.connect(str(DATABASE_PATH)) as connection:

        connection.register(
            "countries_staging",
            countries_df
        )

        connection.register(
            "economic_staging",
            economic_df
        )

        duplicates = economic_df.duplicated().sum()
        conflicts = economic_df.drop_duplicates().duplicated(
            subset=["country_iso3", "indicator_code", "year"]
        ).sum()

        logger.info("Duplicatas identicas: %s", duplicates)
        logger.info("Chaves conflitantes: %s", conflicts)

        if conflicts:
            raise ValueError(
                f"Encontradas {conflicts} chaves economicas conflitantes."
            )

        
        execute_sql_transformations(connection)
        
        
        quality_results = validate_pipeline_tables(connection)
        quality_results.append(
            audit_world_bank(world_data["records"], len(economic_df))
        )
        quality_results.append(
            audit_rest_countries(rest_data["records"], len(countries_df))
        )
        report_path = generate_quality_report(
            quality_results,
            PROJECT_ROOT / "output" / "reports",
            run_id,
        )


        logger.info("Relatorio de qualidade: %s", report_path)

        if not all(result["valid"] for result in quality_results):
            raise ValueError("Falha nas validacoes de qualidade.")
        
        export_parquet(connection)
        validate_parquet_export(connection)
        publish_parquet()

        # Resumo das tabelas
        tables = [
            "countries",
            "country_capitals",
            "country_languages",
            "country_currencies",
            "economic_indicators",
            "country_economic_data"
        ]

        print("\n===================================")
        print("RESULTADO DAS TRANSFORMACOES")
        print("===================================")

        for table in tables:

            result = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            print(f"{table}: {result} registros")

        # Validar Brasil
        print("\nDADOS ECONOMICOS DO BRASIL")

        brazil = connection.execute("""
            SELECT
                country_name,
                year,
                gdp,
                gdp_per_capita,
                wb_population,
                life_expectancy,
                inflation

            FROM country_economic_data

            WHERE country_iso3 = 'BRA'

            ORDER BY year DESC
        """).df()

        print(brazil.to_string(index=False))

    print("\nBanco DuckDB criado:")
    print(DATABASE_PATH)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Transforma dados de uma execucao."
    )
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    main(args.run_id)
