from fastapi import FastAPI

from app.api.router import dashboard_router, router

app = FastAPI(title="Meerkat Backend", version="0.1.0")
app.include_router(router)
app.include_router(dashboard_router)
