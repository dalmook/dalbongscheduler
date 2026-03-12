import { useEffect, useState } from "react";
import { fetchDashboardHtmlResults, fetchDashboardJobs, fetchDashboardSummary } from "../api/dashboard";
import HtmlPreviewPanel from "../components/artifacts/HtmlPreviewPanel";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import Loading from "../components/common/Loading";
import HtmlResultCards from "../components/dashboard/HtmlResultCards";
import JobsTable from "../components/dashboard/JobsTable";
import RecentFailedRuns from "../components/dashboard/RecentFailedRuns";
import SummaryCards from "../components/dashboard/SummaryCards";
import type { DashboardHtmlResult, DashboardJob, DashboardSummary } from "../types/dashboard";

function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [jobs, setJobs] = useState<DashboardJob[]>([]);
  const [htmlResults, setHtmlResults] = useState<DashboardHtmlResult[]>([]);
  const [selectedArtifactId, setSelectedArtifactId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchDashboardSummary(), fetchDashboardJobs(), fetchDashboardHtmlResults()])
      .then(([summaryRes, jobsRes, htmlRes]) => {
        setSummary(summaryRes);
        setJobs(jobsRes);
        setHtmlResults(htmlRes);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;
  if (!summary) return <EmptyState />;

  return (
    <div className="page-grid">
      <h1>Dashboard</h1>
      <SummaryCards summary={summary} />
      <h2>Scheduler Jobs</h2>
      {jobs.length ? <JobsTable jobs={jobs} /> : <EmptyState message="No jobs registered" />}
      <RecentFailedRuns summary={summary} />
      <h2>Latest HTML Results</h2>
      {htmlResults.length ? (
        <>
          <HtmlResultCards rows={htmlResults} onPreview={setSelectedArtifactId} />
          <HtmlPreviewPanel artifactId={selectedArtifactId} />
        </>
      ) : (
        <EmptyState message="No HTML task results" />
      )}
    </div>
  );
}

export default DashboardPage;
