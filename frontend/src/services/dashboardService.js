import api from "./api.js";

// Obtener tareas agrupadas por estado
export async function getTasksByStatus() {
  const response = await api.get(
    "/api/dashboard/tasks-by-status"
  );
  return response.data;
}

// Obtener tareas agrupadas por lista
export async function getTasksByList() {
  const response = await api.get(
    "/api/dashboard/tasks-by-list"
  );
  return response.data;
}

// Obtener estadísticas semanales
export async function getWeeklyStatistics(weeks = 4) {
  const response = await api.get(
    "/api/dashboard/weekly",
    { params: { weeks } }
  );
  return response.data;
}

// Obtener actividad reciente
export async function getRecentActivity(limit = 10) {
  const response = await api.get(
    "/api/dashboard/recent-activity",
    { params: { limit } }
  );
  return response.data;
}

// Obtener las tareas del usuario
export async function getMyTasks() {
  const response = await api.get("/api/tasks");
  return response.data;
}