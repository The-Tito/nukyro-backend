# Trampas, ronda adversaria y verificación

## Trampas que invalidan una evaluación

| Trampa | Por qué falla | Cómo se corrige |
|---|---|---|
| «NoSQL es más moderno / más rápido» | Solo es rápido para los patrones para los que se diseñó el modelo | Señala el patrón y su frecuencia |
| «Necesitamos escalar» | Casi ningún sistema escolar, clínica o comercio lo necesita | Muestra la cuenta de la fase 2 |
| «NoSQL no tiene esquema, así no diseño» | Es al revés: los documentos exigen más análisis previo | El esquema existe (aplicación o `$jsonSchema`) |
| «Tenemos JSON, entonces MongoDB» | PostgreSQL guarda JSON con índices (JSONB) | Puntúa ambas ramas |
| «El equipo ya sabe X» como único argumento | Es un criterio (`operacion`), no el veredicto | Pésalo en la matriz, no lo uses para saltártela |
| Valores sin datos que los respalden | El número no se puede auditar | Etiqueta y cuenta |
| Palabras vagas («flujo ineficiente») | No dicen qué falla | Nombra el problema: duplicación, lectura extra, arreglo sin tope, anomalía de actualización |
| Ignorar picos y casos extremos | El promedio miente; la P99 se dispara antes | Prueba años de datos, hora pico y dos usuarios a la vez |
| Diseñar para una escala que no existe | La forma más común de no terminar un proyecto | Elige lo más simple que cubra el caso extremo |
| Una tensión supuesta sin verificar | Puede no existir | Verifícala con números antes de diseñar alrededor de ella |

## Señales de que se eligió NoSQL cuando convenía SQL

- `$lookup` en el patrón más frecuente.
- Transacciones multi-documento en casi todas las escrituras.
- La misma información copiada en muchos documentos y actualizada a mano en todos.
- Reportes nuevos que obligan a reestructurar colecciones.

## Señales de que se eligió SQL cuando convenía documentos

- Decenas de columnas nulas o tablas EAV para atributos que varían.
- El patrón dominante reconstruye un objeto de 6+ tablas en cada lectura.
- Columnas `TEXT` con JSON sin índice que nadie valida.

---

## Las preguntas del adversario

1. ¿De qué supuesto depende esto y qué pasa si es falso?
2. ¿Qué escenario realista lo tumba?
3. ¿Qué costo aparece después que hoy no contamos?
4. Si tuviera que sabotearlo desde adentro, ¿por dónde entro?

Se distingue de «listar riesgos» en que **puede cambiar la decisión**. Registra cada ataque:

| # | Objetivo | Ataque | Efecto (Cambió / Refinó / Confirmó) | Qué quedó |
|---|---|---|---|---|

### Ataques típicos contra la elección de motor

- Entrada inválida, campos ausentes o tipos inesperados: ¿quién lo rechaza, motor o aplicación?
- Dos solicitudes simultáneas sobre la misma existencia o el mismo cupo.
- Escritura parcial, reintento o petición repetida (idempotencia).
- Fallo de conexión a mitad de una escritura que toca dos documentos o dos motores.
- Años de datos: el arreglo que crece sin tope, el reporte que recorre todo.
- El servicio gestionado sube de precio o el equipo cambia.

### Contraejemplo más pequeño

Para la regla de integridad más crítica, escribe el contraejemplo mínimo que demostraría que no se
cumple. Ej.: dos compras simultáneas con existencia 1; si ambas pasan, la existencia queda en −1.
Después di qué motor lo impide y cómo (bloqueo con `SELECT … FOR UPDATE`, actualización
condicionada `updateOne({_id, existencia: {$gte: 1}}, {$inc: {existencia: -1}})`, índice único…).

---

## Verificación del propio informe

**COVE (cadena de verificación):** verifica afirmaciones, no la prosa.
Borrador → preguntas de verificación (¿esta cifra tiene cuenta? ¿este patrón existe en la tabla?
¿este motor de verdad ofrece esa función en el servicio elegido?) → evidencia (repo, requisitos,
documentación oficial, ejecución de `score.py`) → revisión final.
Una explicación convincente no demuestra que sea correcta.

**Autoconsistencia:** si dudas de un puntaje, puntúa de nuevo la celda desde las anclas sin mirar
el valor anterior. Si cambia en más de 1 nivel, la evidencia es ambigua: anótala como hueco y
pregunta al usuario. La coincidencia sirve para priorizar la revisión; no sustituye la evidencia.

**Afirmaciones que requieren evidencia externa** (no basta con razonarlas): precios de servicios
gestionados, límites de un motor en una versión concreta, disponibilidad de una extensión en el
servicio en la nube elegido, y cualquier afirmación de rendimiento («A es más rápido que B»).
Para rendimiento, propón la medición en el plan de validación.
