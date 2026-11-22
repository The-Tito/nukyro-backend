---
id: ADR-008
titulo: Estructura y seguridad de la API
estado: Aceptada
fecha: 2026-11-22
decisores: asistente por delegación (D-24), según el plan aprobado en D-23; sin revisión humana
kg: [ADR-008, ADR-002, ADR-005, D-15, RF-062, RNF-13, RNF-17]
---

# ADR-008 · Estructura y seguridad de la API

## Contexto

Hay que fijar cómo se organiza el backend y dónde se impone cada regla antes de escribir la primera ruta.

## Decisión

1. **Monolito modular** en `src/nukyro/modules/<módulo>/`: rutas, servicio, consultas. El motor será puro.
2. **SQL explícito** con SQLAlchemy Core y transacciones síncronas cortas. Una conexión por rol.
3. **El servidor decide:** los esquemas de entrada rechazan campos desconocidos; id, versión, fechas, nodo y
   puntuación nunca vienen del cliente.
4. **Sesión anónima:** 256 bits aleatorios en una cookie `__Host-` Secure, HttpOnly, SameSite. La base guarda SHA-256.
5. **Aislamiento:** toda consulta filtra por el participante autenticado. Lo ajeno y lo inexistente dan 404.
6. **CSRF:** toda escritura exige Origin exacto y `X-Nukyro-Request: 1`.
7. **Defensa en la base:** permisos por columna, triggers y funciones restringidas.
8. **Errores y logs:** código estable, sin repetir la entrada ni registrar cookies, cuerpos o secretos.
9. **Local:** HTTPS con CA local; el emisor de identidad simulado nunca entra en la imagen de la API.

## Alternativas consideradas

- **Microservicios, Celery o Redis:** operación que 50 participantes no justifican.
- **ORM con autogeneración:** oculta bloqueos y no genera triggers, funciones ni permisos.
- **Token CSRF con estado:** más piezas; el frontend (A-01) no necesita peticiones entre orígenes.

## Consecuencias

- El SQL se prueba contra PostgreSQL real, no con simulaciones.
- Un frontend en otro origen exigiría revisar los puntos 4 y 6.

## Trazabilidad

Concreta ADR-002, ADR-005 y D-15. Afecta RF-062, RF-063, RIS-01, RNF-03, RNF-04, RNF-13, RNF-15 y RNF-17.
