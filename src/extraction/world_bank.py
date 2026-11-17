
import json
import logging

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.extraction.api_client import APIClient


# ==================================================
# CONFIGURACOES
# ==================================================

logger = logging.getLogger(__name__)

BASE_URL = "https://api.worldbank.org/v2/country/all/indicator"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "world_bank"

PAGE_SIZE = 1000

START_YEAR = 2020
END_YEAR = 2024

INDICATORS = {
    "GDP": {
        "code": "NY.GDP.MKTP.CD",
        "description": "Gross Domestic Product",
        "unit": "USD"
    },
    "GDP_PER_CAPITA": {
        "code": "NY.GDP.PCAP.CD",
        "description": "GDP per capita",
        "unit": "USD"
    },
    "POPULATION": {
        "code": "SP.POP.TOTL",
        "description": "Total population",
        "unit": "people"
    },
    "LIFE_EXPECTANCY": {
        "code": "SP.DYN.LE00.IN",
        "description": "Life expectancy at birth",
        "unit": "years"
    },
    "INFLATION": {
        "code": "FP.CPI.TOTL.ZG",
        "description": "Inflation, consumer prices",
        "unit": "percentage"
    }
}


# ==================================================
# VALIDACAO DA RESPOSTA
# ==================================================

def validate_response(response: Any) -> None:
    """Valida a estrutura retornada pelo World Bank."""

    if not isinstance(response, list):
        raise ValueError(
            "Resposta do World Bank nao e uma lista."
        )

    if len(response) != 2:
        raise ValueError(
            "Estrutura JSON do World Bank inesperada."
        )

    metadata = response[0]
    records = response[1]

    if not isinstance(metadata, dict):
        raise ValueError(
            "Metadados ausentes ou invalidos."
        )

    if records is not None and not isinstance(records, list):
        raise ValueError(
            "Lista de registros invalida."
        )


# ==================================================
# EXTRACAO DE UMA PAGINA
# ==================================================

def extract_page(
    client: APIClient,
    indicator_code: str,
    page: int
) -> list[Any]:

    url = f"{BASE_URL}/{indicator_code}"

    params = {
        "format": "json",
        "per_page": PAGE_SIZE,
        "page": page,
        "date": f"{START_YEAR}:{END_YEAR}"
    }

    response = client.get(
        url,
        params=params
    )

    validate_response(response)

    return response


# ==================================================
# EXTRACAO DE UM INDICADOR
# ==================================================

def extract_indicator(
    client: APIClient,
    indicator_name: str,
    indicator_config: dict[str, str]
) -> list[dict[str, Any]]:
    """Extrai todas as paginas de um indicador."""

    indicator_code = indicator_config["code"]

    logger.info(
        "Iniciando indicador: %s (%s)",
        indicator_name,
        indicator_code
    )

    first_response = extract_page(
        client,
        indicator_code,
        page=1
    )

    metadata = first_response[0]

    total_pages = metadata.get("pages")

    if not isinstance(total_pages, int) or total_pages < 1:
        raise ValueError(
            f"Quantidade de paginas invalida: {total_pages}"
        )

    all_records = []

    for page in range(1, total_pages + 1):

        if page == 1:
            response = first_response
        else:
            response = extract_page(
                client,
                indicator_code,
                page
            )

        records = response[1] or []

        for record in records:

            all_records.append({
                "country_name": (
                    record.get("country") or {}
                ).get("value"),

                "country_iso3": record.get(
                    "countryiso3code"
                ),

                "indicator_name": indicator_name,

                "indicator_code": indicator_code,

                "indicator_description": (
                    indicator_config["description"]
                ),

                "unit": indicator_config["unit"],

                "year": record.get("date"),

                "value": record.get("value"),

                "source_note": record.get("note"),

                "observation_status": record.get(
                    "obs_status"
                )
            })

        logger.info(
            "%s | Pagina %s/%s | Registros recebidos: %s",
            indicator_name,
            page,
            total_pages,
            len(records)
        )

    logger.info(
        "Indicador %s concluido: %s registros.",
        indicator_name,
        len(all_records)
    )

    return all_records


# ==================================================
# EXTRACAO DE TODOS OS INDICADORES
# ==================================================

def extract_all_indicators() -> dict[str, Any]:
    """Executa a extracao completa dos indicadores."""

    all_records = []

    indicator_metadata = []

    with APIClient(
        timeout=90,
        max_retries=3,
        rate_limit=1
    ) as client:

        for indicator_name, config in INDICATORS.items():

            records = extract_indicator(
                client,
                indicator_name,
                config
            )

            all_records.extend(records)

            indicator_metadata.append({
                "name": indicator_name,
                "code": config["code"],
                "records_extracted": len(records)
            })

    extracted_data = {
        "metadata": {
            "source": "World Bank API V2",
            "extracted_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),

            "start_year": START_YEAR,
            "end_year": END_YEAR,

            "total_indicators": len(INDICATORS),

            "total_records": len(all_records),

            "indicators": indicator_metadata
        },

        "records": all_records
    }

    logger.info(
        "Extracao completa: %s registros.",
        len(all_records)
    )

    return extracted_data


# ==================================================
# PERSISTENCIA DOS DADOS BRUTOS
# ==================================================

def save_raw_data(
    data: dict[str, Any],
    run_id: str | None = None
) -> Path:
    """Salva os dados brutos em formato JSON."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if run_id is None:
        run_id = datetime.now(
            timezone.utc
        ).strftime("%Y%m%dT%H%M%S%fZ")

    data["metadata"]["run_id"] = run_id

    output_file = (
        OUTPUT_DIR /
        f"world_bank_{run_id}.json"
    )

    with output_file.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    logger.info(
        "Arquivo salvo: %s",
        output_file
    )

    return output_file


# ==================================================
# EXECUCAO PRINCIPAL
# ==================================================

def main() -> None:

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
    )

    logger.info(
        "Iniciando extracao completa do World Bank."
    )

    extracted_data = extract_all_indicators()

    output_file = save_raw_data(
        extracted_data
    )

    print("\n===================================")
    print("EXTRACAO WORLD BANK CONCLUIDA")
    print("===================================")

    print(
        "Indicadores:",
        extracted_data["metadata"]["total_indicators"]
    )

    print(
        "Registros:",
        extracted_data["metadata"]["total_records"]
    )

    print(
        "Periodo:",
        START_YEAR,
        "a",
        END_YEAR
    )

    print("Arquivo:", output_file)


if __name__ == "__main__":
    main()
