---
id: ADR-002
titulo: El participante como raíz de identidad, con o sin cuenta
estado: Aceptada
fecha: 2026-11-01
decisores: PER-DEV-01, PER-DEV-02, PER-DEV-03
kg: [ADR-002, D3, D7, C4, ACCESO-HIBRIDO, MIGRACION-SESION, MODO-ANONIMO, DEC-PRIMERA-SESION]
---

# ADR-002 · El participante como raíz de identidad, con o sin cuenta

## Contexto

El MVP tiene acceso híbrido (ACCESO-HIBRIDO, CONF-02):

- **Sin cuenta:** un secreto de reanudación en una cookie Secure, HttpOnly y SameSite (RF-062). Los datos caducan a los 30 días de inactividad (MODO-ANONIMO, RET-06).
- **Cuenta opcional con Amazon Cognito:** quien empezó sin cuenta puede crearla y conservar su progreso (MIGRACION-SESION).

Además:

- Solo la **primera sesión** de cada persona cuenta para H02–H07 (DEC-PRIMERA-SESION), y quien no tiene cuenta puede repetir desde otro navegador (C4).
- Las aceptaciones de documentos (18+, Aviso, Términos) ocurren antes de cualquier sesión y guardan versión, fecha y hora (MODO-ANONIMO, Aviso 2.1 §3).
- El panel de administración necesita usuarios propios (PANEL-ADMIN).

## Decisión

1. **Tabla `participants`.** Un participante es "quien participa", identificado por un navegador (sin cuenta) o por una cuenta.
   - Es el dueño de sus sesiones, sus aceptaciones de documentos y su preferencia de excluirse de las estadísticas.
   - Tiene un `account_id` opcional.
2. **Secreto de reanudación por participante.** El servidor emite el secreto al crear el participante, es decir, al aceptar los documentos antes de la primera sesión. Lo entrega en la cookie y solo guarda su **hash SHA-256**; como el secreto es aleatorio y largo, no hace falta un hash lento. Con él se reanudan todas las sesiones de ese navegador. **Esto cambia la redacción de RF-062** (antes: "al crear una sesión").
3. **Tabla `accounts`.** Se liga a Cognito por `cognito_sub` (único) y tiene además un `id` propio. Guarda una copia del correo, el nickname (no único, DEC-NICKNAME), las preferencias de comunicaciones y las fechas del ciclo de vida, tal como declara el Aviso 2.1 (proceso 1). Cognito manda en credenciales y verificación del correo; la base manda en todo lo demás.
4. **Conservar el progreso al crear cuenta.** Al crear la cuenta o iniciar sesión desde un navegador con participante sin cuenta, ese participante queda ligado a la cuenta.
   - Si la cuenta ya tenía un participante, las sesiones del participante del navegador se trasladan a él y el participante del navegador se elimina.
   - El secreto anónimo se invalida.
   - Todo ocurre en una sola transacción y repetir la operación no la duplica (RF-064).
5. **Primera sesión (C4).** Una sesión se marca como primera solo si:
   - no hay sesión anterior del mismo participante para ese escenario, **y**
   - la persona respondió "sí" a la pregunta "¿Es la primera vez que haces este escenario?" al iniciar.

   Se guardan las dos señales por separado: `has_prior_session` (calculada) y `self_reported_first` (declarada). La sesión cuenta para H02–H07 solo si ambas lo indican.
6. **Aislamiento (D7).** Todas las tablas de la sesión cuelgan del participante. El servidor resuelve el participante a partir del secreto o del token de Cognito y filtra por él. No se usa seguridad por fila del motor; el aislamiento se comprueba con pruebas (RNF-03, RNF-17).
7. **Administradores.** Van en la tabla `admin_users`, ligada a `cognito_sub`. Quién es administrador lo decide el grupo de Cognito `admins`; la tabla existe para atribuir cambios de contenido, atención de solicitudes ARCO y la bitácora. Un administrador no es participante.

## Alternativas consideradas

| Opción | Por qué se descartó |
| --- | --- |
| Sesión con cuenta opcional y secreto propio | Conservar el progreso exige recorrer sesiones; no se puede calcular "primera sesión en este navegador"; las aceptaciones de documentos no tendrían dueño antes de la primera sesión. |
| Secreto por sesión (RF-062 original) | Un navegador con varias sesiones manejaría varios secretos, y ligarlas a una cuenta se complica. |
| Seguridad por fila del motor | Depende de un motor aún no elegido; excesivo para 50 participantes y un solo dueño de los datos. |

## Consecuencias

- **A favor:** conservar el progreso es una operación acotada; la primera sesión se calcula por participante; las aceptaciones y la exclusión de estadísticas tienen dueño desde el primer momento.
- **En contra:** la regla de "primera sesión" sigue siendo imperfecta sin cuenta; la pregunta declarada lo mitiga, pero no lo elimina. El correo queda copiado de Cognito: si se cambia en Cognito, hay que sincronizarlo.
- **Requiere actualizar:** RF-062 y OR-02 en el documento de requerimientos (versión 1.1).

## Trazabilidad

RF-001–RF-006, RF-062, RF-063, RF-067–RF-070, RNF-02, RNF-03, RNF-17, OR-02, RN-01, RN-02, RN-05, H02–H07, ACCESO-HIBRIDO, MIGRACION-SESION, MODO-ANONIMO, DEC-PRIMERA-SESION, DEC-NICKNAME, DEC-SUPUESTOS-MODELO.
