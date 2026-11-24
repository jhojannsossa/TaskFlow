import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis
} from "recharts";

import {
  getCurrentUser,
  logoutUser
} from "../services/authService.js";

import {
  getTasksByStatus,
  getTasksByList,
  getWeeklyStatistics,
  getRecentActivity
} from "../services/dashboardService.js";

import "./Dashboard.css";

const COLORS = ["#FF4700", "#FFA37F", "#202020"];

function Dashboard() {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [status, setStatus] = useState(null);
  const [lists, setLists] = useState([]);
  const [weekly, setWeekly] = useState([]);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      try {
        const results = await Promise.all([
          getCurrentUser(),
          getTasksByStatus(),
          getTasksByList(),
          getWeeklyStatistics(4),
          getRecentActivity(5)
        ]);

        if (!active) return;

        setUser(results[0]);
        setStatus(results[1]);
        setLists(results[2]);
        setWeekly(results[3]);
        setActivity(results[4]);
      } catch (err) {
        if (!active) return;

        if (err.response?.status === 401) {
          logoutUser();
          navigate("/login", { replace: true });
          return;
        }

        setError("No se pudieron cargar las estadísticas.");
      } finally {
        if (active) setLoading(false);
      }
    }

    loadDashboard();

    return () => {
      active = false;
    };
  }, [navigate]);

  const todo = status?.todo ?? 0;
  const progress = status?.in_progress ?? 0;
  const done = status?.done ?? 0;
  const total = todo + progress + done;

  const pieData = [
    { name: "Pendientes", value: todo },
    { name: "En progreso", value: progress },
    { name: "Completadas", value: done }
  ];

  const weeklyData = weekly.map((item) => ({
    week: item.week_start.slice(5),
    creadas: item.created,
    completadas: item.completed
  }));

  const listData = lists.map((item) => ({
    name: item.list_name,
    tareas: item.total_tasks
  }));

  const cards = [
    { label: "Total de tareas", value: total },
    { label: "Pendientes", value: todo },
    { label: "En progreso", value: progress },
    { label: "Completadas", value: done }
  ];

  return (
    <>
      <header className="dashboard-header">
        <div>
          <span className="dashboard-eyebrow">
            PANEL DE CONTROL
          </span>

          <h1>Dashboard</h1>

          <p>
            {user
              ? `¡Bienvenido, ${user.name}!`
              : "Tu espacio de trabajo"}
          </p>
        </div>

        <div
          className="dashboard-avatar"
          aria-hidden="true"
        >
          {user?.name?.charAt(0).toUpperCase() || "T"}
        </div>
      </header>

      {loading ? (
        <p role="status">Cargando estadísticas...</p>
      ) : error ? (
        <p className="auth-error" role="alert">
          {error}
        </p>
      ) : (
        <>
          <section
            className="dashboard-stats"
            aria-label="Resumen de tareas"
          >
            {cards.map((card) => (
              <article
                className="dashboard-stat-card"
                key={card.label}
              >
                <span>{card.label}</span>
                <strong>{card.value}</strong>
              </article>
            ))}
          </section>

          <section className="dashboard-charts">
            <article className="dashboard-panel">
              <h2>Distribución de tareas</h2>
              <p>Estado actual de tus tareas</p>

              {total === 0 ? (
                <div className="dashboard-empty">
                  Todavía no tienes tareas para mostrar.
                </div>
              ) : (
                <div className="dashboard-chart">
                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <PieChart>
                      <Pie
                        data={pieData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={60}
                        outerRadius={90}
                      >
                        {pieData.map((entry, index) => (
                          <Cell
                            key={entry.name}
                            fill={COLORS[index]}
                          />
                        ))}
                      </Pie>

                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </article>

            <article className="dashboard-panel">
              <h2>Actividad semanal</h2>
              <p>Tareas creadas y completadas</p>

              <div className="dashboard-chart">
                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <BarChart data={weeklyData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="week" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Legend />

                    <Bar
                      dataKey="creadas"
                      name="Creadas"
                      fill="#FF4700"
                      radius={[5, 5, 0, 0]}
                    />

                    <Bar
                      dataKey="completadas"
                      name="Completadas"
                      fill="#202020"
                      radius={[5, 5, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="dashboard-panel">
              <h2>Tareas por lista</h2>
              <p>Distribución entre tus listas</p>

              {listData.length === 0 ? (
                <div className="dashboard-empty">
                  Todavía no tienes listas.
                </div>
              ) : (
                <div className="dashboard-chart">
                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <BarChart
                      data={listData}
                      layout="vertical"
                      margin={{ left: 10, right: 15 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />

                      <XAxis
                        type="number"
                        allowDecimals={false}
                      />

                      <YAxis
                        dataKey="name"
                        type="category"
                        width={100}
                      />

                      <Tooltip />

                      <Bar
                        dataKey="tareas"
                        fill="#FF4700"
                        radius={[0, 5, 5, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </article>

            <article className="dashboard-panel">
              <h2>Actividad reciente</h2>
              <p>Últimos movimientos registrados</p>

              {activity.length === 0 ? (
                <div className="dashboard-empty">
                  Todavía no hay actividad reciente.
                </div>
              ) : (
                <ul className="dashboard-activity">
                  {activity.map((item) => (
                    <li key={item.id}>
                      <strong>
                        {item.details?.title || item.action}
                      </strong>

                      <span>
                        {new Date(
                          item.created_at
                        ).toLocaleString("es-ES")}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </article>
          </section>
        </>
      )}
    </>
  );
}

export default Dashboard;