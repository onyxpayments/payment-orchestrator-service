import logging
import httpx
from config.settings import settings

logger = logging.getLogger(__name__)


class MockBankGateway:
    def authorize(self, request):
        response = httpx.post(
            f"{settings.bank_service_url}/authorize",
            json=request.model_dump(),
            timeout=5,
        )

        response.raise_for_status()
        body = response.json()

        logger.info("Mock bank response: %s", body)

        return body
