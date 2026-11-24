import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import AuthLayout from "../components/auth/AuthLayout.jsx";
import { registerUser } from "../services/authService.js";

function Register() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");

    const cleanName = name.trim();
    const cleanEmail = email.trim();

    if (cleanName.length < 2) {
      setError("El nombre debe tener al menos 2 caracteres.");
      return;
    }

    if (password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }

    setLoading(true);

    try {
      await registerUser({
        name: cleanName,
        email: cleanEmail,
        password,
      });

      navigate("/login", {
        replace: true,
        state: {
          message:
            "¡Cuenta creada correctamente! Ya puedes iniciar sesión.",
        },
      });
    } catch (err) {
      const detail = err.response?.data?.detail;

      if (err.response?.status === 409) {
        setError("El correo electrónico ya está registrado.");
      } else if (typeof detail === "string") {
        setError(detail);
      } else if (err.response?.status === 422) {
        setError(
          "Revisa el nombre, correo y contraseña introducidos."
        );
      } else {
        setError(
          "No se pudo crear la cuenta. Comprueba la conexión con el servidor."
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Crea tu cuenta"
      subtitle="Empieza a organizar tu trabajo con TaskFlow."
    >
      <form onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="register-name">
            Nombre completo
          </label>

          <input
            id="register-name"
            type="text"
            placeholder="Tu nombre y apellidos"
            autoComplete="name"
            minLength={2}
            maxLength={100}
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={loading}
            required
          />
        </div>

        <div className="form-field">
          <label htmlFor="register-email">
            Correo electrónico
          </label>

          <input
            id="register-email"
            type="email"
            placeholder="nombre@correo.com"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={loading}
            required
          />
        </div>

        <div className="form-field">
          <label htmlFor="register-password">
            Contraseña
          </label>

          <input
            id="register-password"
            type="password"
            placeholder="Crea una contraseña"
            autoComplete="new-password"
            minLength={8}
            maxLength={128}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={loading}
            required
          />
        </div>

        {error && (
          <p className="auth-error" role="alert">
            {error}
          </p>
        )}

        <button
          type="submit"
          className="primary-button"
          disabled={loading}
        >
          {loading ? "Creando cuenta..." : "Crear cuenta"}
        </button>
      </form>

      <p className="auth-switch">
        ¿Ya tienes una cuenta?{" "}
        <Link to="/login">Inicia sesión</Link>
      </p>
    </AuthLayout>
  );
}

export default Register;