
import logging

from datetime import datetime, timezone

from dotenv import load_dotenv

from src.extraction.rest_countries import (
    extract_all_countries,
    save_raw_data as save_countries,
)

from src.extraction.world_bank import (
    extract_all_indicators,
    save_raw_data as save_world_bank,
)

from src.transformation.transform_data import main as transform_data

def main() -> None:
    """Orquestra a execução das extrações de dados."""

    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    logger = logging.getLogger(__name__)

    run_id = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%S%fZ")

    logger.info("========================================")
    logger.info("INICIANDO PIPELINE DE DADOS")
    logger.info("RUN ID: %s", run_id)
    logger.info("========================================")

    try:
        # ------------------------------------------
        # 1. EXTRACAO REST COUNTRIES
        # ------------------------------------------

        logger.info("Iniciando REST Countries.")

        countries_data = extract_all_countries()

        countries_file = save_countries(
            countries_data,
            run_id
        )

        logger.info(
            "REST Countries concluido: %s",
            countries_file
        )

        # ------------------------------------------
        # 2. EXTRACAO WORLD BANK
        # ------------------------------------------

        logger.info("Iniciando World Bank.")

        world_bank_data = extract_all_indicators()

        world_bank_file = save_world_bank(
            world_bank_data,
            run_id
        )

        logger.info(
            "World Bank concluido: %s",
            world_bank_file
        )


        # ------------------------------------------
        # 3. TRANSFORMACAO E QUALIDADE DOS DADOS
        # ------------------------------------------

        logger.info("Iniciando transformacao e Data Quality.")

        transform_data(run_id)

        logger.info("Transformacao e publicacao concluidas.")


        logger.info("========================================")
        logger.info("PIPELINE DE DADOS CONCLUIDO")
        logger.info("RUN ID: %s", run_id)
        logger.info("========================================")

    except Exception:
        logger.exception(
            "Falha durante a execução do pipeline. RUN ID: %s",
            run_id
        )
        raise


if __name__ == "__main__":
    main()
