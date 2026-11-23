# Etapa 5 · Identidad y aislamiento: análisis y plan

> Estado: delegado el 2026-11-22 (D-24, D-32), con revisión humana pendiente. Tareas: T-17, T-18, T-19.
> Decisiones: D-33, D-34, D-35, A-06. Supuestos: ninguno nuevo.

## Objetivo

Con o sin cuenta, cada persona accede solo a lo suyo:

- la API acepta un token de identidad, verificado contra un emisor simulado (D-15);
- crea o actualiza la cuenta;
- vincula el progreso del navegador (P10);
- cada ruta prueba que lo ajeno da 404.

**No incluye:**

- Cognito real, AWS ni gasto (D-15).
- Registro, inicio de sesión ni recuperación de contraseña dentro de la API: los hace Cognito, y la API solo recibe el token (RF-074, RF-075).
- Cambiar las preferencias de comunicaciones después del registro, ni derechos ARCO (E6 y E7).
- Borrar el usuario en el proveedor al purgar (T-21).
- La interfaz (A-01).

## Reafirmación

| Pregunta | Evidencia | Resultado |
|---|---|---|
| ¿Sigue funcionando lo anterior? | `./scripts/verify` sobre develop en d54c24a | sql=269, unit=217, integration=140, blackbox=77; validador en verde |
| ¿El objetivo sigue siendo el del KG? | RF con `se_planea_en` E5; nodo E5 | Sí: RF-074 a RF-077 |
| ¿Lo construido coincide con lo decidido? | `bd/schema.sql`, ADR-002, ADR-008, `security.py` | Sí. Las tablas `accounts` y `consent_events`, el trigger `compute_session_prior`, `guard_participant_update` y `block_account` existen. La API solo conoce la cookie: no hay verificador ni ruta de cuenta |
| ¿Cuánto falta de verdad? | EV-04 | 70 de 87 RF (21 con interfaz pendiente). E5 suma 4. RF-077 ya pregunta y calcula `has_prior_session` (T-10); le falta recalcularlo al vincular |
| ¿Qué aprendimos que cambie el plan? | E2 a E4; D-33 | El reporte de quien programa no basta: se repiten verify, el diff y los sabotajes. La auditoría ya no es un agente, la hace la sesión en Opus (D-33). Las cifras del KG se pasan literales |

## Dictamen

**Con ajuste.** Cambia el cómo:

- la API verifica el token de identidad de Cognito (D-34);
- la vinculación entra por una función de la base (defecto 9);
- el defecto 12 se cierra con una edad máxima del token, sin guardar datos (D-35, A-06).

## Análisis

| Paso | Opciones | Elegida y por qué |
|---|---|---|
| Token que recibe la API | Token de acceso; token de identidad | **Token de identidad (D-34).** Trae `aud`, `token_use`, `email`, `email_verified`, `nickname` y `cognito:groups`, que es lo que pide el criterio de T-17 y lo que hace falta para crear la cuenta. El de acceso no trae `aud` ni correo y obligaría a una llamada más. Riesgo: un token de identidad es para el cliente. Se mitiga con audiencia exacta, tipo `id`, vida corta y transporte solo por `Authorization: Bearer` |
| Firma | HS256; RS256 con JWKS | **RS256 con JWKS** del emisor, con caché por `kid`. Se rechazan `none`, HS* y `kid` desconocido. PyJWT ya estaba aprobado (E2) y RS256 necesita su extra `crypto` (`cryptography`) |
| Emisor simulado | Dentro de la API; contenedor aparte | **Contenedor aparte** en `devtools/issuer/`, fuera de `src/` y de la imagen de la API (ADR-008 §9). Publica `/.well-known/openid-configuration` y JWKS, y emite tokens solo para pruebas. Una prueba falla si la imagen de la API contiene el emisor o su clave |
| Grupo | Ignorarlo; exigirlo | **Un token del grupo `admins` no es participante** (ADR-002 §7): en las rutas de participante da 403 |
| Quién es la persona | Token o cookie, en ese orden | **Una sola dependencia `current_participant`.** Primero el token: cuenta activa y su participante. Si no hay token, la cookie. Una cuenta bloqueada da 403 `account_blocked`. Sin participante, las rutas de sesión piden aceptar los documentos (409) |
| Cuenta | Crearla en cada petición; ruta explícita | **`POST /api/v1/account/login`.** Hace un upsert por `cognito_sub` (`ON CONFLICT DO NOTHING`), exige `email_verified` y copia el correo y el nickname. Las casillas de boletín y encuestas valen `false` si no vienen; al crear la cuenta se registran en `consent_events` con origen `registration`. Si llega la cookie de un navegador sin cuenta, vincula (P10) y borra la cookie |
| Participante con cuenta y sin navegador | Crear el participante al iniciar sesión; al aceptar documentos | **Al aceptar documentos.** `POST /participants` con token crea un participante con `account_id` y sin secreto. Así 18+ y el Aviso siguen ocurriendo antes de la primera sesión |
| Vinculación (P10, defecto 9) | SQL desde la API; función del owner | **`link_participant(p_account, p_secret_hash)`, SECURITY DEFINER.** La API no puede borrar un participante ni cambiar `sessions.participant_id`. Bloquea en orden cuenta y participantes (por id) y rechaza una cuenta bloqueada. Traslada sesiones, copia aceptaciones, une `exclude_from_stats`, borra B y recalcula `has_prior_session` de todas las sesiones de A: una sesión tiene previa si A tiene otra del mismo escenario creada antes (desempate por id). Si una sesión con copia anónima cambia de primera a no primera, reescribe los hechos. Repetirla no hace nada, porque B ya no existe |
| Defecto 12 | Lápida con el `sub` cifrado; edad máxima del token | **Edad máxima del token (D-35):** `iat` de hace menos de 1 hora y `exp − iat` de 1 hora o menos. Una cuenta bloqueada sigue en la base hasta `deletion_due_at`. Si ese plazo nunca es menor que la vida del token (A-06), cualquier token anterior a la baja vence antes de la purga y nunca recrea la cuenta, sin guardar ningún dato. Lo emitido después de la baja lo cierra T-21, que borra al usuario en el proveedor |
| Excepción CSRF de los GET (ADR-008 §6) | Quitarla; mantenerla | **Mantenerla y probarla.** Un GET solo renueva `last_activity_at`. Con token, el navegador no envía `Authorization` solo, así que no aplica. Las escrituras con token siguen pidiendo Origin y `X-Nukyro-Request` |
| Rutas sin prueba de lo ajeno | Lista a mano; inventario automático | **Inventario automático:** una prueba recorre `app.routes` y falla si una ruta de participante no está en el registro de casos de acceso ajeno. Otra prueba envía cada escritura con un Origin ajeno |

## Criterios por RF

| RF | Caso positivo | Caso negativo | Prueba |
|---|---|---|---|
| RF-074 | Token válido de un `sub` nuevo con correo verificado: crea la cuenta con nickname repetible y casillas en `false`; dos inicios simultáneos dejan una cuenta | Correo sin verificar, firma, emisor, audiencia, tipo, vencimiento, edad o grupo inválidos: 401 o 403 y ninguna cuenta | unit (verificador), integration, blackbox con el emisor |
| RF-075 | El mismo token, desde otro "navegador" sin cookie, ve y reanuda las sesiones de la cuenta | Token de otra cuenta: 404 en esas sesiones; cuenta bloqueada: 403 | integration, blackbox |
| RF-076 | Login con cookie de B: sesiones en A, B borrado, cookie invalidada; repetirlo no cambia nada; dos vinculaciones simultáneas dejan el mismo estado | Cookie de B tras vincular: 401; cuenta bloqueada: no vincula; la API no puede ejecutar el traslado sin la función | sql (función, permisos, concurrencia), integration |
| RF-077 | Tras vincular, cada escenario de A tiene a lo más una sesión primera | Defecto 9: dos primeras sesiones antes de la corrección (rojo) y una después (verde) | sql, integration |

Criterios de las tareas (`context/plan.md`), fijos:

- **T-17:** rechaza firma, emisor, audiencia, tipo, vencimiento y grupo inválidos; el emisor no entra en la imagen de la API.
- **T-18:** la vinculación concurrente es idempotente y deja una primera sesión; un token anterior a la baja no recrea la cuenta; los defectos 9 y 12, reproducidos y corregidos.
- **T-19:** cada ruta tiene un caso de acceso ajeno; una escritura de origen ajeno se rechaza.

Salida de E5: los tokens inválidos se rechazan, la vinculación concurrente deja una primera sesión y una ruta sin caso de acceso ajeno hace fallar la suite.

## Contrato y esquema

- **Configuración nueva:** `NUKYRO_OIDC_ISSUER`, `NUKYRO_OIDC_AUDIENCE` y `NUKYRO_OIDC_JWKS_URL` (opcional; por omisión, la del documento de descubrimiento). Faltar una impide arrancar.
- **Rutas nuevas:**
  - `POST /api/v1/account/login`, con cuerpo `{newsletter_opt_in?, surveys_opt_in?}`. Responde `{nickname, has_participant, linked}`.
  - `GET /api/v1/account`, que responde `{nickname, email, newsletter_opt_in, surveys_opt_in}`.
- **Rutas existentes:** aceptan `Authorization: Bearer` además de la cookie.
- **Esquema:**
  - función `link_participant` (owner, SECURITY DEFINER, ejecutable solo por `nukyro_api`, revocada de PUBLIC);
  - si se confirma A-06, `CHECK (deletion_due_at >= blocked_at + interval '1 hour')`.
  - Pruebas nuevas en `bd/pruebas/`. `freeze_schema.py` se vuelve a ejecutar.
- **Dependencias:** `PyJWT[crypto]` con versión fija. El emisor usa la misma biblioteca en su propia imagen.
- **OpenAPI:** las dos rutas nuevas y el esquema de seguridad `bearer`.

## Riesgos

- El emisor simulado puede no parecerse a Cognito. Se mitiga copiando sus claims (`token_use`, `cognito:username`, `cognito:groups`, `auth_time`) y declarando «no probado: Cognito real».
- **Interbloqueo al vincular.** Orden fijo: cuenta y participantes por id. Hay prueba concurrente.
- La función de vinculación es SECURITY DEFINER: `search_path` fijo, revocada de PUBLIC, y prueba de que otros roles no la ejecutan.
- Cambiar quién es "primera sesión" mueve los hechos anónimos: se reescriben en la misma transacción.
- **Costo de uso.** Ya no hay agentes (D-33): se trabaja por tarea y se cierra con `/cerrar` al 96 %.

## Plan breve

| Paso | Qué | Entregable | Cómo se verifica |
|---|---|---|---|
| 1 | T-17 (Sonnet) | Verificador, emisor en contenedor aparte, configuración y dependencia | Pruebas unitarias de cada rechazo; prueba de la imagen; verify |
| 2 | T-18 (Sonnet) | `link_participant`, `/account/login`, `/account`, `current_participant`, defectos 9 y 12 | Pruebas SQL de la función, permisos y concurrencia; integration y blackbox; defectos de rojo a verde |
| 3 | T-19 (Sonnet) | Inventario de rutas con casos de acceso ajeno; CSRF por ruta; revisión de la excepción de los GET | La suite falla al agregar una ruta sin caso (sabotaje) |
| 4 | Comprobar (Opus) | Auditoría en la sesión contra estos criterios, sabotajes y escaneos; EV-05 | `./scripts/verify` desde base vacía |

## Puerta A

Delegada (D-24, D-32) el 2026-11-22. Se aprueban:

- los criterios de esta página;
- PyJWT con su extra `crypto`;
- el emisor en un contenedor aparte;
- D-34 y D-35.

Queda reservado al usuario, sin bloquear T-17: **A-06**, el plazo mínimo de bloqueo antes de purgar (toca la conservación de datos personales).

## Puerta B

La evidencia será EV-05: verify desde una base vacía, los sabotajes del inventario y del verificador, y los escaneos.

No se probará Cognito real ni AWS. La Puerta B queda delegada (D-32), con revisión humana pendiente.
