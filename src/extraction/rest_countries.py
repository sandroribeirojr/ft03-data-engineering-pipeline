
import json
import logging
import os

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.extraction.api_client import APIClient


# --------------------------------------------------
# CONFIGURACOES
# --------------------------------------------------

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://api.restcountries.com/countries/v5"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "rest_countries"

PAGE_SIZE = 100


# --------------------------------------------------
# AUTENTICACAO
# --------------------------------------------------

def get_api_key() -> str:
    """Recupera a chave da API das variaveis de ambiente."""

    api_key = os.getenv("REST_COUNTRIES_API_KEY")

    if not api_key:
        raise ValueError(
            "REST_COUNTRIES_API_KEY nao encontrada no arquivo .env"
        )

    return api_key


# --------------------------------------------------
# VALIDACAO DA RESPOSTA
# --------------------------------------------------

def validate_response(response: dict[str, Any]) -> None:
    """Valida a estrutura basica da resposta da API."""

    if not isinstance(response, dict):
        raise ValueError("A resposta da API nao e um dicionario.")

    if response.get("errors"):
        raise ValueError(
            f"API retornou erros: {response['errors']}"
        )

    data = response.get("data")

    if not isinstance(data, dict):
        raise ValueError("Campo data ausente ou invalido.")

    if not isinstance(data.get("objects"), list):
        raise ValueError("Campo data.objects ausente ou invalido.")

    if not isinstance(data.get("meta"), dict):
        raise ValueError("Campo data.meta ausente ou invalido.")


# --------------------------------------------------
# EXTRACAO DE UMA PAGINA
# --------------------------------------------------

def extract_page(
    client: APIClient,
    offset: int
) -> dict[str, Any]:
    """Consulta uma pagina de paises."""

    params = {
        "limit": PAGE_SIZE,
        "offset": offset
    }

    response = client.get(
        BASE_URL,
        params=params
    )

    validate_response(response)

    return response


# --------------------------------------------------
# EXTRACAO DE TODOS OS PAISES
# --------------------------------------------------

def extract_all_countries() -> dict[str, Any]:
    """Extrai todos os paises utilizando paginacao."""

    api_key = get_api_key()

    pages = []
    all_countries = []

    offset = 0
    total_records = None

    logger.info("Iniciando extracao REST Countries.")

    with APIClient(
        timeout=int(os.getenv("REQUEST_TIMEOUT", 30)),
        max_retries=int(os.getenv("MAX_RETRIES", 3)),
        rate_limit=float(os.getenv("RATE_LIMIT_SECONDS", 1))
    ) as client:

        client.session.headers.update({
            "Authorization": f"Bearer {api_key}"
        })

        while True:

            logger.info(
                "Consultando pagina com offset=%s",
                offset
            )

            response = extract_page(
                client,
                offset
            )

            data = response["data"]

            countries = data["objects"]
            meta = data["meta"]

            if total_records is None:
                total_records = meta.get("total")

                if not isinstance(total_records, int):
                    raise ValueError(
                        "Total de registros nao informado pela API."
                    )

            if not countries and offset < total_records:
                raise ValueError(
                    "API retornou pagina vazia antes do fim da extracao."
                )

            pages.append(response)
            all_countries.extend(countries)

            logger.info(
                "Pagina recebida: %s registros",
                len(countries)
            )

            if not meta.get("more", False):
                break

            if not countries:
                raise ValueError(
                    "Paginacao sem progresso: pagina vazia."
                )

            offset += len(countries)

    if len(all_countries) != total_records:
        raise ValueError(
            f"Quantidade divergente: esperados {total_records}, "
            f"recebidos {len(all_countries)}."
        )

    logger.info(
        "Extracao concluida: %s paises.",
        len(all_countries)
    )

    return {
        "metadata": {
            "source": "REST Countries API v5",
            "extracted_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "total_records": total_records,
            "pages_extracted": len(pages)
        },
        "records": all_countries,
        "raw_pages": pages
    }


# --------------------------------------------------
# PERSISTENCIA DOS DADOS BRUTOS
# --------------------------------------------------

def save_raw_data(
    data: dict[str, Any],
    run_id: str | None = None
) -> Path:
    """Salva os dados extraidos em arquivo JSON."""

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
        f"countries_{run_id}.json"
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
        "Arquivo JSON salvo em: %s",
        output_file
    )

    return output_file


# --------------------------------------------------
# EXECUCAO PRINCIPAL
# --------------------------------------------------

def main() -> None:

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    extracted_data = extract_all_countries()

    output_file = save_raw_data(extracted_data)

    print("\n===================================")
    print("EXTRACAO REST COUNTRIES CONCLUIDA")
    print("===================================")

    print(
        "Total de paises:",
        extracted_data["metadata"]["total_records"]
    )

    print(
        "Paginas consultadas:",
        extracted_data["metadata"]["pages_extracted"]
    )

    print("Arquivo gerado:", output_file)


if __name__ == "__main__":
    main()
