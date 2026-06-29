from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    bank_service_url: str
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = Field(default=5672, ge=1, le=65535)
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = "/"
    rabbitmq_exchange: str = "payment.events"
    rabbitmq_payment_requested_queue: str = "orchestrator.payment-requested.q"
    rabbitmq_payment_requested_routing_key: str = "payment.requested.v1"
    rabbitmq_retry_exchange: str = "payment.retry"
    rabbitmq_payment_requested_retry_queue: str = (
        "orchestrator.payment-requested.retry.q"
    )
    rabbitmq_payment_requested_retry_routing_key: str = "payment.requested.retry"
    rabbitmq_dead_letter_exchange: str = "payment.dead-letter"
    rabbitmq_payment_requested_dead_letter_queue: str = (
        "orchestrator.payment-requested.dlq"
    )
    rabbitmq_payment_requested_dead_letter_routing_key: str = "payment.requested.failed"
    rabbitmq_retry_delay_ms: int = Field(default=5000, ge=100)
    rabbitmq_max_retries: int = Field(default=3, ge=0)
    rabbitmq_reconnect_delay_seconds: float = Field(default=2, ge=0.1)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
