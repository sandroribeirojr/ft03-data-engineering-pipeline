
import re
from typing import Any

import pandas as pd


def validate_iso3(value: Any) -> bool:
    """Valida códigos ISO3."""
    if pd.isna(value):
        return False

    return bool(
        re.fullmatch(r"[A-Z]{3}", str(value).strip().upper())
    )


def validate_year(value: Any) -> bool:
    """Valida o período dos indicadores."""
    try:
        year = int(value)
        return 2020 <= year <= 2024
    except (TypeError, ValueError, OverflowError):
        return False


def validate_non_negative(value: Any) -> bool:
    """Valida valores numéricos não negativos."""
    try:
        number = float(value)
        return pd.notna(number) and number >= 0
    except (TypeError, ValueError, OverflowError):
        return False


def validate_latitude(value: Any) -> bool:
    """Valida latitude."""
    try:
        number = float(value)
        return pd.notna(number) and -90 <= number <= 90
    except (TypeError, ValueError, OverflowError):
        return False


def validate_longitude(value: Any) -> bool:
    """Valida longitude."""
    try:
        number = float(value)
        return pd.notna(number) and -180 <= number <= 180
    except (TypeError, ValueError, OverflowError):
        return False


def calculate_null_ratio(
    dataframe: pd.DataFrame
) -> dict[str, float]:
    """Calcula percentual de valores nulos por coluna."""

    if dataframe.empty:
        return {
            column: 0.0
            for column in dataframe.columns
        }

    return {
        column: round(
            float(dataframe[column].isna().mean() * 100),
            2
        )
        for column in dataframe.columns
    }


def check_unique(
    dataframe: pd.DataFrame,
    columns: list[str]
) -> dict[str, Any]:
    """Verifica unicidade de uma chave."""

    missing_columns = [
        column
        for column in columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        return {
            "valid": False,
            "error": f"Colunas ausentes: {missing_columns}"
        }

    duplicates = int(
        dataframe.duplicated(
            subset=columns,
            keep=False
        ).sum()
    )

    return {
        "valid": duplicates == 0,
        "duplicate_rows": duplicates,
        "columns": columns
    }


def validate_schema(
    dataframe: pd.DataFrame,
    expected_columns: list[str]
) -> dict[str, Any]:
    """Verifica presença das colunas obrigatórias."""

    missing_columns = [
        column
        for column in expected_columns
        if column not in dataframe.columns
    ]

    return {
        "valid": len(missing_columns) == 0,
        "missing_columns": missing_columns,
        "expected_columns": expected_columns
    }
