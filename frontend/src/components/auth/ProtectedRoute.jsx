import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";

import { getCurrentUser, logoutUser } from "../../services/authService.js";

function ProtectedRoute() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let active = true;

    async function verifySession() {
      const token = sessionStorage.getItem("taskflow_token");

      if (!token) {
        if (active) setStatus("unauthenticated");
        return;
      }

      try {
        await getCurrentUser();

        if (active) setStatus("authenticated");
      } catch {
        logoutUser();

        if (active) setStatus("unauthenticated");
      }
    }

    verifySession();

    return () => {
      active = false;
    };
  }, []);

  if (status === "checking") {
    return (
      <main className="app-container">
        <p>Verificando sesión...</p>
      </main>
    );
  }

  if (status === "unauthenticated") {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;