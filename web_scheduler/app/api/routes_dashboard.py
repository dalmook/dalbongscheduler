from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardHtmlResultItem, DashboardJobItem, DashboardSummaryResponse
from app.services.dashboard_service import get_dashboard_html_results, get_dashboard_jobs, get_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary_api(db: Session = Depends(get_db)) -> DashboardSummaryResponse:
    return get_dashboard_summary(db)


@router.get("/jobs", response_model=list[DashboardJobItem])
def dashboard_jobs_api() -> list[DashboardJobItem]:
    return [DashboardJobItem(**job) for job in get_dashboard_jobs()]


@router.get("/html-results", response_model=list[DashboardHtmlResultItem])
def dashboard_html_results_api(db: Session = Depends(get_db)) -> list[DashboardHtmlResultItem]:
    return get_dashboard_html_results(db)
