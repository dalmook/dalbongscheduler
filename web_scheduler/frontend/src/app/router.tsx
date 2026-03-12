import { createBrowserRouter } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import DashboardPage from "../pages/DashboardPage";
import HtmlResultsPage from "../pages/HtmlResultsPage";
import RunsPage from "../pages/RunsPage";
import TaskDetailPage from "../pages/TaskDetailPage";
import TasksPage from "../pages/TasksPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "tasks", element: <TasksPage /> },
      { path: "tasks/:taskId", element: <TaskDetailPage /> },
      { path: "runs", element: <RunsPage /> },
      { path: "html-results", element: <HtmlResultsPage /> },
    ],
  },
]);
