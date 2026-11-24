import { useCallback, useEffect, useState } from "react";
import {
  FolderKanban,
  Plus,
  Pencil,
  Trash2,
  LockKeyhole,
  Users,
  X,
  RefreshCw
} from "lucide-react";

import {
  getLists,
  createList,
  updateList,
  deleteList
} from "../services/listService.js";

import "./Lists.css";

const emptyForm = {
  name: "",
  description: "",
  visibility: "private"
};

function getErrorMessage(error) {
  const detail = error.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (error.response?.status === 401) {
    return "Tu sesión ha caducado. Inicia sesión nuevamente.";
  }

  if (error.response?.status === 422) {
    return "Revisa los datos del formulario.";
  }

  return "No se pudo completar la operación. Inténtalo de nuevo.";
}

function Lists() {
  const [lists, setLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(emptyForm);

  const loadLists = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getLists();
      setLists(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLists();
  }, [loadLists]);

  function openCreateForm() {
    setForm({ ...emptyForm });
    setEditingId(null);
    setError("");
    setSuccess("");
    setShowForm(true);
  }

  function openEditForm(list) {
    setForm({
      name: list.name,
      description: list.description || "",
      visibility: list.visibility
    });

    setEditingId(list.id);
    setError("");
    setSuccess("");
    setShowForm(true);
  }

  function closeForm() {
    if (saving) return;

    setShowForm(false);
    setEditingId(null);
    setForm({ ...emptyForm });
  }

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const name = form.name.trim();

    if (!name || name.length > 100) {
      setError("El nombre debe tener entre 1 y 100 caracteres.");
      return;
    }

    setSaving(true);
    setError("");
    setSuccess("");

    const payload = {
      name,
      description: form.description.trim() || null,
      visibility: form.visibility
    };

    try {
      if (editingId !== null) {
        await updateList(editingId, payload);
        setSuccess("Lista actualizada correctamente.");
      } else {
        await createList(payload);
        setSuccess("Lista creada correctamente.");
      }

      setShowForm(false);
      setEditingId(null);
      setForm({ ...emptyForm });

      await loadLists();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(list) {
    const confirmed = window.confirm(
      `¿Seguro que deseas eliminar "${list.name}"? ` +
      "También podrían eliminarse sus tareas asociadas."
    );

    if (!confirmed) return;

    setError("");
    setSuccess("");

    try {
      await deleteList(list.id);
      setSuccess("Lista eliminada correctamente.");
      await loadLists();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  const privateCount = lists.filter(
    (list) => list.visibility === "private"
  ).length;

  const sharedCount = lists.filter(
    (list) => list.visibility === "shared"
  ).length;

  return (
    <main className="lists-page">
      <header className="lists-header">
        <div>
          <span className="lists-eyebrow">
            TASKFLOW · FACTORÍA F5
          </span>
          <h1>Mis listas</h1>
          <p>
            Organiza tus tareas y colabora en tus proyectos.
          </p>
        </div>

        <button
          type="button"
          className="lists-create-button"
          onClick={openCreateForm}
        >
          <Plus size={18} />
          Nueva lista
        </button>
      </header>

      <section className="lists-summary">
        <article>
          <FolderKanban size={22} />
          <span>Total de listas</span>
          <strong>{lists.length}</strong>
        </article>

        <article>
          <LockKeyhole size={22} />
          <span>Listas privadas</span>
          <strong>{privateCount}</strong>
        </article>

        <article>
          <Users size={22} />
          <span>Listas compartidas</span>
          <strong>{sharedCount}</strong>
        </article>
      </section>

      {error && (
        <p className="lists-error" role="alert">{error}</p>
      )}

      {success && (
        <p className="lists-success" role="status">
          {success}
        </p>
      )}

      <section className="lists-content">
        <div className="lists-section-heading">
          <h2>Tus listas de trabajo</h2>

          <button
            type="button"
            onClick={loadLists}
            className="lists-refresh-button"
            disabled={loading}
          >
            <RefreshCw size={17} />
            Actualizar
          </button>
        </div>

        {loading ? (
          <div className="lists-empty">
            Cargando tus listas...
          </div>
        ) : lists.length === 0 ? (
          <div className="lists-empty">
            <FolderKanban size={44} />
            <h3>Todavía no tienes listas</h3>
            <p>
              Crea tu primera lista para empezar a organizar
              las tareas de TaskFlow.
            </p>
            <button
              type="button"
              className="lists-create-button"
              onClick={openCreateForm}
            >
              <Plus size={18} />
              Crear primera lista
            </button>
          </div>
        ) : (
          <div className="lists-grid">
            {lists.map((list) => (
              <article className="lists-card" key={list.id}>
                <div className="lists-card-top">
                  <div className="lists-card-icon">
                    {list.visibility === "shared"
                      ? <Users size={23} />
                      : <FolderKanban size={23} />}
                  </div>

                  <span
                    className={
                      list.visibility === "shared"
                        ? "lists-badge shared"
                        : "lists-badge"
                    }
                  >
                    {list.visibility === "shared"
                      ? "Compartida"
                      : "Privada"}
                  </span>
                </div>

                <h3>{list.name}</h3>

                <p className="lists-description">
                  {list.description ||
                    "Esta lista no tiene descripción."}
                </p>

                <div className="lists-card-footer">
                  <span>
                    Creada el{" "}
                    {new Date(list.created_at).toLocaleDateString(
                      "es-ES"
                    )}
                  </span>

                  <div className="lists-card-actions">
                    <button
                      type="button"
                      title="Editar lista"
                      aria-label={`Editar ${list.name}`}
                      onClick={() => openEditForm(list)}
                    >
                      <Pencil size={17} />
                    </button>

                    <button
                      type="button"
                      title="Eliminar lista"
                      aria-label={`Eliminar ${list.name}`}
                      onClick={() => handleDelete(list)}
                    >
                      <Trash2 size={17} />
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {showForm && (
        <div className="lists-modal-backdrop">
          <section
            className="lists-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="lists-modal-title"
          >
            <div className="lists-modal-heading">
              <h2 id="lists-modal-title">
                {editingId !== null
                  ? "Editar lista"
                  : "Nueva lista"}
              </h2>

              <button
                type="button"
                onClick={closeForm}
                aria-label="Cerrar formulario"
                disabled={saving}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <label htmlFor="list-name">
                Nombre de la lista
              </label>
              <input
                id="list-name"
                name="name"
                value={form.name}
                onChange={handleChange}
                maxLength={100}
                required
                placeholder="Ej. Proyecto TaskFlow"
              />

              <label htmlFor="list-description">
                Descripción
              </label>
              <textarea
                id="list-description"
                name="description"
                value={form.description}
                onChange={handleChange}
                rows={4}
                placeholder="Describe el propósito de la lista"
              />

              <label htmlFor="list-visibility">
                Visibilidad
              </label>
              <select
                id="list-visibility"
                name="visibility"
                value={form.visibility}
                onChange={handleChange}
              >
                <option value="private">Privada</option>
                <option value="shared">Compartida</option>
              </select>

              <div className="lists-form-actions">
                <button
                  type="button"
                  className="lists-cancel-button"
                  onClick={closeForm}
                  disabled={saving}
                >
                  Cancelar
                </button>

                <button
                  type="submit"
                  className="lists-create-button"
                  disabled={saving}
                >
                  {saving
                    ? "Guardando..."
                    : editingId !== null
                      ? "Guardar cambios"
                      : "Crear lista"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}

export default Lists;