import api from "./api.js";

export async function getTasks() {
  const response = await api.get("/api/tasks");
  return response.data;
}

export async function getTaskById(taskId) {
  const response = await api.get(`/api/tasks/${taskId}`);
  return response.data;
}

export async function createTask(taskData) {
  const response = await api.post("/api/tasks", taskData);
  return response.data;
}

export async function updateTask(taskId, taskData) {
  const response = await api.patch(
    `/api/tasks/${taskId}`,
    taskData
  );
  return response.data;
}

export async function deleteTask(taskId) {
  await api.delete(`/api/tasks/${taskId}`);
}