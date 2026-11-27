import api from "./api.js";

export async function registerUser(userData) {
  const response = await api.post(
    "/api/auth/register",
    userData
  );

  return response.data;
}

export async function loginUser(credentials) {
  const response = await api.post(
    "/api/auth/login",
    credentials
  );

  return response.data;
}

export async function getCurrentUser() {
  const response = await api.get("/api/auth/me");

  return response.data;
}

export function logoutUser() {
  sessionStorage.removeItem("taskflow_token");
}

export async function getUserByEmail(email) {
  const response = await api.get("/api/users/by-email", {
    params: {
      email: email.trim().toLowerCase()
    }
  });

  return response.data;
}

export async function updateCurrentUser(userData) {
  const response = await api.patch(
    "/api/users/me",
    userData
  );

  return response.data;
}

export async function uploadProfileAvatar(file) {
  const formData = new FormData();

  formData.append("file", file);

  const response = await api.post(
    "/api/users/me/avatar",
    formData
  );

  return response.data;
}

export async function deleteProfileAvatar() {
  const response = await api.delete(
    "/api/users/me/avatar"
  );

  return response.data;
}