import { useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
} from "react-router-dom";

import AuthLayout from "../components/auth/AuthLayout.jsx";
import {
  loginUser,
  getCurrentUser,
} from "../services/authService.js";

function Login() {
  const navigate = useNavigate();
  const location = useLocation();

  const successMessage = location.state?.message;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      const response = await loginUser({
        email: email.trim(),
        password,
      });

      sessionStorage.setItem(
        "taskflow_token",
        response.access_token
      );

      // Comprobar que el token funciona.
      await getCurrentUser();

      navigate("/dashboard", {
        replace: true,
        state: null,
      });
    } catch (err) {
      sessionStorage.removeItem("taskflow_token");

      const detail = err.response?.data?.detail;

      setError(
        typeof detail === "string"
          ? detail
          : "No se pudo iniciar sesión. Comprueba tus datos."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Bienvenido a TaskFlow"
      subtitle="Accede a tu espacio de trabajo."
    >
      {successMessage && (
        <p className="auth-success" role="status">
          {successMessage}
        </p>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="email">
            Correo electrónico
          </label>

          <input
            id="email"
            type="email"
            placeholder="nombre@correo.com"
            autoComplete="email"
            value={email}
            onChange={(event) =>
              setEmail(event.target.value)
            }
            required
          />
        </div>

        <div className="form-field">
          <label htmlFor="password">
            Contraseña
          </label>

          <input
            id="password"
            type="password"
            placeholder="Introduce tu contraseña"
            autoComplete="current-password"
            value={password}
            onChange={(event) =>
              setPassword(event.target.value)
            }
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
          {loading
            ? "Iniciando sesión..."
            : "Iniciar sesión"}
        </button>
      </form>

      <p className="auth-switch">
        ¿No tienes una cuenta?{" "}
        <Link to="/register">
          Regístrate
        </Link>
      </p>
    </AuthLayout>
  );
}

export default Login;