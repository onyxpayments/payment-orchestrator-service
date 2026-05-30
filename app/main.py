from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="OnyxPay Payment Orchestrator Service")

app.include_router(router)
