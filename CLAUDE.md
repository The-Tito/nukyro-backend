# Nukyro — Reglas del proyecto

Simulador educativo para la toma de decisiones éticas en el desarrollo de software (MVP 1.0).
Este repositorio contiene el backend, su base de datos y el contexto del proyecto (D-04).

## Regla 1 · Única fuente de verdad: el Knowledge Graph

El archivo `context/proyecto/kg.json` es la **única fuente de verdad** del proyecto Nukyro
(Simulador Educativo para la Toma de Decisiones Éticas en el Desarrollo de Software).

1. **Consultar primero el KG.** Antes de responder, diseñar, modelar datos, escribir código o
   redactar contenido sobre el proyecto, se consulta `context/proyecto/kg.json`. Lo que no esté
   en el KG no se da por hecho: se pregunta al usuario.
2. **El KG prevalece sobre los documentos.** Los archivos de `docs/` y `versiones/` son material
   de origen. Si un documento y el KG difieren, manda el KG. Si se detecta que el KG está
   desactualizado respecto de un documento nuevo, se avisa al usuario y se actualiza el KG;
   no se usa el documento directamente.
3. **Conflictos.** La sección `conflictos` del KG registra contradicciones entre documentos.
   - `resuelto`: usar la resolución indicada.
   - `propuesta` o `pendiente`: no decidir por cuenta propia; mencionar el conflicto (por su id,
     p. ej. `CONF-02`) y pedir confirmación al usuario antes de actuar sobre los nodos afectados.
   - Al confirmarse una decisión, actualizar el conflicto a `resuelto` con la decisión tomada.
4. **Toda información nueva entra al KG.** Decisiones, cambios de alcance o requerimientos
   nuevos se agregan al KG (nodo o arista) con su `fuente` (`{doc, seccion}`; para decisiones
   del usuario usar `{"doc": "DECISION-USUARIO", "seccion": "<fecha AAAA-MM-DD>"}`), y se
   incrementa `meta.version`.
5. **Integridad del KG.** Debe seguir siendo JSON válido; los ids son únicos; cada arista
   apunta a nodos existentes; los ids `RF-`, `RN-`, `RNF-`, `RIU-`, `RIH-`, `RIS-`, `RIC-`,
   `OR-`, `REF-`, `H0`, `FUN-` conservan la numeración del documento de requerimientos.
6. **Citar por id.** Al referirse a requerimientos, reglas o conflictos se citan sus ids del KG.

## Estructura de `context/`

- `HANDOFF.md` e `HISTORIAL.md` (raíz, locales, sin versionar) — lo vigente y lo que dejó de serlo; orientan, pero manda el KG (D-03).
- `context/{plan,decisiones,supuestos,cambios-alcance,fuentes}.md` — vistas del KG (D-02). `bitacora.md`, `estudio.md` y `etapas/` guardan el detalle del trabajo. Ver `context/README.md`.
- `context/proyecto/kg.json` — el Knowledge Graph (`meta`, `esquema`, `estadisticas`, `nodos`, `aristas`, `conflictos`). `meta.historial` registra los cambios de cada versión.
- `context/evaluaciones/` — evaluaciones que alimentan decisiones (p. ej. `evaluacion-motor-bd.md` + `.json` reejecutable con la skill `evaluar-motor-bd`).
- `context/adr/` — registro de decisiones de arquitectura (ADR), con índice en `context/adr/README.md`. Cada ADR también es un nodo del KG (tipo `ADR`); si difieren, manda el KG y se corrige el ADR. Toda decisión difícil de revertir se registra como ADR nuevo y como nodo del KG.

## Regla 2 · Documentos fuente versionados

`docs/` es solo local (D-09): no entra a git y se respalda por otro medio. Nunca `git clean -x` ni `-X`.
Los documentos de `docs/` no se sobrescriben: un cambio produce una versión nueva (p. ej. `..._v1.1.docx`) con su sección de control de cambios, y el KG registra la nueva versión como `Documento` vigente y la anterior como `reemplazado`.

## Sesiones

- **Retomar** (`/retomar`, o «verifica dónde lo dejamos»): `.claude/commands/retomar.md`. Se lee solo
  `HANDOFF.md`, nunca el HISTORIAL, y se contrasta con git y el KG.
- **Fase** (`/fase planear|comprobar|cerrar N`): `.claude/commands/fase.md`.
- **Cerrar** (`/cerrar`): `.claude/commands/cerrar.md`.
- **Lectura económica:** el KG se consulta con `jq`; los documentos largos, con `grep -n` y por rango.

## Reglas no negociables (D-06)

1. El servidor decide las consecuencias; el cliente no (ARQ).
2. No se califica la moralidad del participante ni se usa IA generativa en el producto (PROY).
3. Justificaciones sin texto libre y solo mayores de 18 años (MENORES).
4. Ningún código ético o estándar se presenta como ley (POL-REFERENCIAS).
5. Todo cambio al esquema pasa las pruebas de `bd/pruebas/`.
6. No se inventan datos ni resultados. Lo no probado se dice; lo que no se sabe se registra como supuesto.
7. Un fallo o una opción inviable se reporta; no se sustituye en silencio.

## Forma de trabajo

1. **Plan por etapa:** `context/etapas/etapa-N.md`, aprobado antes del primer paso.
2. **Explicar antes:** qué, por qué y qué concepto o riesgo hay detrás.
3. **Dos puertas (D-22), de E2 a E8:** Reafirmar, planear, Puerta A, construir, comprobar, Puerta B. Entre puertas solo
   se detiene por conflicto, desvío, permiso o bloqueo. Fuera de esas fases, un paso a la vez.
   Mientras rija D-24 el asistente pasa las puertas como «delegada»; lo que D-24 no delega se bloquea y se reporta.
4. **Mostrar:** lo creado, el comando para comprobarlo y el resultado esperado.
5. **El usuario cierra las tareas**, salvo delegación vigente (D-24). Antes de cerrar un entregable se usa el agente `auditor`.
6. **Ninguna decisión se pierde:** va al KG y a su vista en el mismo commit. Cada paso, a `context/bitacora.md`.
7. **Para defender:** al cerrar, proponer 2 o 3 preguntas con respuesta para `context/estudio.md`.
8. **Registro de IA:** skill `registro-ia` al cerrar cada tarea y sesión.

## Decisiones

- Recomendar una opción. Los detalles menores se deciden y se declaran.
- **Preguntar antes** de resolver conflictos o cambiar alcance, stack, dependencias importantes, textos
  legales, datos personales o su conservación; de gastar en AWS; de algo irreversible; y de publicar o entregar.
- Documentos, comentarios y mensajes en español; identificadores técnicos en inglés (DEC-IDIOMA-ID).

## Git

- **Gitflow:** `main` (versiones etiquetadas), `develop` (integración), `feature/T-xx-<descripcion>`
  (sale de `develop` y vuelve por PR), `release/x.y.z`, `hotfix/x.y.z`.
- Verificar la rama antes de editar. Una rama por entregable. D-11, hasta que el usuario la revoque: el asistente sube la rama, crea y fusiona los PR; al revocarla, el usuario revisa y fusiona.
- Un commit por implementación, Conventional Commits en español: `tipo(alcance): descripción (T-xx, D-xx)`.
- Sin coautoría ni líneas de atribución de IA en commits o PR.
- Sin commit ni push si el usuario no lo pide (D-24 los autoriza para E2 a E8 mientras rija). Sin push directo a `main` ni `develop`, salvo la fusión de D-11. Nunca `--no-verify`.
- Fusión (D-11): con el PR abierto, `git merge --no-ff` local en `develop` y push. Nunca `gh pr merge` ni el botón de GitHub: publican nombre y correo del perfil (ADR-006).
- Nunca secretos ni datos personales en git: el remoto es público (D-09). Personas por id `PER-xx`; firma `The-Tito` con noreply (D-10).

## Entorno y comandos

PostgreSQL 16 (RDS; Docker en local), FastAPI, SQLAlchemy 2.x, Alembic y psycopg 3 (DEC-STACK). Código en `src/nukyro/` (ADR-008).

| Qué | Comando |
|---|---|
| Activar revisiones (una vez por clon) | `pre-commit install` |
| Revisar lo preparado | `pre-commit run` |
| Buscar secretos en el historial | `pre-commit run gitleaks-historial --hook-stage manual` |
| Validar el KG | `python3 context/validar_kg.py` |
| Verificar todo el backend | `./scripts/verify` |
| Probar solo la base | `bd/pruebas/ejecutar.sh` |
| Regenerar la migración inicial | `python3 scripts/freeze_schema.py` (solo antes del primer despliegue) |
