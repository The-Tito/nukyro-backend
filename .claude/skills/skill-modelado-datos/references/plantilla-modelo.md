# Plantilla del documento del modelo

Estructura recomendada. Omite las secciones que no aplican y dilo en una línea.

```markdown
---
version: 0.1
estado: Propuesta
fecha: AAAA-MM-DD
---

# Modelo de datos de <proyecto>

Propósito en dos líneas, alcance (qué cubre y qué queda para las migraciones) y convenciones de nombres (idioma, plural, glosario si existe).

## 1. Decisiones de base
| Decisión | Resumen | Registro |
| --- | --- | --- |
| Identificadores | … | ADR-nnn |
(Una fila por decisión importante de la fase 3, con enlace a su ADR.)

## 2. Diagrama entidad-relación
Mermaid `erDiagram` con entidades, relaciones con su cardinalidad y nombre, y solo las columnas que explican el diseño (llaves, estados, llaves de negocio).

## 3. Entidades
Por cada entidad: para qué existe en una frase y una tabla de columnas o grupos de columnas **no obvias**, con su justificación y el requerimiento que la pide.

## 4. Estados
Un diagrama de estados (Mermaid `stateDiagram-v2`) por entidad con estados: inicial, finales, transiciones y quién las provoca. Señala los estados calculados y su consulta.

## 5. Reglas que garantiza la base de datos
| Regla | Mecanismo | Requerimiento |
| --- | --- | --- |
Y las que **no** garantiza la base, con dónde se aplican.

## 6. Acceso y privilegios
(Si aplica.) Roles de base de datos, qué puede hacer cada uno y el mecanismo de aislamiento.

## 7. Procesos que cambian datos
(Si aplica.) Pasos y transacción de los procesos complejos, por ejemplo cómo se asignan los estados al terminar un proceso.

## 8. Borrado y retención
Tabla por entidad: tipo de borrado, qué pasa con los dependientes, plazo de retención.

## 9. Supuestos y pendientes
Supuestos tomados (con su origen: respuesta del usuario o suposición), pruebas técnicas pendientes y decisiones diferidas.
```
