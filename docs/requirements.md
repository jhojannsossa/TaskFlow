# TaskFlow - Especificación de requisitos

## 1. Información del proyecto

- Nombre: TaskFlow
- Tipo: Aplicación web Full Stack
- Formación: BUTCAM
- Versión del documento: 1.0
- Estado: En desarrollo

## 2. Objetivo general

Desarrollar una aplicación web que permita gestionar
tareas personales y colaborativas, mejorar la
productividad y facilitar la organización del trabajo.

## 3. Objetivos específicos

- Organizar tareas personales.
- Gestionar prioridades y fechas de vencimiento.
- Facilitar la colaboración entre usuarios.
- Automatizar recordatorios y notificaciones.
- Visualizar estadísticas de productividad.
- Garantizar la seguridad de la información.

## 4. Actores del sistema

- Visitante.
- Usuario registrado.

### Roles dentro de las listas

- Owner: propietario de la lista.
- Editor: colaborador con permisos de edición.
- Viewer: colaborador con permisos de lectura.

## 5. Requisitos funcionales

### 5.1. Autenticación y usuarios

- RF-001: Registrar nuevos usuarios.
- RF-002: Iniciar sesión.
- RF-003: Cerrar sesión.
- RF-004: Consultar el perfil de usuario.
- RF-005: Modificar el perfil de usuario.
- RF-006: Configurar preferencias de notificación.

### 5.2. Gestión de tareas

- RF-007: Crear tareas.
- RF-008: Consultar tareas.
- RF-009: Editar tareas.
- RF-010: Eliminar tareas.
- RF-011: Cambiar el estado de las tareas.
- RF-012: Establecer prioridades.
- RF-013: Establecer fechas de vencimiento.
- RF-014: Filtrar tareas.
- RF-015: Ordenar tareas.
- RF-016: Consultar el detalle de una tarea.

### 5.3. Gestión de listas

- RF-017: Crear listas privadas.
- RF-018: Crear listas compartidas.
- RF-019: Editar listas.
- RF-020: Eliminar listas.
- RF-021: Invitar colaboradores.
- RF-022: Asignar roles a colaboradores.
- RF-023: Asignar tareas a usuarios.
- RF-024: Sincronizar cambios entre colaboradores.

### 5.4. Notificaciones

- RF-025: Notificar tareas próximas a vencer.
- RF-026: Notificar tareas vencidas.
- RF-027: Notificar cambios de estado.
- RF-028: Notificar nuevas asignaciones.
- RF-029: Notificar cambios en listas compartidas.
- RF-030: Marcar notificaciones como leídas.

### 5.5. Dashboard

- RF-031: Mostrar el total de tareas.
- RF-032: Mostrar tareas pendientes.
- RF-033: Mostrar tareas en progreso.
- RF-034: Mostrar tareas completadas.
- RF-035: Mostrar tareas vencidas.
- RF-036: Calcular porcentajes de finalización.
- RF-037: Mostrar gráficos de productividad.
- RF-038: Filtrar estadísticas por fecha y lista.
- RF-039: Mostrar actividad reciente.

## 6. Requisitos no funcionales

- RNF-001: Diseño responsive.
- RNF-002: Interfaz intuitiva y accesible.
- RNF-003: Contraseñas almacenadas mediante hashing.
- RNF-004: Autenticación mediante JWT.
- RNF-005: Validación de permisos en el backend.
- RNF-006: Validación de datos de entrada.
- RNF-007: Arquitectura modular.
- RNF-008: Aplicación de principios Clean Code.
- RNF-009: Control de versiones mediante Git.
- RNF-010: Pruebas automatizadas.
- RNF-011: Documentación técnica.
- RNF-012: Gestión segura de variables de entorno.
- RNF-013: Compatibilidad con navegadores modernos.
- RNF-014: Integridad de los datos.
- RNF-015: Uso de HTTPS en producción.

## 7. Reglas de negocio

- RN-001: El correo electrónico del usuario será único.
- RN-002: Toda tarea tendrá un creador.
- RN-003: Toda lista tendrá un propietario.
- RN-004: Una lista privada no tendrá colaboradores.
- RN-005: Solo usuarios autorizados podrán editar listas.
- RN-006: Una tarea compartida solo podrá asignarse
  a un usuario autorizado de la lista.
- RN-007: Una tarea completada no generará avisos
  de vencimiento.
- RN-008: Las notificaciones respetarán las preferencias
  del usuario.
- RN-009: Una tarea tendrá un título obligatorio.
- RN-010: Las estadísticas respetarán los permisos
  de acceso del usuario.

## 8. Estados de las tareas

- todo
- in_progress
- done

## 9. Prioridades

- low
- medium
- high
- urgent

## 10. Visibilidad de listas

- private
- shared

## 11. Roles de colaboración

- owner
- editor
- viewer

## 12. Arquitectura tecnológica

- Frontend: React y Vite.
- Backend: Python y FastAPI.
- ORM: SQLAlchemy.
- Base de datos: PostgreSQL.
- Comunicación: API REST mediante HTTP y JSON.
- Autenticación: JWT.

## 13. Pruebas

- Pruebas unitarias.
- Pruebas de integración.
- Pruebas de API.
- Pruebas de interfaz.
- Pruebas de seguridad y permisos.

## 14. Entorno de desarrollo

- Visual Studio Code.
- PyCharm.
- Git.
- GitHub.
- PostgreSQL.
- pgAdmin.
- Postman.
- Jira.
- Figma.