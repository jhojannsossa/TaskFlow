import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";

import {
  LayoutDashboard,
  ListTodo,
  FolderKanban,
  Bell,
  UserRound,
  LogOut,
} from "lucide-react";

import { logoutUser } from "../../services/authService.js";
import { getNotifications } from "../../services/notificationService.js";

import "../../pages/Dashboard.css";

// Opciones de navegación del menú lateral.
const navigation = [
  {
    path: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
  {
    path: "/tasks",
    label: "Mis tareas",
    icon: ListTodo,
  },
  {
    path: "/lists",
    label: "Mis listas",
    icon: FolderKanban,
  },
  {
    path: "/notifications",
    label: "Notificaciones",
    icon: Bell,
  },
  {
    path: "/profile",
    label: "Mi perfil",
    icon: UserRound,
  },
];

function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  // Número de notificaciones pendientes.
  const [unreadCount, setUnreadCount] = useState(0);

  // Consultar las notificaciones del usuario autenticado.
  const loadUnreadCount = useCallback(async () => {
    try {
      const notifications = await getNotifications();

      const count = notifications.filter(
        (notification) => !notification.is_read
      ).length;

      setUnreadCount(count);
    } catch (error) {
      console.error(
        "No se pudo consultar el contador de notificaciones:",
        error
      );
    }
  }, []);

  // Actualizar el contador automáticamente y
  // cuando la página de notificaciones emita un evento.
  useEffect(() => {
    loadUnreadCount();

    const handleNotificationsUpdated = () => {
      loadUnreadCount();
    };

    window.addEventListener(
      "taskflow:notifications-updated",
      handleNotificationsUpdated
    );

    // Consultar nuevas notificaciones cada 30 segundos.
    const intervalId = setInterval(() => {
      loadUnreadCount();
    }, 30000);

    // Limpiar eventos e intervalo al desmontar.
    return () => {
      clearInterval(intervalId);

      window.removeEventListener(
        "taskflow:notifications-updated",
        handleNotificationsUpdated
      );
    };
  }, [loadUnreadCount]);

  // Actualizar el contador al cambiar de página.
  useEffect(() => {
    loadUnreadCount();
  }, [location.pathname, loadUnreadCount]);

  // Cerrar sesión y regresar al login.
  function handleLogout() {
    logoutUser();

    setUnreadCount(0);

    navigate("/login", {
      replace: true,
    });
  }

  return (
    <div className="dashboard-layout">
      <aside className="dashboard-sidebar">
        <div className="dashboard-brand">
          <strong>TaskFlow</strong>
          <span>FACTORÍA F5</span>
        </div>

        <nav aria-label="Navegación principal">
          {navigation.map(
            ({ path, label, icon: Icon }) => (
              <NavLink
                key={path}
                to={path}
                className={({ isActive }) =>
                  `dashboard-nav-link ${
                    isActive ? "active" : ""
                  }`
                }
              >
                <Icon size={19} />

                <span>{label}</span>

                {path === "/notifications" &&
                  unreadCount > 0 && (
                    <span
                      className="dashboard-notification-badge"
                      aria-label={`${unreadCount} notificaciones sin leer`}
                    >
                      {unreadCount > 99
                        ? "99+"
                        : unreadCount}
                    </span>
                  )}
              </NavLink>
            )
          )}
        </nav>

        <button
          type="button"
          className="dashboard-logout"
          onClick={handleLogout}
        >
          <LogOut size={19} />
          Cerrar sesión
        </button>
      </aside>

      <main className="dashboard-main">
        <Outlet />
      </main>
    </div>
  );
}

export default AppLayout;