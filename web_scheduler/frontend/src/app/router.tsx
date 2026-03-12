import { createBrowserRouter } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import DashboardPage from "../pages/DashboardPage";
import TasksPage from "../pages/TasksPage";
import TaskDetailPage from "../pages/TaskDetailPage";
import RunsPage from "../pages/RunsPage";
import HtmlResultsPage from "../pages/HtmlResultsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "tasks", element: <TasksPage /> },
      { path: "tasks/:taskId", element: <TaskDetailPage /> },
      { path: "runs", element: <RunsPage /> },
      { path: "html-results", element: <HtmlResultsPage /> }
    ]
  }
]);
