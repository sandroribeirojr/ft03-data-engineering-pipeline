
import logging
import time

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Optional

import requests

from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


logger = logging.getLogger(__name__)


class RetryableHTTPError(requests.RequestException):
    """Erro HTTP temporário que permite nova tentativa."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None
    ):
        super().__init__(message)
        self.retry_after = retry_after


class APIClient:
    """
    Cliente HTTP reutilizável para consumo de APIs REST.

    Recursos:
    - Timeout configurável.
    - Rate limiting.
    - Retentativas automáticas.
    - Tratamento de erros HTTP.
    - Logging das requisições.
    """

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit: float = 1.0
    ) -> None:

        if timeout <= 0:
            raise ValueError("Timeout deve ser maior que zero.")

        if max_retries < 1:
            raise ValueError("max_retries deve ser pelo menos 1.")

        if rate_limit < 0:
            raise ValueError("rate_limit não pode ser negativo.")

        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit = rate_limit

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": "FT03-DataEngineering-Pipeline/1.0",
            "Accept": "application/json"
        })

        self.last_request = 0.0

    def _apply_rate_limit(self) -> None:
        """Controla o intervalo entre requisições."""

        elapsed = time.monotonic() - self.last_request

        remaining = self.rate_limit - elapsed

        if remaining > 0:
            time.sleep(remaining)

        self.last_request = time.monotonic()

    @staticmethod
    def _get_retry_after(
        response: requests.Response
    ) -> Optional[float]:
        """Obtém o tempo de espera informado pelo servidor."""

        retry_after = response.headers.get("Retry-After")

        if not retry_after:
            return None

        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_date = parsedate_to_datetime(retry_after)

                if retry_date.tzinfo is None:
                    retry_date = retry_date.replace(
                        tzinfo=timezone.utc
                    )

                wait_seconds = (
                    retry_date - datetime.now(timezone.utc)
                ).total_seconds()

                return max(0.0, wait_seconds)

            except (TypeError, ValueError, OverflowError):
                return None

    def _wait_strategy(self, retry_state) -> float:
        """Define espera exponencial ou Retry-After."""

        error = retry_state.outcome.exception()

        if isinstance(error, RetryableHTTPError):
            if error.retry_after is not None:
                return error.retry_after

        return wait_exponential(
            multiplier=1,
            min=2,
            max=10
        )(retry_state)

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None
    ) -> requests.Response:

        self._apply_rate_limit()

        response = self.session.request(
            method=method,
            url=url,
            params=params,
            timeout=self.timeout
        )

        if response.status_code == 429:
            raise RetryableHTTPError(
                "Limite de requisições atingido (HTTP 429).",
                retry_after=self._get_retry_after(response)
            )

        if response.status_code >= 500:
            raise RetryableHTTPError(
                f"Erro temporário no servidor: HTTP {response.status_code}"
            )

        response.raise_for_status()

        return response

    def get(
        self,
        url: str,
        params: Optional[dict] = None
    ) -> Any:
        """Executa GET com retentativas automáticas."""

        logger.info("Iniciando requisição GET: %s", url)

        retrying = Retrying(
            stop=stop_after_attempt(self.max_retries),
            wait=self._wait_strategy,
            retry=retry_if_exception_type((
                requests.ConnectionError,
                requests.Timeout,
                RetryableHTTPError
            )),
            reraise=True
        )

        response = retrying(
            self._request,
            "GET",
            url,
            params
        )

        try:
            data = response.json()

        except ValueError as error:
            logger.error(
                "Resposta não contém JSON válido: %s",
                url
            )
            raise ValueError(
                f"JSON inválido recebido da API: {url}"
            ) from error

        logger.info(
            "Requisição concluída com sucesso: %s",
            url
        )

        return data

    def close(self) -> None:
        """Encerra a sessão HTTP."""

        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()