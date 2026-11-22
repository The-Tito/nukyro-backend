---
name: evaluar-motor-bd
description: Evalúa de forma objetiva qué motor de base de datos le conviene a un proyecto (un solo motor o un híbrido) a partir de sus patrones de acceso, volumetría y reglas de integridad, con matriz ponderada, vetos, análisis de sensibilidad y ronda adversaria. Úsala cuando pidan elegir motor, decidir SQL vs NoSQL, justificar MongoDB o PostgreSQL, evaluar persistencia políglota o auditar la elección de base de datos de un proyecto.
---

# Evaluar el motor de base de datos de un proyecto

Objetivo: decidir, con evidencia rastreable, qué motor (o combinación de motores) se adapta a un
proyecto, y dejar escrito por qué, qué cuesta y qué dato haría cambiar la decisión.

> Regla de oro: **ninguna decisión se justifica con «porque sí», «es más moderno» o «escala mejor».**
> Cada afirmación apunta a un patrón de acceso (P1, P2…) con su frecuencia, o a una cuenta visible.

La elección sale de la **forma de los datos y de su uso**, nunca de la moda. «NoSQL es más rápido»
es una hipótesis: solo lo es para los patrones para los que se diseñó el modelo.

---

## Antes de empezar

1. Crea una lista de tareas con las fases 0–8 de abajo.
2. Lee `references/criterios-y-rubrica.md` (pesos, anclas de 1 a 5 y vetos). Es obligatoria: sin
   las anclas, la puntuación se vuelve opinión.
3. Ten a mano `references/familias-y-motores.md` (fase 4) y `references/hibridos.md` (fase 6).
4. Si el usuario ya dijo qué motor «quiere», **no lo uses como punto de partida**. Evalúa igual;
   al final compara su preferencia con el resultado y explica la diferencia, si la hay.

### Etiquetas de evidencia (se usan en TODO el informe)

| Etiqueta | Significa | Ejemplo |
|---|---|---|
| **[DATO]** | Lo dijo el cliente, está en el código o en un documento del repo (cita la ruta) | `models/venta.py` define `total` como `Decimal` |
| **[SUPUESTO]** | Estimación propia, declarada y con su cuenta | 80 ventas/día × 312 días (supuesto) |
| **[INFERIDO]** | Deducción a partir de datos, con el razonamiento a la vista | El ticket toca producto, inventario y pago → escritura multi-entidad |

Un número sin etiqueta es un error de la evaluación, no un detalle de formato.

---

## Fase 0 · Recolectar evidencia del proyecto

Recorre el repositorio **antes** de opinar. Busca, en este orden:

1. Documentación: `README*`, `docs/`, requisitos, minutas, historias de usuario, casos de uso.
2. Modelo actual: migraciones, DDL, `schema.prisma`, modelos ORM/ODM (Mongoose, SQLAlchemy,
   TypeORM, Django), `$jsonSchema`, archivos `.dbml`, diagramas.
3. Contrato de la API: rutas, controladores, OpenAPI. **Cada endpoint es un candidato a patrón.**
4. Consultas reales: repositorios/DAO, agregaciones, `JOIN`, `$lookup`, reportes, tareas programadas.
5. Infraestructura: `docker-compose`, IaC, variables de entorno, servicio en la nube previsto.
6. Restricciones: retención legal, presupuesto, equipo (qué motores ya domina), conectividad.

Comandos útiles (ajusta a la estructura real):
```bash
git ls-files | head -200
grep -rIl --exclude-dir={node_modules,.git,dist,build,venv} -E "Schema\(|createTable|CREATE TABLE|@Entity|model |collection\(" .
grep -rIn --exclude-dir={node_modules,.git} -E "router\.(get|post|put|patch|delete)|@(Get|Post|Put|Patch|Delete)|app\.(get|post)" . | head -100
```

Salida de la fase: lista de **hallazgos con ruta** y lista de **huecos** (lo que no está en ningún
lado). Si faltan los requisitos por completo, dilo y trabaja con supuestos marcados; no inventes
operaciones que nadie pidió (la IA no debe inventar campos ni reglas).

---

## Fase 1 · Patrones de acceso (operaciones, no datos)

Construye la tabla. **Una operación que lee y escribe se divide en dos patrones.**

| ID | Operación | Usuario | Tipo (L/E) | Datos que requiere | Busca por | Frecuencia (número + nivel) | Criticidad | Evidencia |
|---|---|---|---|---|---|---|---|---|
| P1 | | | | | | | | |

- **Frecuencia:** número estimado por día u hora **y** nivel Alta/Media/Baja. Si no hay dato,
  `(supuesto)` con la cuenta.
- **Criticidad:** ¿qué pasa si el dato queda inconsistente? `Dinero/inventario/legal` (alta),
  `operativa` (media), `tolerable/eventual` (baja). Alimenta el veto de integridad.
- **Busca por:** el campo de búsqueda u orden (alimenta índices y el ajuste del motor).

Después marca: patrón **más frecuente**, patrón que **más escribe**, qué se **lee junto**, qué se
**escribe junto** y qué datos aparecen en **patrones distintos**.

---

## Fase 2 · Volumetría y carga (la cuenta a la vista)

Calcula, mostrando la operación:

- Registros por año de la entidad que más crece × horizonte de retención.
- Tamaño aproximado (bytes por registro × filas, con índices y factor operativo ~2–2.5).
- Carga pico: operaciones por segundo en la hora pico; usuarios concurrentes.
- **Caso extremo:** años de datos, hora pico, dos usuarios sobre el mismo registro.
- **Sensibilidad:** triplica los dos supuestos que más pesan. ¿Cambia alguna decisión?

Conclusión obligatoria de la fase, en una línea: **¿este proyecto tiene un problema de escala o
no?** La mayoría de los sistemas escolares, clínicas y comercios caben de sobra en un solo servidor
relacional; si el volumen no lo justifica, «escalar» no puede ser argumento a favor de ningún motor.

---

## Fase 3 · Partir el sistema en dominios (agregados)

Agrupa los patrones en **dominios**: conjuntos de datos que se leen y escriben juntos y tienen su
propia regla de consistencia (ej. «ventas e inventario», «catálogo», «sesiones», «bitácora»,
«recomendaciones»).

| Dominio | Patrones | Peso del dominio | Criticidad máxima | Escrituras que cruzan a otro dominio |
|---|---|---|---|---|

- **Peso del dominio:** proporción de la actividad ponderada por criticidad. Cálculo sugerido:
  Σ(frecuencia diaria × factor de criticidad: alta 3, media 2, baja 1), normalizado a 1.
  Muestra la cuenta.
- **Escrituras cruzadas:** si una escritura crítica toca dos dominios (ej. la venta descuenta el
  inventario), esos dominios **no se pueden separar en motores distintos** sin un mecanismo de
  consistencia. Anótalo: es el principal freno de un híbrido.

Si el sistema completo es un solo dominio coherente, el híbrido queda descartado aquí y se dice por qué.

---

## Fase 4 · Las cuatro preguntas y las señales de familia, por dominio

Para **cada dominio**, responde con patrones en la mano:

| Pregunta | Inclina a SQL | Inclina a documentos |
|---|---|---|
| ¿La forma de los datos cambia? | Fija: mismas columnas | Varía entre registros |
| ¿Qué leo con más frecuencia? | Cruces y reportes variados | Un objeto completo |
| ¿Qué toca una escritura crítica? | Varias entidades a la vez | Una sola entidad |
| ¿Conozco los patrones de acceso? | No, o cambian seguido | Sí, y son estables |

Luego revisa las **señales de otras familias** (detalle en `references/familias-y-motores.md`):
relaciones recorridas en varios saltos (grafo), medición + marca de tiempo (series de tiempo),
GET/PUT por clave con expiración (clave-valor), búsqueda por similitud (vectores), búsqueda de
texto libre con relevancia (motor de búsqueda), consistencia requerida (ACID vs BASE).

Salida: por dominio, la **familia candidata** y los **motores concretos** a puntuar (mínimo dos,
para que haya contra qué comparar). Incluye siempre la variante «dentro de un solo motor»
(PostgreSQL con JSONB, MongoDB con transacciones y `$jsonSchema`) cuando aplique.

---

## Fase 5 · Matriz ponderada (árbol de ramas)

Abre las ramas de **arquitectura** (ToT) y recórrelas por dentro (CoT):

- **R1** Un solo motor relacional para todo.
- **R2** Un solo motor de documentos para todo.
- **R3** Un solo motor con modelo mixto (p. ej. PostgreSQL + JSONB para la parte variable).
- **R4…** Híbridos: cada dominio en el motor que mejor puntuó (solo si la fase 3 no lo descartó).

Puntúa cada motor en cada dominio con las **anclas** de `references/criterios-y-rubrica.md`.
**Cada celda lleva su justificación con patrón y etiqueta de evidencia.** Escribe el JSON de
entrada (formato en `examples/`) y ejecuta:

```bash
python3 <ruta-de-la-skill>/scripts/score.py evaluacion.json            # tabla en markdown
python3 <ruta-de-la-skill>/scripts/score.py evaluacion.json --json     # salida para procesar
```

El script: calcula el puntaje por dominio y por arquitectura, aplica los **vetos**, resta el
**costo de cada motor adicional** y de cada **escritura cruzada entre motores**, hace el
**análisis de sensibilidad** (pesos ±50 %, castigo de 0× a 2×) y declara **empate técnico** si el
margen es menor al umbral. **No cambies los puntajes para que gane la rama que «se siente»
correcta.** Si el resultado te parece absurdo, revisa las anclas y corrige la celda mal puntuada
diciendo cuál y por qué.

---

## Fase 6 · ¿Un motor o un híbrido?

Aplica la regla de `references/hibridos.md`. En corto, un híbrido **solo** se recomienda si se
cumplen las tres:

1. **Gana después del castigo**: el script lo pone arriba con el costo de operación ya restado.
2. **No hay variante en un solo motor que cubra lo mismo**: JSONB, columnas generadas, extensiones
   (`pgvector`, TimescaleDB, búsqueda de texto completo), colecciones de series de tiempo de Mongo,
   Atlas Search, etc. Si existe y queda a < umbral, gana el motor único.
3. **Las escrituras críticas no cruzan motores**, o si cruzan, se define el mecanismo (outbox,
   CDC, el motor transaccional como fuente de verdad y el otro como proyección reconstruible).

Si el veredicto es híbrido, define **cuál es la fuente de verdad** de cada dato y cómo se
reconstruye el otro motor si se pierde.

---

## Fase 7 · Ronda adversaria (puede cambiar la decisión)

Ataca la rama ganadora; no la defiendas. Lee `references/trampas-y-adversario.md`. Como mínimo:

1. ¿De qué supuesto depende y qué pasa si es falso?
2. ¿Qué escenario realista la tumba? (caso extremo, dos usuarios a la vez, enlace caído)
3. ¿Qué costo aparece después que hoy no contamos? (respaldos, migraciones, curva del equipo,
   precio del servicio gestionado)
4. Si tuviera que sabotearla desde adentro, ¿por dónde entro?
5. **Contraejemplo más pequeño** contra la regla de integridad más crítica.
6. **Sesgo de la segunda opinión:** pregúntate qué ganaría la rama perdedora con un solo dato
   distinto, y si ese dato es plausible.

Registra cada ataque como **Cambió / Refinó / Confirmó**. Una ronda que confirma todo sin
encontrar nada es sospechosa; dilo si pasa y por qué crees que la decisión es robusta.

---

## Fase 8 · Informe

Escribe el informe con la estructura de `references/plantilla-reporte.md` en
`context/evaluaciones/evaluacion-motor-bd.md`. Guarda junto a él el JSON de
puntuación (`context/evaluaciones/evaluacion-motor-bd.json`) para que otro pueda reejecutar el cálculo.

El veredicto se escribe con la **plantilla de cinco partes**:

1. **Postura:** qué motor(es), en una línea.
2. **Patrón:** qué operaciones lo exigen y con qué frecuencia.
3. **Criterio:** qué regla aplica (cuatro preguntas, veto de integridad, castigo del híbrido…).
4. **Costo:** qué se pierde con esta decisión.
5. **Lo que falta saber:** el dato que la validaría o la revertiría, y a quién pedírselo.

Cierra con un **plan de validación medible**: qué consulta, con qué volumen y en qué recursos
habría que medir (P95/P99, no promedios) para respaldar el veredicto con evidencia, no solo con
razonamiento.

---

## Lista de verificación final

- [ ] Todos los números tienen etiqueta y cuenta.
- [ ] Cada puntaje cita un patrón y un ancla.
- [ ] Se puntuaron al menos dos motores por dominio y al menos tres ramas de arquitectura.
- [ ] Se ejecutó `score.py` y se reporta la sensibilidad y si hubo empate técnico.
- [ ] Se probó la variante en un solo motor antes de recomendar un híbrido.
- [ ] La ronda adversaria tiene al menos un ataque con resultado distinto de «Confirmó», o una
      explicación de por qué no lo hubo.
- [ ] El informe termina con lo que falta saber y el plan de medición.
- [ ] No se usó «más moderno», «escala mejor» o «es más rápido» sin un patrón y un número.
