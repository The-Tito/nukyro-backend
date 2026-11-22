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
