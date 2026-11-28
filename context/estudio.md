# Para defender

Preguntas probables por tarea o etapa, con respuesta que cita las decisiones (D-xx, ADR-xxx).

## T-01 · Adopción de la metodología

**¿Por qué el KG no tiene los nombres del equipo si es la única fuente de verdad?**
El repositorio es público (D-08) y lo publicado no se retira del todo. El KG conserva roles y relaciones con seudónimos; la identidad se consulta en los originales, que son solo locales (D-09, ADR-006).

**¿Seudonimizar es lo mismo que anonimizar?**
No. Con la universidad, la asignatura, la cuenta de GitHub o los documentos se puede volver a identificar a una persona. Se reduce la exposición, no se elimina (ADR-006).

**¿Cómo se sabe que un documento no cambió si no está en git?**
Para el archivo principal de cada documento, el KG guarda su sha256 y el validador lo compara donde existe docs/. Las copias, plantillas y fuentes LaTeX solo se comprueban por existencia. En un clon sin esa carpeta no lo comprueba y lo avisa (D-13, Regla 2).

## E2 · Base ejecutable y entrada

**¿Por qué una tabla sin identificadores puede no ser anónima?**
PostgreSQL guarda en cada fila la transacción que la escribió (`xmin`). Con el diseño viejo, un JOIN por `xmin` decía
quién eligió cada opción. Por eso los hechos se copian solo al cerrar y se reescriben en orden aleatorio (ADR-007).

**¿Por qué la primera sesión la decide la base y no la API?**
Dos inicios simultáneos veían «no hay sesión previa» y los dos quedaban como primera. El trigger bloquea la fila del
participante: el segundo espera y ya ve la sesión del primero (RN-18).

**¿Qué impide que otra página haga peticiones a nombre del participante?**
La cookie `__Host-` con SameSite y, en toda escritura, Origin exacto más una cabecera que otro origen no puede
enviar sin permiso. La excepción de los GET está declarada en ADR-008.

## E3 · Motor de simulación

**¿Por qué un reintento se busca antes de validar el nodo actual?**
Si la respuesta se pierde, la sesión ya avanzó. Validar primero el nodo rechazaría un reintento legítimo. Se devuelve
la decisión confirmada, aunque el reintento traiga otra alternativa (RN-14, defecto 1).

**¿Cómo sabe el sistema qué decisiones causaron un evento sin inventar causas?**
Guarda cada efecto con su valor anterior y nuevo. Una condición verdadera solo atribuye las decisiones que cambiaron
esa variable; una rama falsa o un efecto recortado sin cambio no cuentan (ADR-009).

**¿Cómo puede un examen correcto medir mal?**
Si la correcta es siempre la más larga o la misma clave, se aprueba sin saber. Por eso el orden cambia por sesión y
una prueba derrota una lista cerrada de estrategias ciegas. Eso no valida la calidad pedagógica: la revisa una persona.

## E4 · Experiencia educativa

**¿Por qué el resumen espera a que terminen las evaluaciones?**
Muestra causas y retroalimentación, o sea las respuestas de la causal. Antes daría 409 (defecto 11). Por lo mismo la
puntuación no sale al enviar cada evaluación.

**¿Cómo se sabe que alguien respondió la encuesta sin saber qué respondió?**
La sesión solo guarda un indicador. La respuesta entra por una función que reescribe la tabla completa en orden
aleatorio. El límite: si una sola persona respondió, su fila es evidente (ADR-007).

## E5 · Identidad y aislamiento

**¿Qué pasa si un token válido al empezar una petición vence antes de crear la cuenta?**
Al insertar una cuenta, la API verifica el mismo token dentro de la transacción. Si venció durante la espera,
devuelve 401 y revierte el alta. El plazo mínimo de A-06 cubre la vigencia de un token anterior al bloqueo (D-35).

**¿Cómo se decide qué sesión queda como primera al vincular?**
La base bloquea la cuenta y los participantes, traslada el progreso y recalcula la primera sesión de cada
escenario por fecha e id. Repetir la vinculación encuentra el secreto anterior invalidado (RF-076, RF-077).

**¿Cómo detecta la suite una ruta nueva sin un caso de acceso ajeno?**
Compara las rutas que FastAPI registra con el inventario. La integración usa ese inventario para probar las
peticiones del dueño y de otra persona, y verifica el rechazo de escrituras de origen ajeno (T-19).

## T-20 · Derechos del participante

**¿Cómo acredita su titularidad quien usa Nukyro sin cuenta?**
El servidor busca la huella del secreto de reanudación recibido en la cookie. La descarga y el borrado se limitan al participante que acredita esa cookie (RF-078).

**¿Qué ocurre cuando una persona se opone y después borra sus datos?**
La oposición se guarda en el participante. El borrado respeta ese estado y suprime la copia de nuevos hechos (RF-079, D-20).

**¿Por qué purgar una cuenta bloqueada solo borra?**
El bloqueo ya decidió si correspondía conservar una copia anónima. Purgar elimina los datos bloqueados cuando vence el plazo (RF-070, D-20).

## T-21 · Caducidad y purgas

**¿Por qué el trabajo comprueba de nuevo el plazo bajo bloqueo?**
Una solicitud puede renovar la actividad entre el listado y el bloqueo de una fila. Al revalidar antes de cambiarla, la operación respeta la actividad más reciente (RF-080).

**¿Qué pasa si la identidad se elimina en el proveedor y falla el borrado local?**
La cuenta sigue bloqueada. El reintento acepta que la identidad ya no exista y termina la purga. Un token emitido durante el bloqueo tampoco puede crear una cuenta nueva con esa identidad (D-35).

## T-22 · Informe del piloto

**¿Por qué un cálculo en vivo y un informe cerrado dan garantías diferentes?**
El informe cerrado guarda un solo resultado. Analítica carece de permiso para pedir un segundo corte exacto y despejar cambios pequeños por diferencia (D-39).

**¿Cuándo se muestran los caminos del escenario?**
Solo si todos los grupos del desglose alcanzan diez participantes y hay al menos dos grupos. Una cifra total combinada con categorías visibles podría permitir deducir una categoría suprimida (RN-20).
