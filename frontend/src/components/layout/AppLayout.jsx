import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ListTodo,
  FolderKanban,
  Bell,
  UserRound,
  LogOut
} from "lucide-react";

import { logoutUser } from "../../services/authService.js";
import "../../pages/Dashboard.css";

const navigation = [
  { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { path: "/tasks", label: "Mis tareas", icon: ListTodo },
  { path: "/lists", label: "Mis listas", icon: FolderKanban },
  { path: "/notifications", label: "Notificaciones", icon: Bell },
  { path: "/profile", label: "Mi perfil", icon: UserRound }
];

function AppLayout() {
  const navigate = useNavigate();

  function handleLogout() {
    logoutUser();
    navigate("/login", { replace: true });
  }

  return (
    <div className="dashboard-layout">
      <aside className="dashboard-sidebar">
        <div className="dashboard-brand">
          <strong>TaskFlow</strong>
          <span>FACTORÍA F5</span>
        </div>

        <nav aria-label="Navegación principal">
          {navigation.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                `dashboard-nav-link ${isActive ? "active" : ""}`
              }
            >
              <Icon size={19} />
              {label}
            </NavLink>
          ))}
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