# Para defender

Preguntas probables por tarea o etapa, con respuesta que cita las decisiones (D-xx, ADR-xxx).

## T-01 · Adopción de la metodología

**¿Por qué el KG no tiene los nombres del equipo si es la única fuente de verdad?**
El repositorio es público (D-08) y lo publicado no se retira del todo. El KG conserva roles y relaciones con seudónimos; la identidad se consulta en los originales, que son solo locales (D-09, ADR-006).

**¿Seudonimizar es lo mismo que anonimizar?**
No. Con la universidad, la asignatura, la cuenta de GitHub o los documentos se puede volver a identificar a una persona. Se reduce la exposición, no se elimina (ADR-006).

**¿Cómo se sabe que un documento no cambió si no está en git?**
Para el archivo principal de cada documento, el KG guarda su sha256 y el validador lo compara donde existe docs/. Las copias, plantillas y fuentes LaTeX solo se comprueban por existencia. En un clon sin esa carpeta no lo comprueba y lo avisa (D-13, Regla 2).
