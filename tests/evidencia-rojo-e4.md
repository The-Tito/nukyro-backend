# Evidencia en rojo de la etapa 4 (T-15)

Cada sabotaje fue temporal y se restauró (el archivo vuelve a su contenido; `git diff` solo muestra los cambios de T-15). Comando: `./scripts/verify` (paso integration). La línea FAILED se copió de la salida real.

## a) Puerta 409 del resumen (defecto 11, RF-057)
Sabotaje: en `src/nukyro/modules/summary/service.py`, `if row["completed_at"] is None:` pasó a `if False:`.
```
FAILED tests/integration/test_summary.py::test_rf057_defecto_11_el_resumen_es_409_hasta_terminar_las_evaluaciones
```

## b) Filtro de retroalimentación por alternativa (RF-042, RF-043)
Sabotaje: en `src/nukyro/modules/summary/queries.py`, se quitó `AND (f.option_id IS NULL OR f.option_id = d.option_id)` del JOIN de `feedback`.
```
FAILED tests/integration/test_summary.py::test_rf042_a_rf048_el_resumen_trae_lo_propio_de_cada_decision
```

No se vieron en rojo otras pruebas nuevas (resultados con total aplicable, abandonar y reanudar).
