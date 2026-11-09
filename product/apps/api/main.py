# Entry point

from fastapi import FastAPI
from product.apps.api.auth.router import router as auth_router

app = FastAPI(title="Family Health Assistant API")
app.include_router(auth_router)