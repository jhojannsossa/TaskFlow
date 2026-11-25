import { useCallback, useEffect, useState } from "react";
import {
  Bell,
  Check,
  CheckCheck,
  RefreshCw,
} from "lucide-react";

import {
  getNotifications,
  markNotificationAsRead,
  markAllNotificationsAsRead,
} from "../services/notificationService.js";

import "./Notifications.css";

function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [processingId, setProcessingId] = useState(null);
  const [processingAll, setProcessingAll] = useState(false);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getNotifications();
      setNotifications(data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "No se pudieron cargar las notificaciones."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  const unreadCount = notifications.filter(
    (notification) => !notification.is_read
  ).length;

  async function handleMarkAsRead(notificationId) {
    setProcessingId(notificationId);
    setError("");
    setSuccess("");

    try {
      await markNotificationAsRead(notificationId);

      setNotifications((previous) =>
        previous.map((notification) =>
          notification.id === notificationId
            ? { ...notification, is_read: true }
            : notification
        )
      );

      setSuccess("Notificación marcada como leída.");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "No se pudo actualizar la notificación."
      );
    } finally {
      setProcessingId(null);
    }
  }

  async function handleMarkAllAsRead() {
    setProcessingAll(true);
    setError("");
    setSuccess("");

    try {
      await markAllNotificationsAsRead();

      setNotifications((previous) =>
        previous.map((notification) => ({
          ...notification,
          is_read: true,
        }))
      );

      setSuccess("Todas las notificaciones se marcaron como leídas.");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "No se pudieron actualizar las notificaciones."
      );
    } finally {
      setProcessingAll(false);
    }
  }

  function formatDate(dateValue) {
    if (!dateValue) return "Fecha no disponible";

    const date = new Date(dateValue);

    if (Number.isNaN(date.getTime())) {
      return "Fecha no disponible";
    }

    return date.toLocaleString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <main className="notifications-page">
      <header className="notifications-header">
        <div>
          <span className="notifications-eyebrow">
            FACTORÍA F5 · TASKFLOW
          </span>
          <h1>Notificaciones</h1>
          <p>
            Mantente al día con la actividad de tus tareas
            y listas compartidas.
          </p>
        </div>

        <div className="notifications-header-icon">
          <Bell size={26} />
        </div>
      </header>

      <section className="notifications-content">
        <div className="notifications-toolbar">
          <div>
            <h2>Mis notificaciones</h2>
            <p>
              {unreadCount === 0
                ? "No tienes notificaciones pendientes."
                : `Tienes ${unreadCount} notificación(es) sin leer.`}
            </p>
          </div>

          <div className="notifications-actions">
            <button
              type="button"
              className="notifications-refresh"
              onClick={loadNotifications}
              disabled={loading}
            >
              <RefreshCw size={16} />
              Actualizar
            </button>

            <button
              type="button"
              className="notifications-primary-button"
              onClick={handleMarkAllAsRead}
              disabled={
                loading ||
                processingAll ||
                unreadCount === 0
              }
            >
              <CheckCheck size={16} />
              {processingAll
                ? "Actualizando..."
                : "Marcar todas como leídas"}
            </button>
          </div>
        </div>

        {error && (
          <div className="notifications-error" role="alert">
            {error}
          </div>
        )}

        {success && (
          <div className="notifications-success" role="status">
            {success}
          </div>
        )}

        {loading ? (
          <div className="notifications-empty">
            <RefreshCw size={28} />
            <p>Cargando notificaciones...</p>
          </div>
        ) : notifications.length === 0 ? (
          <div className="notifications-empty">
            <div className="notifications-empty-icon">
              <Bell size={30} />
            </div>
            <h3>Todo al día</h3>
            <p>
              Cuando tengas nuevas notificaciones,
              aparecerán aquí.
            </p>
          </div>
        ) : (
          <div className="notifications-list">
            {notifications.map((notification) => (
              <article
                key={notification.id}
                className={`notifications-card ${
                  notification.is_read
                    ? "notifications-card-read"
                    : "notifications-card-unread"
                }`}
              >
                <div className="notifications-card-icon">
                  <Bell size={20} />
                </div>

                <div className="notifications-card-content">
                  <p className="notifications-message">
                    {notification.message}
                  </p>

                  <span className="notifications-date">
                    {formatDate(notification.created_at)}
                  </span>

                  <span
                    className={`notifications-status ${
                      notification.is_read ? "read" : "unread"
                    }`}
                  >
                    {notification.is_read
                      ? "Leída"
                      : "Sin leer"}
                  </span>
                </div>

                {!notification.is_read && (
                  <button
                    type="button"
                    className="notifications-mark-button"
                    onClick={() =>
                      handleMarkAsRead(notification.id)
                    }
                    disabled={
                      processingId === notification.id ||
                      processingAll
                    }
                  >
                    <Check size={16} />
                    {processingId === notification.id
                      ? "Guardando..."
                      : "Marcar como leída"}
                  </button>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

export default Notifications;