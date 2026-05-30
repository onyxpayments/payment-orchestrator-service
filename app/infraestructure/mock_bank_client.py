import httpx


class MockBankClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def authorize_payment(self, payload: dict) -> dict:
        response = httpx.post(f"{self.base_url}/authorize", json=payload, timeout=5)
        response.raise_for_status()
        return response.json()