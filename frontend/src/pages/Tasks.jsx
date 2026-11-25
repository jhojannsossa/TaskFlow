import { useCallback, useEffect, useState } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  X,
  RefreshCw,
  ClipboardList
} from "lucide-react";

import {
  getTasks,
  createTask,
  updateTask,
  deleteTask
} from "../services/taskService.js";

import {
  getLists,
  getListMembers
} from "../services/listService.js";

import { getCurrentUser } from "../services/authService.js";

import "./Tasks.css";

const initialForm = {
  title: "",
  description: "",
  list_id: "",
  status: "todo",
  priority: "medium",
  due_date: ""
};

const statusLabels = {
  todo: "Por hacer",
  in_progress: "En progreso",
  done: "Hecha"
};

const priorityLabels = {
  low: "Baja",
  medium: "Media",
  high: "Alta",
  urgent: "Urgente"
};

function getErrorMessage(error) {
  const detail = error.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (error.response?.status === 403) {
    return "No tienes permisos para modificar esta tarea.";
  }

  if (error.response?.status === 422) {
    return "Revisa los datos del formulario.";
  }

  return "No se pudo completar la operación.";
}

function Tasks() {
  const [tasks, setTasks] = useState([]);
  const [lists, setLists] = useState([]);
  const [editableListIds, setEditableListIds] = useState([]);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);

  const [filter, setFilter] = useState("all");
  const [form, setForm] = useState({ ...initialForm });

  // Cargar tareas, listas y permisos del usuario.
  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      // No conceder permisos mientras se recargan.
      setEditableListIds([]);

      const [tasksData, listsData, user] = await Promise.all([
        getTasks(),
        getLists(),
        getCurrentUser()
      ]);

      // Comprobar el rol del usuario en cada lista.
      const roleChecks = await Promise.allSettled(
        listsData.map(async (list) => {
          // El propietario puede editar su lista.
          if (Number(list.owner_id) === Number(user.id)) {
            return Number(list.id);
          }

          // Consultar colaboradores de la lista.
          const members = await getListMembers(list.id);

          const myMembership = members.find(
            (member) =>
              Number(member.user_id) === Number(user.id)
          );

          // Solo el Editor puede modificar tareas.
          return myMembership?.role === "editor"
            ? Number(list.id)
            : null;
        })
      );

      const permittedListIds = roleChecks
        .filter(
          (result) =>
            result.status === "fulfilled" &&
            result.value !== null
        )
        .map((result) => result.value);

      setEditableListIds(permittedListIds);
      setTasks(tasksData);
      setLists(listsData);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Comprobar si el usuario puede editar una lista.
  function canEditList(listId) {
    return editableListIds.includes(Number(listId));
  }

  // Listas donde el usuario puede crear tareas.
  const editableLists = lists.filter(
    (list) => canEditList(list.id)
  );

  // Abrir formulario para crear una tarea.
  function openCreate() {
    if (editableLists.length === 0) {
      return;
    }

    setEditingId(null);

    setForm({
      ...initialForm,
      list_id: editableLists[0]?.id?.toString() || ""
    });

    setError("");
    setSuccess("");
    setShowForm(true);
  }

  // Abrir formulario para editar una tarea.
  function openEdit(task) {
    if (!canEditList(task.list_id)) {
      return;
    }

    setEditingId(task.id);

    setForm({
      title: task.title,
      description: task.description || "",
      list_id: String(task.list_id),
      status: task.status,
      priority: task.priority,
      due_date: task.due_date
        ? task.due_date.slice(0, 10)
        : ""
    });

    setError("");
    setSuccess("");
    setShowForm(true);
  }

  // Cerrar formulario.
  function closeForm() {
    if (saving) {
      return;
    }

    setShowForm(false);
    setEditingId(null);
  }

  // Actualizar campos del formulario.
  function handleChange(event) {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value
    }));
  }

  // Crear o actualizar una tarea.
  async function handleSubmit(event) {
    event.preventDefault();

    const editingTask =
      editingId === null
        ? null
        : tasks.find((task) => task.id === editingId);

    const targetListId =
      editingTask?.list_id ?? form.list_id;

    // Impedir modificaciones desde el frontend.
    if (!canEditList(targetListId)) {
      setError(
        "No tienes permisos para modificar tareas en esta lista."
      );
      return;
    }

    if (!form.title.trim()) {
      setError("Debes escribir un título.");
      return;
    }

    if (editingId === null && !form.list_id) {
      setError("Debes seleccionar una lista.");
      return;
    }

    const payload = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      status: form.status,
      priority: form.priority,
      due_date: form.due_date
        ? `${form.due_date}T12:00:00`
        : null
    };

    if (editingId === null) {
      payload.list_id = Number(form.list_id);
      payload.assigned_to = null;
    }

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      if (editingId !== null) {
        await updateTask(editingId, payload);

        setSuccess(
          "Tarea actualizada correctamente."
        );
      } else {
        await createTask(payload);

        setSuccess(
          "Tarea creada correctamente."
        );
      }

      setShowForm(false);
      setEditingId(null);

      await loadData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  // Eliminar una tarea.
  async function handleDelete(task) {
    if (!canEditList(task.list_id)) {
      return;
    }

    const confirmed = window.confirm(
      `¿Quieres eliminar la tarea "${task.title}"?`
    );

    if (!confirmed) {
      return;
    }

    setError("");
    setSuccess("");

    try {
      await deleteTask(task.id);

      setSuccess(
        "Tarea eliminada correctamente."
      );

      await loadData();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  // Cambiar el estado de una tarea.
  async function changeStatus(task, newStatus) {
    if (!canEditList(task.list_id)) {
      return;
    }

    if (task.status === newStatus) {
      return;
    }

    setError("");
    setSuccess("");

    try {
      await updateTask(task.id, {
        status: newStatus
      });

      setSuccess(
        "Estado actualizado correctamente."
      );

      await loadData();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  // Contadores de tareas.
  const counts = {
    todo: tasks.filter(
      (task) => task.status === "todo"
    ).length,

    in_progress: tasks.filter(
      (task) => task.status === "in_progress"
    ).length,

    done: tasks.filter(
      (task) => task.status === "done"
    ).length
  };

  // Filtrar tareas por estado.
  const visibleTasks = tasks.filter(
    (task) =>
      filter === "all" ||
      task.status === filter
  );

  // Obtener nombre de la lista.
  function getListName(listId) {
    return (
      lists.find(
        (list) => Number(list.id) === Number(listId)
      )?.name || "Lista no disponible"
    );
  }

  return (
    <div className="tasks-page">

      {/* ENCABEZADO */}
      <header className="tasks-header">
        <div>
          <span className="tasks-eyebrow">
            TASKFLOW · FACTORÍA F5
          </span>

          <h1>Mis tareas</h1>

          <p>
            Organiza y realiza el seguimiento de tus tareas.
          </p>
        </div>

        {/* Solo mostrar si puede crear tareas */}
        {editableLists.length > 0 && (
          <button
            type="button"
            className="tasks-primary-button"
            onClick={openCreate}
            disabled={loading}
          >
            <Plus size={18} />
            Nueva tarea
          </button>
        )}
      </header>

      {/* RESUMEN DE TAREAS */}
      <section className="tasks-summary">

        <article>
          <ClipboardList size={22} />
          <span>Por hacer</span>
          <strong>{counts.todo}</strong>
        </article>

        <article>
          <ClipboardList size={22} />
          <span>En progreso</span>
          <strong>{counts.in_progress}</strong>
        </article>

        <article>
          <ClipboardList size={22} />
          <span>Hechas</span>
          <strong>{counts.done}</strong>
        </article>

      </section>

      {/* MENSAJES */}
      {error && (
        <p
          className="tasks-error"
          role="alert"
        >
          {error}
        </p>
      )}

      {success && (
        <p
          className="tasks-success"
          role="status"
        >
          {success}
        </p>
      )}

      {/* CONTENIDO */}
      <section className="tasks-content">

        <div className="tasks-toolbar">
          <h2>Listado de tareas</h2>

          <div className="tasks-toolbar-actions">

            <select
              aria-label="Filtrar tareas por estado"
              value={filter}
              onChange={(event) =>
                setFilter(event.target.value)
              }
            >
              <option value="all">
                Todos los estados
              </option>

              <option value="todo">
                Por hacer
              </option>

              <option value="in_progress">
                En progreso
              </option>

              <option value="done">
                Hechas
              </option>
            </select>

            <button
              type="button"
              onClick={loadData}
              disabled={loading}
              className="tasks-refresh"
            >
              <RefreshCw size={17} />
              Actualizar
            </button>

          </div>
        </div>

        {/* ESTADOS DE CARGA */}
        {loading ? (
          <div className="tasks-empty">
            Cargando tareas...
          </div>
        ) : lists.length === 0 ? (
          <div className="tasks-empty">
            Primero debes crear una lista en Mis listas.
          </div>
        ) : visibleTasks.length === 0 ? (
          <div className="tasks-empty">
            <ClipboardList size={42} />

            <h3>No hay tareas para mostrar</h3>

            <p>
              {editableLists.length > 0
                ? "Crea tu primera tarea o cambia el filtro."
                : "No hay tareas para mostrar con este filtro."}
            </p>
          </div>
        ) : (

          /* TARJETAS DE TAREAS */
          <div className="tasks-grid">

            {visibleTasks.map((task) => (

              <article
                className="tasks-card"
                key={task.id}
              >

                <div className="tasks-card-top">

                  <span
                    className={`tasks-status ${task.status}`}
                  >
                    {statusLabels[task.status]}
                  </span>

                  <span
                    className={`tasks-priority ${task.priority}`}
                  >
                    {priorityLabels[task.priority]}
                  </span>

                </div>

                <h3>{task.title}</h3>

                <p className="tasks-description">
                  {task.description || "Sin descripción"}
                </p>

                <div className="tasks-meta">

                  <span>
                    Lista: {getListName(task.list_id)}
                  </span>

                  {task.due_date && (
                    <span>
                      Fecha límite:{" "}
                      {task.due_date.slice(0, 10)}
                    </span>
                  )}

                </div>

                {/* ACCIONES SEGÚN PERMISOS */}
                <div className="tasks-card-footer">

                  <select
                    aria-label={`Estado de ${task.title}`}
                    value={task.status}
                    disabled={!canEditList(task.list_id)}
                    onChange={(event) =>
                      changeStatus(
                        task,
                        event.target.value
                      )
                    }
                  >
                    <option value="todo">
                      Por hacer
                    </option>

                    <option value="in_progress">
                      En progreso
                    </option>

                    <option value="done">
                      Hecha
                    </option>
                  </select>

                  {/* Ocultar edición y eliminación al Lector */}
                  {canEditList(task.list_id) && (

                    <div className="tasks-card-actions">

                      <button
                        type="button"
                        title="Editar tarea"
                        aria-label={`Editar ${task.title}`}
                        onClick={() => openEdit(task)}
                      >
                        <Pencil size={17} />
                      </button>

                      <button
                        type="button"
                        title="Eliminar tarea"
                        aria-label={`Eliminar ${task.title}`}
                        onClick={() =>
                          handleDelete(task)
                        }
                      >
                        <Trash2 size={17} />
                      </button>

                    </div>

                  )}

                </div>

              </article>

            ))}

          </div>

        )}

      </section>

      {/* FORMULARIO MODAL */}
      {showForm && (

        <div className="tasks-modal-backdrop">

          <section
            className="tasks-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="tasks-modal-title"
          >

            <div className="tasks-modal-heading">

              <h2 id="tasks-modal-title">
                {editingId !== null
                  ? "Editar tarea"
                  : "Nueva tarea"}
              </h2>

              <button
                type="button"
                onClick={closeForm}
                disabled={saving}
                aria-label="Cerrar formulario"
              >
                <X size={20} />
              </button>

            </div>

            <form onSubmit={handleSubmit}>

              {/* TÍTULO */}
              <label htmlFor="task-title">
                Título
              </label>

              <input
                id="task-title"
                name="title"
                value={form.title}
                onChange={handleChange}
                maxLength={200}
                required
                placeholder="Ej. Diseñar página de inicio"
              />

              {/* DESCRIPCIÓN */}
              <label htmlFor="task-description">
                Descripción
              </label>

              <textarea
                id="task-description"
                name="description"
                value={form.description}
                onChange={handleChange}
                rows={3}
                placeholder="Describe la tarea"
              />

              {/* LISTA */}
              <label htmlFor="task-list">
                Lista
              </label>

              <select
                id="task-list"
                name="list_id"
                value={form.list_id}
                onChange={handleChange}
                disabled={editingId !== null}
                required
              >

                <option value="">
                  Selecciona una lista
                </option>

                {editableLists.map((list) => (

                  <option
                    key={list.id}
                    value={list.id}
                  >
                    {list.name}
                  </option>

                ))}

              </select>

              {/* ESTADO Y PRIORIDAD */}
              <div className="tasks-form-row">

                <div>
                  <label htmlFor="task-status">
                    Estado
                  </label>

                  <select
                    id="task-status"
                    name="status"
                    value={form.status}
                    onChange={handleChange}
                  >
                    <option value="todo">
                      Por hacer
                    </option>

                    <option value="in_progress">
                      En progreso
                    </option>

                    <option value="done">
                      Hecha
                    </option>
                  </select>
                </div>

                <div>
                  <label htmlFor="task-priority">
                    Prioridad
                  </label>

                  <select
                    id="task-priority"
                    name="priority"
                    value={form.priority}
                    onChange={handleChange}
                  >
                    <option value="low">
                      Baja
                    </option>

                    <option value="medium">
                      Media
                    </option>

                    <option value="high">
                      Alta
                    </option>

                    <option value="urgent">
                      Urgente
                    </option>
                  </select>
                </div>

              </div>

              {/* FECHA LÍMITE */}
              <label htmlFor="task-due-date">
                Fecha límite
              </label>

              <input
                id="task-due-date"
                type="date"
                name="due_date"
                value={form.due_date}
                onChange={handleChange}
              />

              {/* BOTONES DEL FORMULARIO */}
              <div className="tasks-form-actions">

                <button
                  type="button"
                  className="tasks-cancel-button"
                  onClick={closeForm}
                  disabled={saving}
                >
                  Cancelar
                </button>

                <button
                  type="submit"
                  className="tasks-primary-button"
                  disabled={saving}
                >
                  {saving
                    ? "Guardando..."
                    : editingId !== null
                      ? "Guardar cambios"
                      : "Crear tarea"}
                </button>

              </div>

            </form>

          </section>

        </div>

      )}

    </div>
  );
}

export default Tasks;