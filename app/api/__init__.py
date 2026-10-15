# RuleRadar AI - API Package Init
from app.api.routes_documents import router as documents_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_compare import router as compare_router
from app.api.routes_qa import router as qa_router
from app.api.routes_export import router as export_router
from app.api.routes_system import router as system_router

__all__ = [
    "documents_router",
    "analysis_router",
    "compare_router",
    "qa_router",
    "export_router",
    "system_router"
]
