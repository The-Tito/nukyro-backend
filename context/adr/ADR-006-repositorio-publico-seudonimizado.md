---
id: ADR-006
titulo: Repositorio público con contexto seudonimizado
estado: Aceptada
fecha: 2026-11-22
decisores: usuario (DECISION-USUARIO 2026-11-22)
kg: [ADR-006, D-05, D-08, D-09, D-14, A-03, CONTACTO]
---

# ADR-006 · Repositorio público con contexto seudonimizado

## Contexto

El repositorio es público (D-08) y D-05 solo admitía datos personales en un remoto privado. El KG, los ADR y los documentos fuente nombraban a los integrantes y a la persona docente, con matrículas y un correo. Lo que se sube a un repositorio público no se puede retirar del todo (A-03).

## Decisión

- El KG y los ADR identifican a las personas con `PER-DEV-01` a `PER-DEV-03` y `PER-DOCENTE`, sin nombre, matrícula ni correo.
- Se omiten el grupo escolar y los prefijos de matrícula (D-14).
- El canal de contacto remite a su documento (`CONTACTO`).
- `docs/`, `versiones/` y los `.docx` de `bd/presentacion/` son solo locales.
- En las rutas del KG, `*` sustituye al dato personal. El validador exige que el patrón dé con un solo archivo y sigue comparando su sha256.
- Los commits se firman con la cuenta de GitHub y su correo noreply (D-08, D-10).

## Alternativas consideradas

- **Publicar con consentimiento escrito:** depende de cuatro personas y no se puede deshacer del todo.
- **Contexto en otro repositorio privado:** separa el KG del código que describe.
- **Hacer privado el repositorio:** rechazado por el usuario (D-08).

## Consecuencias

- Es seudonimización, no anonimato: la universidad, la asignatura y la cuenta de GitHub siguen visibles y permiten inferir personas.
- Los documentos fuente no tienen copia en el remoto: se respaldan y comparten por otro medio (S-02). La equivalencia de los seudónimos solo se deduce del respaldo local del KG anterior.
- En un clon sin `docs/` el validador no comprueba esos archivos y lo avisa.
- La fusión desde GitHub no respeta la firma de D-10. Por eso los PR se fusionan en local (D-11).
- Antes de cada push se revisa que no entren datos personales.

## Trazabilidad

D-09 reemplaza a D-05 y cierra A-03. Afecta a CONTACTO, a los nodos Persona y a las rutas de los nodos Documento del KG.
