# Recorridos esperados de DEMO-BECAS (T-13)

Calculados a mano con ADR-009 y recalculados con un evaluador independiente (`tests/unit/test_demo_truth.py`, que no usa el motor y cubre las 6 561 rutas). Las pruebas los comparan con el motor y con la API por HTTPS.
Variables (todas entre 0 y 10, inicio 5): `privacy` (P), `access` (A), `quality` (Q). Los efectos se aplican en el orden
de la lista de cada alternativa; el recorte a 0..10 se anota con «→». Al avanzar, la ruta es intro, D1 a D8 y un desenlace.

Reglas: `ev_access` (evento, sale de D6): A <= 4. `ev_leak` (evento, sale de D7): P <= 4.
`tr_crisis` (transición, prioridad 10, sale de D8): any(P <= 3, all(A <= 3, Q <= 4)). `tr_solid` (prioridad 20, sale de D8):
all(P >= 7, A >= 6, Q >= 6). Si ninguna gana, el nodo D8 va a `OUT_MIXED`.
Causa de una variable = decisiones cuyo efecto la cambió (valor anterior distinto del nuevo).

## Recorrido 1: desenlace OUT_SOLID

| Decisión | Alternativa | Razones | Efectos | P | A | Q |
|---|---|---|---|--:|--:|--:|
| inicio | | | | 5 | 5 | 5 |
| D1 | o1_2923 | r1_b84c | P+2 | 7 | 5 | 5 |
| D2 | o2_c749 | | P+2, Q+1 | 9 | 5 | 6 |
| D3 | o3_a1b4 | r3_973e | A+2, Q+1 | 9 | 7 | 7 |
| D4 | o4_65c3 | | Q+1 | 9 | 7 | 8 |
| D5 | o5_7d70 | r5_763d, r5_db24 | A+1, Q+1 | 9 | 8 | 9 |
| D6 | o6_701b | | P+1, Q+2 (11→10), A+1 | 10 | 9 | 10 |
| D7 | o7_34d2 | r7_0ad4 | P+2 (12→10), Q+1 (11→10) | 10 | 9 | 10 |
| D8 | o8_d43a | r8_538a | P+2 (12→10) | 10 | 9 | 10 |

- Eventos: ninguno (A = 9 al salir de D6; P = 10 al salir de D7).
- Transición ganadora: `tr_solid`. `tr_crisis` es falsa (P > 3 y A > 3).
- Causas de `tr_solid`: P, D1, D2, D6 (D7 y D8 no la cambiaron: 10→10); A, D3, D5, D6; Q, D2, D3, D4, D5, D6 (D7: 10→10). Unión: D1, D2, D3, D4, D5, D6.
- Justificaciones: todas correctas (D5 con dos razones correctas, el mínimo).
- Desenlace: `OUT_SOLID`.

## Recorrido 2: desenlace OUT_MIXED

| Decisión | Alternativa | Razones | Efectos | P | A | Q |
|---|---|---|---|--:|--:|--:|
| inicio | | | | 5 | 5 | 5 |
| D1 | o1_5a9a | r1_b84c, r1_81cb | P+1, A+1 | 6 | 6 | 5 |
| D2 | o2_2a86 | | P+1 | 7 | 6 | 5 |
| D3 | o3_509f | r3_973e | A+1 | 7 | 7 | 5 |
| D4 | o4_65c3 | | Q+1 | 7 | 7 | 6 |
| D5 | o5_b24e | r5_763d, r5_a786 | Q+1 | 7 | 7 | 7 |
| D6 | o6_ed23 | | P-2, Q+1 | 5 | 7 | 8 |
| D7 | o7_485f | r7_0ad4 | P-1 | 4 | 7 | 8 |
| D8 | o8_d43a | r8_538a | P+2 | 6 | 7 | 8 |

- Eventos: solo `ev_leak` (al salir de D7: P = 4). `ev_access` no (A = 7 al salir de D6).
- Causas de `ev_leak`: cambiaron P las decisiones D1 (5→6), D2 (6→7), D6 (7→5) y D7 (5→4). Causas: D1, D2, D6, D7.
- Al salir de D8 (P = 6, A = 7, Q = 8): `tr_crisis` falsa, `tr_solid` falsa (P < 7). Ninguna transición: va a `OUT_MIXED` por el destino predeterminado de D8.
- Justificaciones: todas correctas.
- Desenlace: `OUT_MIXED`.

## Recorrido 3: desenlace OUT_CRISIS

| Decisión | Alternativa | Razones | Efectos | P | A | Q |
|---|---|---|---|--:|--:|--:|
| inicio | | | | 5 | 5 | 5 |
| D1 | o1_1fba | r1_bb73 | P-2 | 3 | 5 | 5 |
| D2 | o2_808f | | P-3 | 0 | 5 | 5 |
| D3 | o3_9a36 | r3_973e, r3_7688 | A-2 | 0 | 3 | 5 |
| D4 | o4_19ff | | Q-2 | 0 | 3 | 3 |
| D5 | o5_2565 | r5_763d | A-2, Q-1 | 0 | 1 | 2 |
| D6 | o6_9abb | | Q-3 (-1→0) | 0 | 1 | 0 |
| D7 | o7_b8f2 | r7_0ad4 | P-3 (-3→0, sin cambio) | 0 | 1 | 0 |
| D8 | o8_0923 | r8_03af | P-3 (-3→0, sin cambio) | 0 | 1 | 0 |

- Eventos, en orden: `ev_access` al salir de D6 (A = 1) con causas D3 (5→3) y D5 (3→1);
  `ev_leak` al salir de D7 (P = 0) con causas D1 (5→3) y D2 (3→0); D7 no cuenta porque 0→0.
- Transición ganadora: `tr_crisis` (prioridad 10, gana a `tr_solid`, que es falsa). Sus dos partes son verdaderas:
  P <= 3 (causas D1, D2) y all(A <= 3, Q <= 4) (A: D3, D5; Q: D4 (5→3), D5 (3→2), D6 (2→0)).
  Unión: D1, D2, D3, D4, D5, D6.
- Justificaciones: D1 incorrecta (razón incorrecta), D3 incorrecta (mezcla), D5 incorrecta (una razón correcta, mínimo 2),
  D7 correcta, D8 incorrecta (razón incorrecta).
- Desenlace: `OUT_CRISIS`.

## Notas

- Las claves de alternativas y razones son neutras (no revelan orden ni acierto). Alternativas elegidas sin razones: D2, D4 y D6 no piden justificación.
- Hacia el cliente no salen valores ni causas; la API solo muestra los eventos (título y texto) y el desenlace.
