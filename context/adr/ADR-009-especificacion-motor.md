---
id: ADR-009
titulo: Especificación del motor de simulación
estado: Aceptada
fecha: 2026-11-22
decisores: asistente por delegación (D-24), sin revisión humana
kg: [ADR-009, ADR-001, ADR-003, RF-028, RF-030, RF-066, RN-14]
---

# ADR-009 · Especificación del motor de simulación

## Contexto

El esquema guarda `effects` y `condition` como JSON sin gramática. Sin una, dos implementaciones darían finales
distintos con el mismo recorrido.

## Decisión

El motor es una función pura: `(contenido, estado, acción) -> resultado`. No lee reloj, base ni azar.

### Efectos

`options.effects` es una lista de `{"variable_key", "op": "add"|"set", "value": entero}`. Se aplican en el orden de la
lista. Cada resultado se recorta a `min_value` y `max_value` y se guarda con su valor anterior, aunque no cambie.

### Condiciones

| Forma | Es verdadera si |
|---|---|
| `{"var": k, "op": "eq"\|"ne"\|"lt"\|"lte"\|"gt"\|"gte", "value": n}` | el valor actual de k cumple |
| `{"chose": option_key}` | esa alternativa está confirmada |
| `{"visited": node_key}` | ese nodo está en el recorrido |
| `{"all": [c, ...]}` | todas; lista no vacía |
| `{"any": [c, ...]}` | alguna; lista no vacía |
| `{"not": c}` | c es falsa |

Cualquier otra clave, tipo o profundidad mayor de 8 es contenido inválido. Un booleano no es un entero.

### Orden al salir de un nodo

1. Confirmar la decisión y aplicar sus efectos.
2. Con el estado ya actualizado, evaluar las reglas `event` de ese nodo por (`priority`, `key`). Se activan todas las
   verdaderas. Su destino es un nodo de tipo evento que se muestra como consecuencia, sin cambiar la ruta.
3. Evaluar las `transition` en el mismo orden. Gana la primera verdadera y se registra igual que un evento.
4. Si ninguna gana: `next_node_id` de la alternativa y, si no hay, `default_next_node_id` del nodo.
5. Agregar el paso. Si es un desenlace, fijarlo con su hora. Todo va en una transacción.

### Causas (RF-034, RF-065)

| Condición verdadera | Decisiones causantes |
|---|---|
| `var` | las que cambiaron esa variable (anterior distinto de nuevo) |
| `chose` | la de esa alternativa |
| `visited` | ninguna |
| `all` | unión de sus partes |
| `any` | unión de sus partes verdaderas |
| `not` | las que cambiaron las variables que menciona c |

El resumen solo atribuye estas relaciones, con el `relation_type` y la explicación del contenido.

### Avance, reintentos y validez

- **Avanzar sin decisión:** solo en nodos que no son decisión ni desenlace. El cliente manda el nodo del que sale.
  Si ya se salió de ese nodo, devuelve el estado actual sin cambios. En una decisión pendiente da 409.
- **Decidir:** primero se busca la decisión de ese nodo. Si existe, se devuelve la confirmada, aunque la petición
  traiga otra alternativa o la sesión haya avanzado (RN-14). Si no, el nodo debe ser el actual.
- **Razones:** si se exige justificación, al menos una y sin repetir; si no se exige, ninguna. Es correcta con el
  mínimo de correctas y ninguna incorrecta (defecto 10).
- **Pre-test:** toda versión publicada lo tiene (D-28, RF-007) y no se sale del primer nodo sin completarlo.
- **Inicio y ciclos:** hay un solo nodo `intro`. El grafo de rutas es acíclico: un nodo se visita una vez.
- **Publicar exige:** un pre-test con preguntas y una opción correcta por cada una (D-28); gramática y claves válidas; destinos de la misma versión y del tipo correcto; todo nodo
  alcanzable; toda ruta termina en desenlace; toda decisión con alternativa válida y, si se justifica, con razones
  correctas suficientes.
- **Hacia el cliente** no salen variables, efectos, reglas, destinos ni cuáles razones son correctas.

### Precisiones

- El destino de una regla `event` no crea paso ni cuenta para `visited`; para publicar sí cuenta como alcanzable.
  Dos reglas pueden mostrar el mismo evento: cada una se registra una vez por sesión.
- Una variable repetida en los efectos de una alternativa es válida: es causa si algún efecto la cambió.
- Una petición rechazada no cambia nada, tampoco la actividad del participante: solo renueva la que se acepta.
- Publicar rechaza todo nodo inaccesible: el contenido no tiene cómo justificar uno (RF-066).
- `visited` sobre un evento solo mostrado es válido y siempre falso.
- El pre-test lo exige P12 y la puerta del primer nodo la aplica P5; el motor puro no lo conoce.
- Un `not` sin variables puede no tener decisiones causantes: solo se atribuye la regla, no se inventa una causa.

### Ejemplos calculados a mano

Variables: `p` = 3 entre 0 y 5; `e` = 3 entre 0 y 5. En D1: A = `p -2`, B = `p +3`. En D2: C = `e +1`, D = `p -2`.
Reglas al salir de D2: evento EV si `p lt 2`; transición a MALO si `any(p lte 1, chose D)`, prioridad 10; predeterminado BUENO.

| Recorrido | p | e | Evento | Final | Causas del evento | Causas de la transición |
|---|--:|--:|---|---|---|---|
| A, C | 1 | 4 | EV | MALO | D1 | D1 |
| A, D | 0 (recortado de -1) | 3 | EV | MALO | D1, D2 | D1, D2 |
| B, C | 5 (recortado de 6) | 4 | no | BUENO | | |
| B, D | 3 | 3 | no | MALO | | D2 (solo la rama verdadera) |

## Alternativas consideradas

- **Expresiones evaluadas como código:** inyección y resultados no deterministas.
- **JSONLogic:** gramática mucho mayor que la necesaria y sin cálculo de causas.
- **Ciclos con salida:** chocan con una decisión por nodo (RN-14) y hacen ambiguo el reintento de avance.

## Consecuencias

El contenido no puede repetir un nodo. Un operador nuevo exige cambiar este ADR, el validador y sus ejemplos.

## Trazabilidad

Concreta ADR-001 y ADR-003. Afecta RF-013 a RF-038, RF-063 a RF-066, RN-03, RN-04, RN-06 y RN-14.
