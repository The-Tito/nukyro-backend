# Trazabilidad de la etapa 5 (T-17 a T-19): RF, prueba positiva y prueba negativa

Fuente: etapa-5, «Criterios por RF». Prefijos: `U` unitarias (`tests/unit/test_identity.py`), `I` integración
(`tests/integration/test_identity.py`, `test_account.py`), `B` caja negra (`tests/blackbox/test_account.py`), `S` SQL
(`bd/pruebas/pruebas-defectos.sql`, pruebas L-01 a L-19) y `C` concurrencia (`bd/pruebas/pruebas-concurrencia.sh`, CC5 y CC6).

| RF | Prueba positiva | Prueba negativa |
|---|---|---|
| RF-074 | I `test_rf074_el_primer_inicio_crea_la_cuenta_con_las_casillas_sin_marcar`, I `test_rf074_las_casillas_marcadas_se_guardan_y_quedan_en_el_historial`, I `test_rf074_el_nickname_no_es_unico`, I `test_rf074_el_correo_y_el_nickname_se_sincronizan_con_cognito`, B `test_rf074_rf075_crear_la_cuenta_aceptar_iniciar_y_reanudar_desde_otro_dispositivo` | I `test_rf074_sin_correo_verificado_no_se_crea_la_cuenta`, I `test_rf074_un_token_sin_correo_o_nickname_validos_no_crea_cuenta`, I `test_rf074_el_cuerpo_rechaza_campos_desconocidos`, I `test_rf074_los_inicios_simultaneos_dejan_una_cuenta_y_un_participante`, I `test_rf074_repetir_el_inicio_no_duplica_ni_cambia_las_casillas`, B `test_rf074_un_token_invalido_o_sin_correo_verificado_no_entra` |
| RF-075 | I `test_rf075_la_cuenta_acepta_documentos_inicia_sesion_y_la_reanuda_desde_otro_dispositivo`, I `test_rf075_get_account_devuelve_lo_de_quien_pregunta`, I `test_rf075_aceptar_dos_veces_no_crea_otro_participante`, B `test_rf074_rf075_crear_la_cuenta_aceptar_iniciar_y_reanudar_desde_otro_dispositivo` | I `test_rf075_un_token_invalido_no_abre_ninguna_ruta` (firma, clave, emisor, audiencia, tipo, edad, vida y grupo), I `test_rf075_un_encabezado_malo_es_401_y_no_cae_a_la_cookie`, I `test_rf075_las_rutas_de_cuenta_no_aceptan_la_cookie`, I `test_rf075_sin_haber_iniciado_sesion_la_cuenta_no_existe`, I `test_rf075_una_cuenta_sin_documentos_aceptados_no_inicia_sesion`, B `test_rf075_sin_token_ni_cookie_no_hay_acceso`, U `test_identity.py` (37 casos del verificador, T-17) |
| RF-076 | S L-01 a L-03 (`linked`, sin secreto, repetirla no hace nada), S L-05, L-06 y L-08 (`merged`: sesiones, aceptaciones y exclusión), I `test_rf076_crear_la_cuenta_conserva_el_progreso_e_invalida_la_cookie`, I `test_rf076_repetir_el_inicio_con_la_misma_cookie_no_cambia_nada`, B `test_rf076_crear_la_cuenta_conserva_el_progreso_y_la_cookie_deja_de_servir`, C CC5 (dos vinculaciones del mismo navegador: una traslada y la otra no hace nada) | S L-11 (cuenta bloqueada, 23514), S L-12 (cuenta inexistente, P0002), S L-13 a L-15, S L-16 a L-19 (permisos y SECURITY DEFINER), I `test_d20_vincular_a_una_cuenta_bloqueada_no_mueve_el_progreso`, I `test_rf076_la_cookie_de_otra_cuenta_no_se_vincula_a_quien_no_es_su_dueno` |
| RF-077 y defecto 9 | S L-04 y L-07 (de dos primeras sesiones a una), S L-09 (la del navegador más antigua es la primera), S L-10 (otro escenario no se mezcla), I `test_defecto9_la_cuenta_con_progreso_y_un_navegador_con_progreso_dejan_una_primera_sesion`, I `test_defecto9_si_la_sesion_del_navegador_es_mas_antigua_ella_es_la_primera`, B `test_rf077_rf076_dos_primeras_sesiones_se_vuelven_una_al_vincular` | I `test_defecto9_las_vinculaciones_simultaneas_dejan_una_sola_primera_sesion`, C CC6 (vincular contra una sesión que se inicia). Visto en rojo con el recálculo quitado: `bd/pruebas/evidencia-rojo.md` |
| RF-062 y T-19 | I `test_t19_con_token_y_cookie_manda_el_token`, I `test_t19_lo_ajeno_da_404_y_no_cambia_nada` (cada ruta con `session_id`, dueño anónimo o con cuenta contra intruso anónimo o con cuenta; la misma petición del dueño no da 404), I `test_t19_las_rutas_propias_solo_devuelven_lo_de_quien_llama`, I `test_t19_sin_credenciales_la_entrada_crea_un_participante_nuevo_y_no_toca_a_nadie` | I `test_t19_lo_inexistente_da_el_mismo_404_que_lo_ajeno`, I `test_t19_sin_credenciales_es_401_y_no_escribe`, I `test_t19_una_escritura_de_origen_ajeno_se_rechaza_con_las_credenciales_del_dueno` (origen ajeno, `null`, cabecera en 0 o vacía) y `test_t19_una_escritura_sin_origen_o_sin_cabecera_se_rechaza`, B `test_t19_la_sesion_de_otra_cuenta_es_404_y_la_escritura_ajena_es_403`, I `test_rf062_la_escritura_con_token_exige_origin_y_cabecera` |
| T-19, inventario | U `test_todas_las_rutas_estan_en_el_inventario_y_el_inventario_no_tiene_sobrantes`, U `test_el_tipo_de_cada_ruta_coincide_con_su_forma` | U `test_toda_ruta_que_no_es_publica_autentica_en_su_manejador`, U `test_las_rutas_publicas_no_leen_credenciales`. Visto fallar al agregar una ruta sin registrar y al quitarle `authenticate` a una ruta |
| ADR-008 §6, GET | I `test_t19_un_get_autenticado_solo_renueva_la_actividad` (cada GET: nada cambia salvo `last_activity_at`) | I `test_t19_las_respuestas_no_se_pueden_leer_desde_otro_origen` (sin CORS, el preflight no se acepta) |
| D-20 | I `test_d20_una_cuenta_bloqueada_no_inicia_sesion_ni_usa_ninguna_ruta`, I `test_t19_una_cuenta_bloqueada_no_usa_ninguna_ruta` (las 14 rutas con identidad, `submit_survey` incluida: 403 `account_blocked` y nada cambia) | S L-11, I `test_d20_vincular_a_una_cuenta_bloqueada_no_mueve_el_progreso` |

**Defecto 12 (T-18, D-35, A-06).** S D12-01 a D12-04 comprueban el rechazo de plazos menores,
el mínimo exacto y la espera de la purga. I `test_defecto12_el_token_anterior_al_bloqueo_no_recrea_la_cuenta`
recorre inicio, bloqueo y purga con el mismo token. Resultado en rojo en `bd/pruebas/evidencia-rojo.md`.

## Sabotajes de T-19 (cada uno hace fallar la prueba indicada)

| Sabotaje | Prueba que falla |
|---|---|
| Lectura de la sesión sin el filtro del dueño (simulación) | `test_t19_lo_ajeno_da_404_y_no_cambia_nada[...-GET-/api/v1/sessions/{session_id}]` |
| Bloqueo de la sesión para escribir sin el dueño (decisiones y avance) | `...[...-POST-.../decisions]` |
| Evaluaciones sin el dueño (también el resumen, que usa la misma consulta) | `...[...-GET-.../assessments/{kind}]` |
| Encuesta sin el dueño | `...[...-GET-.../survey]` |
| `PUT` tratado como método seguro en el CSRF | `test_t19_una_escritura_de_origen_ajeno_se_rechaza_con_las_credenciales_del_dueno[...-PUT-...]` |
| Cuenta bloqueada tratada como activa al resolver al participante | `test_t19_una_cuenta_bloqueada_no_usa_ninguna_ruta[POST-/api/v1/participants]` |
| Ruta nueva sin inventario / ruta sin `authenticate` | las dos pruebas unitarias del inventario |
