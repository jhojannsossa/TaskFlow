import { useEffect, useRef, useState } from "react";

import {
  getCurrentUser,
  updateCurrentUser,
  uploadProfileAvatar,
  deleteProfileAvatar,
} from "../services/authService.js";

import "./Profile.css";

const MAX_AVATAR_SIZE = 2 * 1024 * 1024;

const ALLOWED_IMAGE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
];

function Profile() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    job_title: "",
    birth_date: "",
    share_birthday: false,
  });

  const [avatarUrl, setAvatarUrl] = useState(null);
  const [avatarError, setAvatarError] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [avatarSaving, setAvatarSaving] = useState(false);

  const fileInputRef = useRef(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    async function loadProfile() {
      try {
        const user = await getCurrentUser();

        setFormData({
          name: user.name ?? "",
          email: user.email ?? "",
          job_title: user.job_title ?? "",
          birth_date: user.birth_date ?? "",
          share_birthday: user.share_birthday ?? false,
        });

        setAvatarUrl(user.avatar_url ?? null);
      } catch {
        setError("No se pudo cargar tu perfil.");
      } finally {
        setLoading(false);
      }
    }

    loadProfile();
  }, []);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return;
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);

    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  const initials = formData.name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  const apiBaseUrl =
    import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

  const avatarSrc = previewUrl
    || (avatarUrl
      ? `${apiBaseUrl.replace(/\/$/, "")}${avatarUrl}`
      : null);

      useEffect(() => {
        setAvatarError(false);
      }, [avatarSrc]);

  function handleChange(event) {
    const { name, value, type, checked } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value,
    }));

    setSuccess("");
  }

  function handleSelectAvatar(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setError("");
    setSuccess("");

    if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
      setError("Selecciona una imagen JPG, PNG o WebP.");
      event.target.value = "";
      return;
    }

    if (file.size > MAX_AVATAR_SIZE) {
      setError("La fotografía no puede superar los 2 MB.");
      event.target.value = "";
      return;
    }

    setSelectedFile(file);
  }

  async function handleUploadAvatar() {
    if (!selectedFile) {
      return;
    }

    setAvatarSaving(true);
    setError("");
    setSuccess("");

    try {
      const updatedUser = await uploadProfileAvatar(
        selectedFile
      );

      setAvatarUrl(updatedUser.avatar_url ?? null);
      setSelectedFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      setSuccess("Fotografía actualizada correctamente.");
    } catch (err) {
      setError(
        typeof err.response?.data?.detail === "string"
          ? err.response.data.detail
          : "No se pudo subir la fotografía."
      );
    } finally {
      setAvatarSaving(false);
    }
  }

  async function handleDeleteAvatar() {
    if (selectedFile) {
      setSelectedFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      return;
    }

    if (!avatarUrl) {
      return;
    }

    setAvatarSaving(true);
    setError("");
    setSuccess("");

    try {
      const updatedUser = await deleteProfileAvatar();

      setAvatarUrl(updatedUser.avatar_url ?? null);
      setSuccess("Fotografía eliminada correctamente.");
    } catch (err) {
      setError(
        typeof err.response?.data?.detail === "string"
          ? err.response.data.detail
          : "No se pudo eliminar la fotografía."
      );
    } finally {
      setAvatarSaving(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const updatedUser = await updateCurrentUser({
        name: formData.name.trim(),
        email: formData.email.trim(),
        job_title: formData.job_title.trim() || null,
        birth_date: formData.birth_date || null,
        share_birthday: formData.share_birthday,
      });

      setFormData({
        name: updatedUser.name ?? "",
        email: updatedUser.email ?? "",
        job_title: updatedUser.job_title ?? "",
        birth_date: updatedUser.birth_date ?? "",
        share_birthday: updatedUser.share_birthday ?? false,
      });

      setSuccess("Tu perfil se ha actualizado correctamente.");
    } catch (err) {
      setError(
        typeof err.response?.data?.detail === "string"
          ? err.response.data.detail
          : "No se pudieron guardar los cambios."
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p>Cargando perfil...</p>;
  }

  return (
    <section className="profile-page">
      <header className="profile-header">
        <span className="profile-brand">FACTORÍA F5</span>
        <h1>Mi perfil</h1>
        <p>Personaliza tu información y tus preferencias.</p>
      </header>

      <div className="profile-card">
        <div className="profile-avatar-section">
          <div className="profile-avatar">
            {avatarSrc && !avatarError ? (
              <img
                src={avatarSrc}
                alt="Fotografía de perfil"
                onError={() => setAvatarError(true)}
              />
            ) : (
              initials
            )}
          </div>

          <div className="profile-avatar-information">
            <h2>{formData.name || "Mi cuenta"}</h2>
            <p>{formData.job_title || "Usuario TaskFlow"}</p>

            <div className="profile-avatar-actions">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleSelectAvatar}
                className="profile-file-input"
                id="profile-avatar-input"
                disabled={avatarSaving}
              />

              <button
                type="button"
                className="profile-avatar-button"
                onClick={() => fileInputRef.current?.click()}
                disabled={avatarSaving}
              >
                {avatarUrl ? "Cambiar foto" : "Seleccionar foto"}
              </button>

              {selectedFile && (
                <button
                  type="button"
                  className="profile-avatar-upload"
                  onClick={handleUploadAvatar}
                  disabled={avatarSaving}
                >
                  {avatarSaving ? "Subiendo..." : "Guardar foto"}
                </button>
              )}

              {(avatarUrl || selectedFile) && (
                <button
                  type="button"
                  className="profile-avatar-delete"
                  onClick={handleDeleteAvatar}
                  disabled={avatarSaving}
                >
                  {selectedFile ? "Cancelar" : "Eliminar foto"}
                </button>
              )}
            </div>

            <small className="profile-avatar-help">
              JPG, PNG o WebP. Máximo 2 MB.
            </small>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="profile-form-grid">
            <label>
              Nombre completo
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                minLength={2}
                maxLength={100}
                required
              />
            </label>

            <label>
              Correo electrónico
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </label>

            <label>
              Cargo en la empresa
              <input
                type="text"
                name="job_title"
                value={formData.job_title}
                onChange={handleChange}
                maxLength={100}
                placeholder="Ej. Desarrollador Full Stack"
              />
            </label>

            <label>
              Fecha de nacimiento
              <input
                type="date"
                name="birth_date"
                value={formData.birth_date}
                onChange={handleChange}
                max={new Date().toLocaleDateString("en-CA")}
              />
            </label>
          </div>

          <label className="profile-checkbox">
            <input
              type="checkbox"
              name="share_birthday"
              checked={formData.share_birthday}
              onChange={handleChange}
            />
            Compartir mi cumpleaños con compañeros de
            listas compartidas
          </label>

          {error && (
            <p className="profile-message profile-error" role="alert">
              {error}
            </p>
          )}

          {success && (
            <p className="profile-message profile-success" role="status">
              {success}
            </p>
          )}

          <button
            className="profile-save-button"
            type="submit"
            disabled={saving}
          >
            {saving ? "Guardando..." : "Guardar cambios"}
          </button>
        </form>
      </div>
    </section>
  );
}

export default Profile;