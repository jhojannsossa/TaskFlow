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
  getCurrentUser,
  getUserByEmail
} from "../services/authService.js";

import {
  getLists,
  createList,
  updateList,
  deleteList,
  getListMembers,
  addListMember,
  updateListMember,
  deleteListMember
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

  if (error.response?.status === 403) {
    return "No tienes permisos para realizar esta acción.";
  }

  if (error.response?.status === 404) {
    return "No se encontró el recurso solicitado.";
  }

  if (error.response?.status === 422) {
    return "Revisa los datos del formulario.";
  }

  return "No se pudo completar la operación. Inténtalo de nuevo.";
}

function Lists() {
  const [lists, setLists] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({ ...emptyForm });

  // Estados para la gestión de colaboradores.
  const [selectedList, setSelectedList] = useState(null);
  const [members, setMembers] = useState([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [membersSaving, setMembersSaving] = useState(false);
  const [membersError, setMembersError] = useState("");
  const [membersSuccess, setMembersSuccess] = useState("");
  const [memberEmail, setMemberEmail] = useState("");
  const [memberRole, setMemberRole] = useState("editor");

  const loadLists = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [listsData, userData] = await Promise.all([
        getLists(),
        getCurrentUser()
      ]);

      setLists(listsData);
      setCurrentUser(userData);
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
      } else {
        await createList(payload);
      }

      setShowForm(false);
      setEditingId(null);
      setForm({ ...emptyForm });

      await loadLists();

      setSuccess(
        editingId !== null
          ? "Lista actualizada correctamente."
          : "Lista creada correctamente."
      );
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
      await loadLists();
      setSuccess("Lista eliminada correctamente.");
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  // Abrir la ventana de colaboradores.
  async function openMembersModal(list) {
    setSelectedList(list);
    setMembers([]);
    setMemberEmail("");
    setMemberRole("editor");
    setMembersError("");
    setMembersSuccess("");
    setMembersLoading(true);

    try {
      const data = await getListMembers(list.id);
      setMembers(data);
    } catch (err) {
      setMembersError(getErrorMessage(err));
    } finally {
      setMembersLoading(false);
    }
  }

  function closeMembersModal() {
    if (membersSaving) return;

    setSelectedList(null);
    setMembers([]);
    setMembersError("");
    setMembersSuccess("");
    setMemberEmail("");
    setMemberRole("editor");
  }

  // Buscar por correo y añadir un colaborador.
  async function handleAddMember(event) {
    event.preventDefault();

    if (!selectedList || membersSaving) return;

    const email = memberEmail.trim().toLowerCase();

    if (!email) {
      setMembersError("Introduce un correo electrónico.");
      return;
    }

    setMembersSaving(true);
    setMembersError("");
    setMembersSuccess("");

    try {
      const user = await getUserByEmail(email);

      if (user.id === currentUser?.id) {
        setMembersError(
          "Ya eres el propietario de esta lista."
        );
        return;
      }

      if (members.some((member) => member.user_id === user.id)) {
        setMembersError(
          "Este usuario ya pertenece a la lista."
        );
        return;
      }

      await addListMember(selectedList.id, {
        user_id: user.id,
        role: memberRole
      });

      const updatedMembers = await getListMembers(
        selectedList.id
      );

      setMembers(updatedMembers);
      setMemberEmail("");
      setMemberRole("editor");
      setMembersSuccess(
        "Colaborador añadido correctamente."
      );
    } catch (err) {
      setMembersError(getErrorMessage(err));
    } finally {
      setMembersSaving(false);
    }
  }

  // Cambiar los permisos de un miembro.
  async function handleUpdateMemberRole(userId, role) {
    if (!selectedList || membersSaving) return;

    setMembersSaving(true);
    setMembersError("");
    setMembersSuccess("");

    try {
      await updateListMember(
        selectedList.id,
        userId,
        { role }
      );

      const updatedMembers = await getListMembers(
        selectedList.id
      );

      setMembers(updatedMembers);
      setMembersSuccess(
        "Permisos actualizados correctamente."
      );
    } catch (err) {
      setMembersError(getErrorMessage(err));
    } finally {
      setMembersSaving(false);
    }
  }

  // Eliminar un colaborador.
  async function handleDeleteMember(userId) {
    if (!selectedList || membersSaving) return;

    const confirmed = window.confirm(
      `¿Deseas eliminar al usuario #${userId} ` +
      "de esta lista compartida?"
    );

    if (!confirmed) return;

    setMembersSaving(true);
    setMembersError("");
    setMembersSuccess("");

    try {
      await deleteListMember(selectedList.id, userId);

      const updatedMembers = await getListMembers(
        selectedList.id
      );

      setMembers(updatedMembers);
      setMembersSuccess(
        "Colaborador eliminado correctamente."
      );
    } catch (err) {
      setMembersError(getErrorMessage(err));
    } finally {
      setMembersSaving(false);
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
        <p className="lists-error" role="alert">
          {error}
        </p>
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
              <article
                className="lists-card"
                key={list.id}
              >
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
                    {new Date(
                      list.created_at
                    ).toLocaleDateString("es-ES")}
                  </span>

                  <div className="lists-card-actions">
                    {currentUser?.id === list.owner_id && (
                      <>
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

                        {list.visibility === "shared" && (
                          <button
                            type="button"
                            title="Administrar colaboradores"
                            aria-label={`Administrar colaboradores de ${list.name}`}
                            onClick={() => openMembersModal(list)}
                          >
                            <Users size={17} />
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* Ventana para crear o editar listas */}
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
                <option value="private">
                  Privada
                </option>
                <option value="shared">
                  Compartida
                </option>
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

      {/* Ventana para administrar colaboradores */}
      {selectedList && (
        <div className="lists-modal-backdrop">
          <section
            className="lists-modal lists-members-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="members-modal-title"
          >
            <div className="lists-modal-heading">
              <div>
                <h2 id="members-modal-title">
                  Colaboradores
                </h2>
                <p className="lists-members-subtitle">
                  {selectedList.name}
                </p>
              </div>

              <button
                type="button"
                onClick={closeMembersModal}
                aria-label="Cerrar colaboradores"
                disabled={membersSaving}
              >
                <X size={20} />
              </button>
            </div>

            <p className="lists-members-help">
              Añade usuarios registrados en TaskFlow
              mediante su correo electrónico.
            </p>

            {membersError && (
              <p className="lists-error" role="alert">
                {membersError}
              </p>
            )}

            {membersSuccess && (
              <p className="lists-success" role="status">
                {membersSuccess}
              </p>
            )}

            <form onSubmit={handleAddMember}>
              <label htmlFor="member-email">
                Correo electrónico
              </label>

              <input
                id="member-email"
                type="email"
                value={memberEmail}
                onChange={(event) =>
                  setMemberEmail(event.target.value)
                }
                placeholder="usuario@ejemplo.com"
                required
                disabled={membersSaving}
              />

              <label htmlFor="member-role">
                Rol del colaborador
              </label>

              <select
                id="member-role"
                value={memberRole}
                onChange={(event) =>
                  setMemberRole(event.target.value)
                }
                disabled={membersSaving}
              >
                <option value="editor">
                  Editor
                </option>
                <option value="viewer">
                  Lector
                </option>
              </select>

              <div className="lists-form-actions">
                <button
                  type="submit"
                  className="lists-create-button"
                  disabled={membersSaving || membersLoading}
                >
                  <Plus size={17} />
                  {membersSaving
                    ? "Procesando..."
                    : "Añadir colaborador"}
                </button>
              </div>
            </form>

            <div className="lists-members-section">
              <h3>
                Miembros de la lista ({members.length})
              </h3>

              {membersLoading ? (
                <p>Cargando colaboradores...</p>
              ) : members.length === 0 ? (
                <p className="lists-members-empty">
                  Todavía no hay colaboradores.
                </p>
              ) : (
                <div className="lists-members-list">
                  {members.map((member) => (
                    <div
                      className="lists-member-item"
                      key={member.id}
                    >
                      <div className="lists-member-info">
                        <strong>
                          Usuario #{member.user_id}
                        </strong>
                        <span>
                          {member.role === "editor"
                            ? "Puede editar tareas"
                            : "Solo puede consultar"}
                        </span>
                      </div>

                      <div className="lists-member-actions">
                        <select
                          aria-label={`Rol del usuario ${member.user_id}`}
                          value={member.role}
                          disabled={membersSaving}
                          onChange={(event) =>
                            handleUpdateMemberRole(
                              member.user_id,
                              event.target.value
                            )
                          }
                        >
                          <option value="editor">
                            Editor
                          </option>
                          <option value="viewer">
                            Lector
                          </option>
                        </select>

                        <button
                          type="button"
                          className="lists-member-delete"
                          title="Eliminar colaborador"
                          aria-label={`Eliminar usuario ${member.user_id}`}
                          disabled={membersSaving}
                          onClick={() =>
                            handleDeleteMember(
                              member.user_id
                            )
                          }
                        >
                          <Trash2 size={17} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="lists-form-actions">
              <button
                type="button"
                className="lists-cancel-button"
                onClick={closeMembersModal}
                disabled={membersSaving}
              >
                Cerrar
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

export default Lists;