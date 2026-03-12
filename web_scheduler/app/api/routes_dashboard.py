from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.dashboard import DashboardHtmlResultItem, DashboardJobItem, DashboardSummaryResponse
from app.services.dashboard_service import get_dashboard_html_results, get_dashboard_jobs, get_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = get_logger(__name__)


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary_api(request: Request, db: Session = Depends(get_db)) -> DashboardSummaryResponse:
    logger.info("request_id=%s dashboard_summary", getattr(request.state, "request_id", "-"))
    return get_dashboard_summary(db)


@router.get("/jobs", response_model=list[DashboardJobItem])
def dashboard_jobs_api(request: Request) -> list[DashboardJobItem]:
    logger.info("request_id=%s dashboard_jobs", getattr(request.state, "request_id", "-"))
    return [DashboardJobItem(**job) for job in get_dashboard_jobs()]


@router.get("/html-results", response_model=list[DashboardHtmlResultItem])
def dashboard_html_results_api(request: Request, db: Session = Depends(get_db)) -> list[DashboardHtmlResultItem]:
    logger.info("request_id=%s dashboard_html_results", getattr(request.state, "request_id", "-"))
    return get_dashboard_html_results(db)
