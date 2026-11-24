import api from "./api.js";

// Obtener listas propias y compartidas.
export async function getLists() {
  const response = await api.get("/api/lists");
  return response.data;
}

// Obtener una lista por su identificador.
export async function getListById(listId) {
  const response = await api.get(`/api/lists/${listId}`);
  return response.data;
}

// Crear una lista nueva.
export async function createList(listData) {
  const response = await api.post("/api/lists", listData);
  return response.data;
}

// Modificar una lista existente.
export async function updateList(listId, listData) {
  const response = await api.patch(
    `/api/lists/${listId}`,
    listData
  );
  return response.data;
}

// Eliminar una lista.
export async function deleteList(listId) {
  await api.delete(`/api/lists/${listId}`);
}

// Consultar los colaboradores.
export async function getListMembers(listId) {
  const response = await api.get(
    `/api/lists/${listId}/members`
  );
  return response.data;
}

// Añadir un colaborador.
export async function addListMember(listId, memberData) {
  const response = await api.post(
    `/api/lists/${listId}/members`,
    memberData
  );
  return response.data;
}

// Modificar el rol de un colaborador.
export async function updateListMember(
  listId,
  userId,
  memberData
) {
  const response = await api.patch(
    `/api/lists/${listId}/members/${userId}`,
    memberData
  );
  return response.data;
}

// Eliminar un colaborador.
export async function deleteListMember(listId, userId) {
  await api.delete(
    `/api/lists/${listId}/members/${userId}`
  );
}