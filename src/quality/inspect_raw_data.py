
import json
import logging

from collections import Counter
from pathlib import Path
from typing import Any


# ==================================================
# CONFIGURAÇÕES
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REST_COUNTRIES_DIR = (
    PROJECT_ROOT / "data" / "raw" / "rest_countries"
)

WORLD_BANK_DIR = (
    PROJECT_ROOT / "data" / "raw" / "world_bank"
)

logger = logging.getLogger(__name__)


# ==================================================
# LOCALIZAR ARQUIVOS
# ==================================================

def get_latest_json(directory: Path) -> Path:
    """
    Localiza o arquivo JSON mais recente de uma fonte.
    """

    if not directory.exists():
        raise FileNotFoundError(
            f"Diretório não encontrado: {directory}"
        )

    files = list(directory.glob("*.json"))

    if not files:
        raise FileNotFoundError(
            f"Nenhum arquivo JSON encontrado em {directory}"
        )

    return max(
        files,
        key=lambda file: file.stat().st_mtime
    )


# ==================================================
# CARREGAR JSON
# ==================================================

def load_json(file_path: Path) -> Any:
    """
    Carrega um arquivo JSON e valida sua leitura.
    """

    logger.info("Lendo arquivo: %s", file_path.name)

    try:
        with file_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"JSON inválido: {file_path}"
        ) from error


# ==================================================
# IDENTIFICAR TIPO DOS CAMPOS
# ==================================================

def get_value_type(value: Any) -> str:
    """
    Retorna o tipo Python de um valor.
    """

    if value is None:
        return "null"

    if isinstance(value, bool):
        return "bool"

    if isinstance(value, dict):
        return "dict"

    if isinstance(value, list):
        return "list"

    return type(value).__name__


# ==================================================
# INSPECIONAR REGISTROS
# ==================================================

def inspect_records(
    source_name: str,
    records: list
) -> None:

    print("\n" + "=" * 70)
    print(f"INSPEÇÃO: {source_name}")
    print("=" * 70)

    print(f"\nTotal de registros: {len(records)}")

    if not records:
        print("ATENÇÃO: Nenhum registro encontrado.")
        return

    first_record = records[0]

    if not isinstance(first_record, dict):
        print(
            "ATENÇÃO: O primeiro registro não é um objeto JSON."
        )
        print("Tipo encontrado:", get_value_type(first_record))
        return

    print("\nCAMPOS IDENTIFICADOS")
    print("-" * 70)

    for field, value in first_record.items():

        print(
            f"{field:<30} "
            f"Tipo: {get_value_type(value):<12} "
            f"Valor: {str(value)[:70]}"
        )

    print("\nESTRUTURAS ANINHADAS")
    print("-" * 70)

    for field, value in first_record.items():

        if isinstance(value, dict):

            print(f"\n{field}:")
            print("Subcampos:", list(value.keys()))

        elif isinstance(value, list):

            print(f"\n{field}:")
            print("Quantidade de elementos:", len(value))

            if value:
                print(
                    "Tipo do primeiro elemento:",
                    get_value_type(value[0])
                )

                if isinstance(value[0], dict):
                    print(
                        "Subcampos do primeiro elemento:",
                        list(value[0].keys())
                    )

                    if field == "capitals":
                        print(
                            "Exemplo de capital:",
                            json.dumps(
                                value[0],
                                ensure_ascii=False,
                                indent=2
                            )
                        )

    print("\nANÁLISE DE VALORES NULOS")
    print("-" * 70)

    field_names = set()

    for record in records:
        if isinstance(record, dict):
            field_names.update(record.keys())

    for field in sorted(field_names):

        null_count = sum(
            1
            for record in records
            if not isinstance(record, dict)
            or record.get(field) is None
        )

        null_ratio = null_count / len(records) * 100

        print(
            f"{field:<30} "
            f"Nulos: {null_count:<8} "
            f"Null ratio: {null_ratio:.2f}%"
        )


# ==================================================
# INSPECIONAR ARQUIVO REST COUNTRIES
# ==================================================

def inspect_rest_countries() -> None:

    file_path = get_latest_json(
        REST_COUNTRIES_DIR
    )

    data = load_json(file_path)

    print("\nARQUIVO REST COUNTRIES")
    print("Arquivo:", file_path.name)

    if not isinstance(data, dict):
        raise ValueError(
            "Estrutura principal do REST Countries inválida."
        )

    print("\nMETADADOS")

    print(
        json.dumps(
            data.get("metadata", {}),
            ensure_ascii=False,
            indent=2
        )
    )

    records = data.get("records")

    if not isinstance(records, list):
        raise ValueError(
            "Campo records não encontrado como lista."
        )

    inspect_records(
        "REST COUNTRIES",
        records
    )


# ==================================================
# INSPECIONAR ARQUIVO WORLD BANK
# ==================================================

def inspect_world_bank() -> None:

    file_path = get_latest_json(
        WORLD_BANK_DIR
    )

    data = load_json(file_path)

    print("\nARQUIVO WORLD BANK")
    print("Arquivo:", file_path.name)

    if not isinstance(data, dict):
        raise ValueError(
            "Estrutura principal do World Bank inválida."
        )

    print("\nMETADADOS")

    print(
        json.dumps(
            data.get("metadata", {}),
            ensure_ascii=False,
            indent=2
        )
    )

    records = data.get("records")

    if not isinstance(records, list):
        raise ValueError(
            "Campo records não encontrado como lista."
        )

    inspect_records(
        "WORLD BANK",
        records
    )


# ==================================================
# EXECUÇÃO PRINCIPAL
# ==================================================

def main() -> None:

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    inspect_rest_countries()

    inspect_world_bank()

    print("\n" + "=" * 70)
    print("INSPEÇÃO DOS DADOS CONCLUÍDA")
    print("=" * 70)


if __name__ == "__main__":
    main()
