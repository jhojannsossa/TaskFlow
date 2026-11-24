import { Link } from "react-router-dom";
import "./AuthLayout.css";

function AuthLayout({ title, subtitle, children }) {
  return (
    <main className="auth-layout">
      <section className="auth-brand-panel">
        <div className="auth-brand-content">
          <span className="auth-company">FACTORÍA F5</span>

          <h1>TaskFlow</h1>

          <p className="auth-brand-slogan">
            Organiza lo importante.
            <br />
            Colabora mejor.
          </p>

          <p className="auth-brand-description">
            Gestiona tus tareas, comparte responsabilidades
            y alcanza tus objetivos en equipo.
          </p>

          <div className="auth-brand-footer">
            Proyecto Full Stack · Factoría F5
          </div>
        </div>
      </section>

      <section className="auth-form-panel">
        <div className="auth-form-container">
          <Link to="/login" className="auth-logo">
            <span className="auth-logo-mark" />
            <strong>TaskFlow</strong>
            <span className="auth-logo-separator">×</span>
            <span className="auth-logo-company">Factoría F5</span>
          </Link>

          <header className="auth-header">
            <h2>{title}</h2>
            <p>{subtitle}</p>
          </header>

          {children}
        </div>
      </section>
    </main>
  );
}

export default AuthLayout;