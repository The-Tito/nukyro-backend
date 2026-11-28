# Evidencia en rojo · defectos 2 a 9 (T-09, S-03)

Las pruebas se escribieron y se corrieron **contra el `bd/schema.sql` original** (el de la rama `develop`, sin
tocar) antes de corregir nada. PostgreSQL 16 desechable, esquema y semilla aplicados como `nukyro_owner`
(sin SUPERUSER ni CREATEROLE).

Comando: `GUARDAR=<carpeta> bd/pruebas/ejecutar.sh` (código de salida 1).

| Suite | Resultado contra el esquema original |
|---|---|
| `pruebas-reglas.sql` (con los cambios de la tabla de `etapa-2.md`) | 31 PASS y se detiene en el primer FAIL: T31 |
| `pruebas-defectos.sql` | 36 PASS, **130 FAIL** (no se detiene: cuenta todos) |
| `pruebas-concurrencia.sh` | 5 PASS, **10 FAIL** |

## Qué falló realmente, por defecto

| Defecto | Prueba | Síntoma real en el esquema original |
|---|---|---|
| 2 (xmin) | D2-10 a D2-21, CC2 | No existe `erase_anonymous_participant` (42883) ni `topic_facts` (42P01) ni `stopped_at_key` (42703): no hay archivo por función. **No se reprodujo el vínculo por xmin en sí**: el esquema viejo no tiene el flujo nuevo contra el que medirlo; lo que se prueba en verde es el resultado (un solo xmin distinto del de cualquier participante vivo). |
| 3 (INSERT RETURNING) | D3-01, D3-02, D3-11 | D3-01 **pasa** también en rojo (42501) porque en el esquema viejo la API tenía INSERT sin SELECT y `RETURNING` falla: es el síntoma del defecto, no una prueba que lo distinga. Lo que sí falla en rojo: D3-02 (la API sí inserta `decision_facts`), D3-11 (jobs insertaba; llegó 23502 por `closure_reason`), D2-04/05/06 (hay privilegios sobre hechos). |
| 4 (FK de administradores) | D4-01 a D4-04 | D4-02: borrar al administrador que publicó dio **23514** (el SET NULL dispara el trigger de versión), no 23503. D4-03: el administrador que creó un borrador se borró sin error. D4-04: el rol admin tenía DELETE sobre `admin_users`. |
| 5 (ciclo de la versión) | D5-01, 02, 03, 05, 06, 09, 10, 11 | Se pudo insertar una versión publicada o retirada y un borrador con `published_by`; un borrador pasó a retirado sin publicarse y cambió de escenario; al retirar se alteraron `published_by`, `created_at` y `scenario_id` sin error. Pasan en rojo D5-12, 14, 15, 16 (esas reglas ya existían). |
| 6 (editar contra publicar) | CC3a, CC3b | CC3a: publicar no esperó a la edición en curso (2 ms). CC3b: una edición que llega con otra transacción publicando **se aceptó** (código 0) y el nodo publicado quedó con título «tarde». Las pruebas secuenciales D6-01 a 03 pasan en rojo (no distinguen el defecto: es una carrera). |
| 7 (permisos por columna) | D7-01 a 05, 11 a 14, 16, 20, 22 a 24, 27, 30 a 38, 40, 42 a 49, 51, 53, 55 a 58, 61 a 62, 65 a 66 | La API cambió `cognito_sub`, `deletion_due_at`, el participante, la versión y `started_at` de sesiones, `has_prior_session`, `facts_written_at`, decisiones, pasos, efectos, eventos, aceptaciones, variables y preguntas de respuestas; borró cuentas, participantes, sesiones y decisiones; cambió respuestas tras enviar el intento; una cuenta bloqueada se modificó y se reactivó; `account_id` y `secret_hash` cambiaron. Donde el síntoma fue otro código (23514, 23505, 23503) también cuenta: la base no rechazó por permiso. |
| 8 (jobs sin leer hechos) | D8-01 a 04, 05 a 36, CC4 | jobs leía hechos y encuestas (D3-12/13/15) y borraba y actualizaba directamente (D8-01 a 04). No existen `block_account`, `expire_anonymous_participants`, `purge_blocked_accounts`, `report_session_summary` (42883). Analítica leía filas de hechos (D3-16/17/19). |
| 9 (primera sesión) | CC1, D9-01 a 07, D7-40 | CC1: dos inicios simultáneos dieron **2 primeras sesiones** (`2/2`). D9-03 a 07: la base confía en el valor enviado. D7-40: sin `has_prior_session` el INSERT falla con 23502. |

## Lo que la prueba en rojo no pudo demostrar

- T32b a T39 de `pruebas-reglas.sql` no se alcanzaron en rojo: el script se detiene en el primer FAIL (T31).
- El orden físico aleatorio de las filas reescritas no se prueba (solo el xmin compartido).

## Agregado en la revisión

**Defecto 2, reproducido contra el esquema de 60e867e.** Como `nukyro_api`, una transacción inserta un participante
y su fila de `decision_facts`, como hacía P5. Después:

```sql
SELECT p.id, f.decision_key, f.option_key
  FROM nukyro.participants p JOIN nukyro.decision_facts f ON f.xmin = p.xmin;
```

Devolvió una fila: el participante, `D01` y `A`. El hecho «anónimo» decía quién eligió qué.

**Intentos enviados (defecto 7).** Con la primera corrección, D7-55b y D7-55d fallaron: la API podía reabrir un
intento enviado y agregarle respuestas. Pasan con `trg_guard_attempt_submitted` y el trigger de respuestas también en INSERT.

**Defecto 9 al vincular una cuenta (T-18).** Con `link_participant` sin el recálculo de `has_prior_session` (el
traslado de sesiones del paso 1 de P10 y nada más), fallaron L-07 y L-09 y, en concurrencia, CC5 y CC6: la cuenta
con una sesión y el navegador con otra quedaban con **dos primeras sesiones** (`1/2/2` en CC5; en CC6, dos primeras
entre tres sesiones). Con el recálculo por `(started_at, id)` pasan: queda una sola, la más antigua.

**Defecto 12 al purgar una cuenta (T-18, A-06).** Con el esquema de `ff3a65c`, D12-01 y D12-02
fallaron porque PostgreSQL aceptó el bloqueo con un plazo menor a una hora en vez de devolver 23514.
La prueba de integración `test_defecto12_el_token_anterior_al_bloqueo_no_recrea_la_cuenta` recibió
200 en vez de 403 al reutilizar el mismo token del emisor simulado en la API tras una purga inmediata.
Con el `CHECK`, el plazo de una hora se acepta, antes del plazo el mismo token recibe 403 y al
purgar recibe 401. En ese momento la cuenta ya no existe y el inicio de sesión no la recrea.

La auditoría también comprobó la petición que valida el token antes de la purga y llega al INSERT
después. Al adelantar el reloj del verificador al instante de purga entre esos dos pasos, el primer
arreglo devolvió 200. Si se inserta una cuenta se vuelve a verificar el token dentro de la misma
transacción, antes de escribir consentimientos o vincular el progreso. La prueba obtiene 401 y
comprueba que la transacción revirtió el alta.
