from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .utils.logging import configure_logging
from .config import settings
from .api import auth as auth_router
from .api import bills as bills_router
from .api import negotiations as negotiations_router
from .api import dashboard as dashboard_router
from .api import admin as admin_router
from app.api import auth as auth_router

configure_logging()

app = FastAPI(title="Savings Automation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # <-- propiedad, no el campo pydantic
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router.router)
app.include_router(bills_router.router)
app.include_router(negotiations_router.router)
app.include_router(dashboard_router.router)
app.include_router(admin_router.router)
app.include_router(auth_router.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
