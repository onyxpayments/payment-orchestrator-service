from fastapi import FastAPI

from adapters.inbound.http.routes import router

app = FastAPI(title="OnyxPay Payment Orchestrator Service")

app.include_router(router)
