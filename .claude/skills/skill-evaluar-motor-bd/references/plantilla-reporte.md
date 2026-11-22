# Plantilla del informe `context/evaluaciones/evaluacion-motor-bd.md`

Respeta el orden. Las secciones pueden ser cortas, pero ninguna se omite; si no hay información,
escribe qué falta y a quién pedírsela.

```markdown
# Evaluación del motor de base de datos · <nombre del proyecto>

**Fecha:** <fecha> · **Evidencia revisada:** <rutas principales del repo y documentos>

## 1. Veredicto
- **Postura:** <motor o combinación, en una línea>
- **Patrón:** <P# más decisivos y su frecuencia>
- **Criterio:** <regla que inclinó la balanza>
- **Costo:** <qué se pierde>
- **Lo que falta saber:** <dato que validaría o revertiría, y a quién pedirlo>
- **Confianza:** Alta / Media / Baja, con el porqué (margen, sensibilidad, supuestos críticos)

## 2. Evidencia recolectada
| Hallazgo | Ruta / fuente | Etiqueta |
Huecos detectados: …

## 3. Patrones de acceso
<tabla de la fase 1> + más frecuente, el que más escribe, qué viaja junto

## 4. Volumetría y carga
<cuentas a la vista> · caso extremo · triplicar supuestos · ¿hay problema de escala? (sí/no)

## 5. Dominios
<tabla de la fase 3, con el cálculo del peso y las escrituras cruzadas>

## 6. Cuatro preguntas y señales por dominio
<una tabla por dominio> → familia candidata y motores a puntuar

## 7. Matriz de puntuación
<salida de score.py pegada> + justificación de cada celda (patrón + ancla + etiqueta)
Pesos usados y, si se cambiaron, por qué.

## 8. ¿Un motor o híbrido?
Las tres condiciones, una por una, con su resultado.
Si es híbrido: fuente de verdad de cada dato y mecanismo de consistencia.
Si es un motor: el híbrido como evolución futura y su disparador.

## 9. Ronda adversaria
| # | Objetivo | Ataque | Efecto | Qué quedó |
Contraejemplo más pequeño de la regla más crítica.

## 10. Recomendaciones de implementación
Servicio gestionado sugerido, tipos de dato críticos (dinero en numeric/Decimal128),
reglas que garantiza el motor vs la aplicación, 2–3 índices derivados de los patrones dominantes.

## 11. Plan de validación medible
Consulta(s) representativas de los patrones dominantes · volumen (horizonte de retención) ·
recursos limitados (perfil similar a la instancia prevista) · métricas: P50/P95/P99, throughput,
CPU estrangulada, memoria, volcado a disco · criterio que confirmaría o refutaría el veredicto.

## 12. Preguntas para el cliente o el equipo
<lista numerada, ordenada por cuánto cambian la decisión>
```

**Antes de entregar:** ¿cité patrón y frecuencia? ¿los números tienen cuenta o dicen (supuesto)?
¿nombré el costo? ¿probé el caso extremo? ¿usé los términos exactos (embebido, referencia, índice
único parcial, `$jsonSchema`, JSONB, transacción)? ¿cerré con la información que falta?
