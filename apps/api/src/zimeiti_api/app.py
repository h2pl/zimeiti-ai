"""FastAPI 应用工厂（Task 1.4）。"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Zimeiti AI API")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app
