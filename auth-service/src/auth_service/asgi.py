"""Entrypoint ASGI para producción.

Carga la configuración desde las variables de entorno y construye la app.
Uvicorn importará este archivo y buscará la variable `app`.
"""
from auth_service.config import load_config
from auth_service.main import build_app

config = load_config()
app = build_app(config)
