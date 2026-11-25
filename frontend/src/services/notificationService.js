import api from "./api.js";

// Obtener las notificaciones del usuario autenticado
export async function getNotifications() {
  const response = await api.get("/api/notifications");
  return response.data;
}

// Marcar una notificación como leída
export async function markNotificationAsRead(notificationId) {
  const response = await api.patch(
    `/api/notifications/${notificationId}/read`
  );
  return response.data;
}

// Marcar todas las notificaciones como leídas
export async function markAllNotificationsAsRead() {
  const response = await api.patch("/api/notifications/read-all");
  return response.data;
}

// Consultar las preferencias de notificaciones
export async function getNotificationPreferences() {
  const response = await api.get("/api/notifications/preferences");
  return response.data;
}

// Actualizar las preferencias de notificaciones
export async function updateNotificationPreferences(preferences) {
  const response = await api.patch(
    "/api/notifications/preferences",
    preferences
  );
  return response.data;
}