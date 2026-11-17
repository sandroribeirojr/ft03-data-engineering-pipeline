
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.transformation.data_validation import (
    calculate_null_ratio,
    check_unique,
    validate_schema,
)


logger = logging.getLogger(__name__)


def validate_dataframe(
    dataframe: pd.DataFrame,
    dataset_name: str,
    expected_columns: list[str],
    unique_columns: list[str],
) -> dict[str, Any]:
    """
    Executa verificações de qualidade em um DataFrame.
    """

    logger.info(
        "Iniciando validação do dataset: %s",
        dataset_name,
    )

    schema_result = validate_schema(
        dataframe,
        expected_columns,
    )

    uniqueness_result = check_unique(
        dataframe,
        unique_columns,
    )

    null_ratios = calculate_null_ratio(dataframe)

    checks = {
        "schema": schema_result,
        "uniqueness": uniqueness_result,
    }

    valid_checks = [
        result["valid"]
        for result in checks.values()
    ]

    return {
        "dataset": dataset_name,
        "total_records": len(dataframe),
        "total_columns": len(dataframe.columns),
        "schema": schema_result,
        "uniqueness": uniqueness_result,
        "null_ratio_percent": null_ratios,
        "valid": all(valid_checks),
    }


def validate_numeric_range(
    dataframe: pd.DataFrame,
    column: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> dict[str, Any]:
    """
    Verifica se os valores numéricos estão dentro
    dos limites definidos.
    """

    if column not in dataframe.columns:
        return {
            "valid": False,
            "error": f"Coluna ausente: {column}",
        }

    values = pd.to_numeric(
        dataframe[column],
        errors="coerce",
    )

    invalid_mask = values.isna()

    if minimum is not None:
        invalid_mask |= values < minimum

    if maximum is not None:
        invalid_mask |= values > maximum

    invalid_count = int(invalid_mask.sum())

    return {
        "column": column,
        "minimum": minimum,
        "maximum": maximum,
        "invalid_records": invalid_count,
        "valid": invalid_count == 0,
    }


def generate_quality_report(
    results: list[dict[str, Any]],
    output_directory: Path,
    run_id: str,
) -> Path:
    """
    Gera relatório JSON de qualidade dos dados.
    """

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = {
        "run_id": run_id,
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_datasets": len(results),
        "datasets": results,
        "overall_status": (
            "PASSED" if all(item["valid"] for item in results) else "FAILED"
        ),
    }

    report_path = (
        output_directory / "data_quality_report.json"
    )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=4,
            default=str,
        )

    logger.info(
        "Relatório de qualidade gerado: %s",
        report_path,
    )

    return report_path



def validate_pipeline_tables(
    connection: Any,
) -> list[dict[str, Any]]:
    """Valida esquema, unicidade, nulos e intervalos."""
    datasets = {
        "countries": (
            ["country_iso3", "country_name", "population"],
            ["country_iso3"],
            {"population": (0, None), "latitude": (-90, 90),
             "longitude": (-180, 180)},
        ),
        "country_capitals": (
            ["country_iso3", "capital_name", "latitude", "longitude"],
            ["country_iso3", "capital_name"],
            {"latitude": (-90, 90), "longitude": (-180, 180)},
        ),
        "fact_economic_indicator": (
            ["country_iso3", "indicator_code", "year", "value"],
            ["country_iso3", "indicator_code", "year"],
            {"year": (2020, 2024)},
        ),
        "economic_unmatched": (
            ["country_iso3", "indicator_code", "year", "rejection_reason"],
            ["country_iso3", "indicator_code", "year"],
            {"year": (2020, 2024)},
        ),
    }

    results = []

    for table, (columns, keys, ranges) in datasets.items():
        df = connection.execute(f"SELECT * FROM {table}").df()
        result = validate_dataframe(df, table, columns, keys)

        result["ranges"] = {
            column: validate_numeric_range(df, column, minimum, maximum)
            for column, (minimum, maximum) in ranges.items()
        }
        result["valid"] &= all(
            check["valid"] for check in result["ranges"].values()
        )
        results.append(result)

    results.append(validate_referential_integrity(connection))
    return results


def validate_referential_integrity(connection: Any) -> dict[str, Any]:
    """Valida integridade referencial e reconciliacao."""
    sql_path = Path(__file__).resolve().parents[2] / "sql" / "data_quality.sql"
    queries = sql_path.read_text(encoding="utf-8").split(";")

    orphan_count = connection.execute(queries[0]).fetchone()[0]
    total, matched, unmatched = connection.execute(queries[1]).fetchone()
    difference = total - matched - unmatched

    return {
        "dataset": "referential_integrity",
        "orphan_records": orphan_count,
        "source_records": total,
        "matched_records": matched,
        "unmatched_records": unmatched,
        "reconciliation_difference": difference,
        "valid": orphan_count == 0 and difference == 0,
    }


def audit_extraction(
    source: str,
    extracted: int,
    prepared: int,
    reasons: dict[str, int],
) -> dict[str, Any]:
    """Audita a quantidade de registros preservados na preparacao."""
    excluded = extracted - prepared
    return {
        "dataset": f"{source}_extraction",
        "extracted_records": extracted,
        "prepared_records": prepared,
        "excluded_records": excluded,
        "exclusion_reasons": reasons,
        "valid": excluded >= 0 and sum(reasons.values()) == excluded,
    }


def audit_world_bank(
    records: list[dict[str, Any]],
    prepared: int,
) -> dict[str, Any]:
    """Audita registros economicos excluidos na preparacao."""
    df = pd.DataFrame(records)
    iso3 = df["country_iso3"].fillna("").astype(str).str.strip().str.upper()
    year = pd.to_numeric(df["year"], errors="coerce")

    invalid_iso3 = ~iso3.str.fullmatch(r"[A-Z]{3}")
    invalid_year = ~(year.between(2020, 2024) & year.mod(1).eq(0))

    reasons = {
        "invalid_iso3": int(invalid_iso3.sum()),
        "invalid_year_only": int((~invalid_iso3 & invalid_year).sum()),
    }

    return audit_extraction("world_bank", len(df), prepared, reasons)


def audit_rest_countries(
    records: list[dict[str, Any]],
    prepared: int,
) -> dict[str, Any]:
    """Audita a preparacao dos registros de paises."""
    iso3 = pd.Series(
        [record.get("codes", {}).get("alpha_3") for record in records],
        dtype="string",
    ).str.strip().str.upper()

    invalid_iso3 = int((~iso3.fillna("").str.fullmatch(r"[A-Z]{3}")).sum())

    return audit_extraction(
        "rest_countries",
        len(records),
        prepared,
        {"invalid_iso3": invalid_iso3},
    )
