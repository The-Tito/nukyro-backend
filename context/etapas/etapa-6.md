# E6 · Ciclo de datos y estadísticas

> Puerta A delegada el 2026-11-28 (D-24, D-32). T-20, T-21 y T-22. D-39 fija la política de publicación de estadísticas.

## Objetivo

Demostrar el ciclo local de datos desde el ejercicio de derechos hasta su caducidad o purga, preservando las estadísticas permitidas. Usar PostgreSQL 16 y el proveedor de identidad simulado (D-15). El contenido legal de la app sigue siendo de demostración (D-17). RF-069 y los trámites ARCO de cuentas se implementan en E7.

## Reafirmación

| Qué se revisó | Evidencia | Resultado |
|---|---|---|
| Línea base de `develop` | `./scripts/verify` en `283e3f7` | SQL 298, unitarias 265, integración 422 y caja negra 90. Validador y migración desde cero en verde. |
| Resultado previo | EV-05 y RF-074 a RF-077 | 74 de 87 RF comprobados en el alcance local. |
| Aviso y contrato | DOC-AVP22, RF-078 a RF-080, RET-01, RET-02 y RET-06 | Desvincular a 30 días sin actividad. Bloquear cuentas tras 12 meses sin iniciar sesión, con 30 días de bloqueo. Logs técnicos a 90 días salvo incidente. La cookie acredita la titularidad sin cuenta; RF-069 reserva las solicitudes de cuentas para ARCO. |
| Código, esquema y ADR | ADR-002, ADR-007, ADR-008, `bd/schema.sql` y rutas de FastAPI | El esquema ya archiva, reescribe, bloquea y purga. Faltan rutas de derechos y el comando de tareas. El resumen actual solo considera hechos archivados. El contrato OpenAPI completo se entrega en T-28. |
| Reidentificación | RN-20, ADR-007, CC2, D2-18 y D2-19 | La reescritura separa los hechos de los datos de personas vivas. Comparar cortes exactos solapados puede revelar diferencias de una persona incluso con umbral 10 (A-07). |

## Dictamen

Con ajuste. T-20 y T-21 siguen los contratos y plazos aprobados. El cálculo interno y el informe al cierre siguen D-39.

## Análisis

- **T-20.** El servidor identifica al titular con el secreto de reanudación para descargar o borrar sesiones sin cuenta (RF-078). La oposición al uso estadístico se admite con o sin cuenta (RF-079), es idempotente y se ordena con el archivo por el bloqueo del participante. Para una cuenta se toma su bloqueo antes que el del participante, tal como en D-20 y ADR-007.
- **T-21.** Mantener la caducidad y la purga en funciones de PostgreSQL. El comando programable acepta un instante UTC inyectable y comunica solo los conteos de cada operación. Eliminar primero la identidad en el proveedor simulado al purgar y reintentar errores de proveedor sin borrar la cuenta local hasta recibir borrado o ausencia confirmada (D-35).
- **T-22.** Combinar hechos archivados y sesiones vigentes elegibles con la misma definición de métricas (D-19, D-21). Usar primeras sesiones por escenario según RN-18 para limitar la contribución de cada participante. Comparar resultados antes y después del archivo, y proteger umbrales por métrica. Se compararon un informe exacto al cierre, cortes semanales exactos cerrados y privacidad diferencial. El usuario eligió un informe exacto al cierre del piloto, con supresión de grupos pequeños y de totales que permitan despejarlos (D-39).

## Criterios por RF

| RF | Caso positivo | Caso negativo | Prueba |
|---|---|---|---|
| RF-070 | Borrar o bloquear archiva hechos permitidos y conserva el agregado | Oposición y minoría de edad omiten archivo; purgar una cuenta bloqueada solo borra | SQL, integración y T-22 |
| RF-072 | El agregado contiene métricas y abandono por versión; la cifra aparece con diez participantes elegibles | Nueve se suprimen; las publicaciones permitidas no exponen grupos por diferencias de cortes | SQL y pruebas del contrato de T-22 |
| RF-078 | La cookie propia permite descargar y borrar sesiones sin cuenta | Sin secreto válido se rechaza; token de cuenta se atiende por el flujo de ARCO de E7 | Integración por HTTPS y matriz de accesos |
| RF-079 | La oposición persiste, repetirla es inocuo y el archivo posterior la respeta | Sin credenciales o con cuenta bloqueada no muta nada; una escritura de origen ajeno se rechaza | Integración y D2-17 |
| RF-080 | Los plazos de 30 días y 12 meses se comprueban con un reloj controlado | Reintentos y concurrencia preservan consistencia; una falla al borrar en el proveedor conserva la cuenta bloqueada | SQL e integración de T-21 |

T-21 también comprueba el límite de 90 días para la bitácora (RET-02). T-20 y T-21 conservan la evidencia original del defecto 2 y 8 y añaden evidencia a través de sus nuevos puntos de entrada.

## Contrato y esquema

- `GET /api/v1/participants/me/data`: descarga JSON de sesiones propias sin cuenta, con progreso, decisiones y justificaciones, evaluaciones y datos relacionados. El recurso se resuelve por la cookie. Los campos del documento serán explícitos.
- `DELETE /api/v1/participants/me/data`: borra el historial sin cuenta con el procedimiento del owner, limpia la cookie y responde 204. Requiere la protección CSRF de ADR-008.
- `PUT /api/v1/participants/me/statistics-opposition`: registra oposición para el participante autenticado con el esquema existente. Responde 204, también al repetir la operación.
- T-21 mantiene los permisos separados de `nukyro_jobs`. T-22 habilita únicamente agregados para `nukyro_analytics`. El informe al cierre tendrá un único resultado persistido y reutilizable. El cálculo vivo quedará interno para comprobaciones de regresión (D-39).
- Los cambios de esquema posteriores se congelan en la migración inicial, conforme al flujo actual previo al despliegue.

## Riesgos

- Una vinculación puede concurrir con la descarga o el borrado. El bloqueo del participante y la invalidación del secreto hacen que la operación corresponda al estado que ganó la carrera.
- La reescritura de hechos mantiene el límite residual de ADR-007 para quien tenga acceso privilegiado a respaldos, almacenamiento o WAL. Las pruebas de E6 comprueban las superficies a las que acceden los roles de aplicación.
- Separar los reportes internos de las publicaciones evita usar los conteos exactos en vivo como prueba de privacidad.
- Los comandos de T-21 se prueban con el proveedor local. AWS y Cognito reales quedan fuera de la comprobación de D-15.

## Plan breve

| Paso | Entregable | Comprobación |
|---|---|---|
| T-20 | Rutas de descarga, oposición y borrado; archivo mediante SQL existente | Probar titularidad, CSRF, oposición y borrado por la API. |
| T-21 | Comando programable, plazos e integración con el proveedor simulado | Verificar fronteras, reintentos y concurrencia. |
| T-22 | Resumen vivo interno, métricas por tema y abandono y un informe exacto al cierre según D-39 | Comparar antes y después de borrar y casos de nueve, diez y diferencias de cortes. |
| E6 | Auditoría, evidencia, reporte y diagramas (D-31) | `./scripts/verify` desde cero y evidencia de los RF. |

## Puerta A

Delegada (D-24, D-32) para los criterios ya aprobados de E6. La publicación de T-22 queda fijada tras la aprobación de D-39. T-20 y T-21 mantienen los datos, plazos y finalidades vigentes.

## Puerta B

Pendiente. Verificar los cinco RF, los defectos 2 y 8, el umbral y las diferencias de cortes, y registrar la evidencia y la revisión documental de D-31.
