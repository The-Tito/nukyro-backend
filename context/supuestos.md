# Supuestos

Vista del KG: si difieren, manda el KG.

| ID | Supuesto | Estado | Cómo se verifica | Etapa | Evidencia |
|---|---|---|---|---|---|
| S-01 | Los otros dos integrantes aceptan español, PR y commits sin coautoría de IA. | por_verificar | Confirmación de ambos al usuario | adopción | KG |
| S-02 | Los documentos que solo existen en local (D-09) tienen una copia fuera de esta máquina. | por_verificar | El usuario confirma dónde está la copia | E1 | KG |
| S-03 | Los 13 defectos de MODELO-DATOS.pendientes ocurren al ejecutar el esquema y los procesos. | por_verificar | una prueba que falla por cada uno | E2 a E7 | KG |
| S-04 | Lo probado en local (D-15) funcionará con Cognito y RDS reales. S1 y S2 no se probaron en este proyecto. | por_verificar | despliegue, fuera de este plan | posterior | KG |
