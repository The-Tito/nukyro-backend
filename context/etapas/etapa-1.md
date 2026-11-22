# Etapa 1 · Cierre documental: análisis y plan

> Estado: aprobado por el usuario el 2026-11-22 (D-12). Tareas: T-02, T-03, T-04. Conflicto: CONF-14.

## Objetivo

Que los documentos vigentes digan lo mismo que el KG antes de construir sobre ellos.

## Situación actual

- Los Términos v1.0 citan el Aviso 2.1 y solo describen el uso con cuenta (CONF-14, pendiente).
- El reporte técnico afirma tres prácticas que, según el handoff del 2026-11-01, el equipo no decidió.
- El índice de requerimientos v1.1 no se regeneró (DOC-REQ11) y el del reporte v1 depende de abrirlo en Word.
- Los documentos tienen sha256 en el KG: editarlos en su sitio hace fallar el validador (Regla 2).

## Análisis

**T-02 · Términos.**
- A: versión 1.1 completa con control de cambios. Deja un solo texto vigente, pero hay que revisarlo entero.
- B: adenda a la 1.0. Es más rápida, pero obliga a leer dos documentos.
- **Recomendación: A**, que además es lo que pide la resolución de CONF-14.

**T-03 · Prácticas del reporte.**
- A: confirmar cada una con el equipo. Evita afirmar lo no decidido, pero depende de otras personas.
- B: retirarlas en una v2.1. No depende de nadie, pero pierde medidas útiles y obliga a reentregar.
- **Recomendación: A**, y B solo para las que se rechacen.

**T-04 · Índices.**
- A: versión nueva solo de requerimientos, porque el reporte v1 ya está reemplazado.
- B: versión nueva de ambos. Es más trabajo sobre un documento sin vigencia.
- **Recomendación: A.**

## Riesgos

- Es un texto legal: el asistente redacta y el usuario aprueba.
- El cambio relevante del Aviso 2.2 debe avisarse en la plataforma y, a quien tenga cuenta, por correo (§14 del Aviso, verificado). Comprobar si ya hay cuentas.

## Plan breve

| Paso | Qué | Entregable | Cómo se verifica |
|---|---|---|---|
| 1 | Listar cláusulas que cambian | Tabla cláusula, hoy, propuesta | La aprueba el usuario |
| 2 | Redactar Términos v1.1 | Documento nuevo | Criterios de T-02 y auditor |
| 3 | Registrar la versión | KG y CONF-14 | `python3 context/validar_kg.py` |
| 4 | Confirmar las tres prácticas | Decisiones D-xx | Respuesta del equipo |
| 5 | Regenerar el índice | Requerimientos con versión nueva | Revisión en Word y validador |

## Decisiones del usuario

- Aprobar este plan y las tres recomendaciones: hecho (D-12).
- Aprobar el texto legal.
- Indicar fechas de entrega y rúbrica, si existen.

## Criterios de cierre

T-02, T-03 y T-04 cerradas por el usuario y CONF-14 resuelto.
