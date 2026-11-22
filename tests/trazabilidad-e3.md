# Trazabilidad de la etapa 3: RF, prueba positiva y prueba negativa

Fuente: etapa-3, «Criterios por RF». RF-066 queda para T-12. Prefijos: `B` caja negra
(`tests/blackbox/test_simulation.py`), `I` integración (`tests/integration/test_simulation.py`),
`U` unitarias (`tests/unit/test_engine.py` y `tests/unit/test_simulation_schemas.py`).

| RF | Prueba positiva | Prueba negativa |
|---|---|---|
| RF-006 | B `test_rf006_otra_peticion_con_la_cookie_retoma_el_ultimo_nodo_confirmado` | B `test_rf006_otra_cookie_es_404_y_una_decision_revertida_no_avanza` |
| RF-013 | B `test_rf013_la_intro_muestra_titulo_y_contexto_del_escenario` | B `test_rf013_la_intro_no_expone_reglas_ni_variables` |
| RF-014, RF-015 | U `test_un_evento_en_la_ruta_si_avanza`, U `test_rf014_rf015_la_entrada_valida_solo_lleva_nodo_alternativa_y_razones`, B `test_rf014_rf015_la_ruta_recorre_narrativo_decision_evento_y_desenlace` | U `test_rf014_rf015_un_destino_o_fecha_del_cliente_se_rechaza`, B `test_rf014_rf015_un_destino_enviado_por_el_cliente_es_422_y_no_mueve_nada` |
| RF-016 | B `test_rf016_avanzar_mueve_un_nodo_y_repetir_no_mueve_otro` | B `test_rf016_con_el_pretest_pendiente_avanzar_es_409` |
| RF-017, RF-024 | B `test_rf017_rf024_con_decision_y_razones_exigidas_se_continua`, I `test_rf064_cuatro_recorridos_persisten_valores_causas_y_final` | B `test_rf017_rf024_sin_decision_es_409_y_sin_razones_exigidas_es_422_sin_cambios`, I `test_cada_invalido_deja_cero_cambios` |
| RF-018, RF-038 | B `test_rf018_rf038_el_desenlace_se_muestra_y_marca_el_fin` | B `test_rf018_rf038_avanzar_desde_el_desenlace_es_409` |
| RF-019 | B `test_rf019_se_listan_las_alternativas_y_razones_del_nodo_actual` | B `test_rf019_las_alternativas_no_llevan_efectos_destinos_ni_razones_correctas` |
| RF-020, RF-021, RF-022 | I `test_rf020_rf021_rf022_queda_la_alternativa_con_la_hora_del_servidor` | I `test_rf020_rf021_rf022_alternativa_de_otro_nodo_o_fecha_del_cliente_es_422` |
| RF-023, RF-025 | U `test_justification`, I `test_rf023_rf025_las_razones_quedan_ligadas_a_la_decision` | U `test_rejections`, I `test_rf023_rf025_razon_de_otro_nodo_repetida_o_no_pedida_es_422` |
| RF-026, RF-027 | I `test_rf026_rf027_cada_sesion_parte_de_los_valores_iniciales` | I `test_rf026_rf027_una_sesion_no_cambia_la_de_otro_participante` |
| RF-028, RF-029 | U `test_clamp_keeps_previous_value`, I `test_rf028_rf029_los_efectos_se_aplican_en_orden_con_limites_tras_registrar` | U `test_rejections`, I `test_rf028_rf029_una_peticion_invalida_deja_las_variables_iguales` |
| RF-030, RF-031 | U `test_adr_examples` (caso AC: el evento ve p ya actualizada) | U `test_adr_examples` (casos BC y BD: sin evento), U `test_precedence` (transición falsa) |
| RF-032 | U `test_precedence` (alternativa y predeterminado sin regla verdadera) | U `test_precedence` (una regla verdadera prevalece) |
| RF-033, RF-034, RF-065 | U `test_causes`, I `test_rf033_rf034_rf065_el_evento_guarda_la_regla_y_las_decisiones_causantes` | U `test_causes` (rama falsa del `any`), I `test_rf033_rf034_rf065_no_atribuye_una_rama_falsa_ni_otra_sesion` |
| RF-035 | B `test_rf035_los_eventos_son_solo_texto_narrativo_del_contenido` | B `test_rf035_ninguna_respuesta_lleva_valores_de_variables` |
| RF-036, RF-037 | U `test_adr_examples` (los cuatro ejemplos de ADR-009) | U `test_input_not_mutated_and_deterministic` |
| RF-063 | I `test_rf063_secreto_nodo_version_y_alternativa_validos_confirman` | I `test_cada_invalido_deja_cero_cambios` |
| RF-064 | I `test_mil_pares_concurrentes_no_duplican_nada`, I `test_defecto1_reintento_tras_avanzar_con_otra_alternativa_devuelve_lo_confirmado` | I `test_un_fallo_en_cada_escritura_deja_cero_cambios` |

Nota: `test_precedence` y `test_adr_examples` cubren el positivo y el negativo en casos de una misma prueba
parametrizada o secuencial, no en pruebas separadas.

Vivacidad (no es un RF de la tabla): I `test_decidir_y_borrar_al_participante_a_la_vez_no_se_interbloquean`.
