from fastapi import FastAPI

from app.adapters.inbound.http.health import router as health_router
from app.adapters.inbound.http.routes import router

app = FastAPI(title="OnyxPay Payment Orchestrator Service")

app.include_router(health_router)
app.include_router(router)
