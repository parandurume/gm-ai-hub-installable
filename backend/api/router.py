"""전체 API 라우터 등록."""

from __future__ import annotations

from fastapi import FastAPI


def register_routes(app: FastAPI) -> None:
    """모든 API 라우터를 앱에 등록."""
    from backend.api.health import router as health_router
    from backend.api.setup_wizard import router as setup_router

    app.include_router(health_router)
    app.include_router(setup_router)

    # Phase 2에서 추가되는 라우터들
    try:
        from backend.api.documents import router as documents_router
        app.include_router(documents_router)
    except ImportError:
        pass

    try:
        from backend.api.gianmun import router as gianmun_router
        app.include_router(gianmun_router)
    except ImportError:
        pass

    try:
        from backend.api.search import router as search_router
        app.include_router(search_router)
    except ImportError:
        pass

    try:
        from backend.api.chat import router as chat_router
        app.include_router(chat_router)
    except ImportError:
        pass

    try:
        from backend.api.meeting import router as meeting_router
        app.include_router(meeting_router)
    except ImportError:
        pass

    try:
        from backend.api.complaint import router as complaint_router
        app.include_router(complaint_router)
    except ImportError:
        pass

    try:
        from backend.api.regulation import router as regulation_router
        app.include_router(regulation_router)
    except ImportError:
        pass

    try:
        from backend.api.pii import router as pii_router
        app.include_router(pii_router)
    except ImportError:
        pass

    try:
        from backend.api.diff import router as diff_router
        app.include_router(diff_router)
    except ImportError:
        pass

    try:
        from backend.api.settings_api import router as settings_router
        app.include_router(settings_router)
    except ImportError:
        pass

    # v1.1 추가 라우터
    try:
        from backend.api.models import router as models_router
        app.include_router(models_router)
    except ImportError:
        pass

    try:
        from backend.api.optimize import router as optimize_router
        app.include_router(optimize_router)
    except ImportError:
        pass

    try:
        from backend.api.filesystem import router as filesystem_router
        app.include_router(filesystem_router)
    except ImportError:
        pass

    try:
        from backend.api.samples import router as samples_router
        app.include_router(samples_router)
    except ImportError:
        pass
