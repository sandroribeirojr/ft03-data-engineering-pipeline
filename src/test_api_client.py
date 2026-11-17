
import os

from dotenv import load_dotenv

from src.extraction.api_client import APIClient


def test_rest_countries():

    load_dotenv()

    api_key = os.getenv("REST_COUNTRIES_API_KEY")

    if not api_key:
        raise ValueError(
            "REST_COUNTRIES_API_KEY não encontrada no arquivo .env"
        )

    url = (
        "https://api.restcountries.com/"
        "countries/v5/names.common/Brazil"
    )

    params = {
        "response_fields": (
            "names.common,codes.alpha_3,capitals,"
            "population,region,languages,currencies"
        )
    }

    try:

        with APIClient(
            timeout=30,
            max_retries=3,
            rate_limit=1
        ) as client:

            client.session.headers.update({
                "Authorization": f"Bearer {api_key}"
            })

            response = client.get(
                url,
                params=params
            )

        print("\nAPI REST Countries v5 acessada!")

        print("\nTipo de resposta:")
        print(type(response))

        if not isinstance(response, dict):
            raise ValueError("Formato JSON inesperado.")

        if response.get("errors"):
            raise ValueError(
                f"Erro retornado pela API: {response['errors']}"
            )

        data = response.get("data", {})
        countries = data.get("objects", [])

        if not countries:
            raise ValueError(
                "Nenhum país foi encontrado na resposta."
            )

        nomes = [
            country.get("names", {}).get("common")
            for country in countries
        ]

        if "Brazil" not in nomes:
            raise ValueError(
            f"Esperávamos Brazil, mas recebemos: {nomes}"
        )

        for country in countries:

            print("\n-------------------------")

            print(
                "País:",
                country.get("names", {}).get("common")
            )

            print(
                "Código:",
                country.get("codes", {}).get("alpha_3")
            )

            print(
                "Capital:",
                country.get("capitals")
            )

            print(
                "Região:",
                country.get("region")
            )

            print(
                "População:",
                country.get("population")
            )

            print(
                "Idiomas:",
                country.get("languages")
            )

            print(
                "Moedas:",
                country.get("currencies")
            )

    except Exception as error:

        print("\nFalha no teste:")
        print(type(error).__name__)
        print(error)

        raise


if __name__ == "__main__":
    test_rest_countries()
