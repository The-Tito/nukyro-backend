# Formato de entrada de `score.py`

```jsonc
{
  "proyecto": "Nombre",
  "criterios":  { "forma": 0.15, "lectura": 0.20, ... },   // opcional; por omisión, los de la rúbrica
  "parametros": {                                         // opcional
    "castigo_motor_extra": 0.30, "castigo_cruce": 0.40,
    "castigo_cruce_mitigado": 0.15, "umbral_empate": 0.15,
    "criterio_veto": "integridad", "umbral_veto": 1
  },
  "dominios": [
    { "id": "ventas", "nombre": "Venta e inventario", "peso": 0.5, "criticidad": "alta|media|baja" }
  ],
  "puntajes": {
    "ventas": {
      "postgresql": { "forma": 5, "lectura": 5, "integridad": 5, "imprevistas": 5,
                      "escala": 5, "especial": 3, "operacion": 5, "por_que": "texto libre" }
    }
  },
  "cruces": [                                             // escrituras críticas entre dominios
    { "de": "ventas", "a": "credito", "mitigado": false, "descripcion": "..." }
  ],
  "arquitecturas": [                                      // opcional; si falta se generan
    { "id": "R1", "nombre": "Solo PostgreSQL", "asignacion": { "ventas": "postgresql" } }
  ]
}
```

- Los pesos de dominio y de criterio se normalizan solos (no tienen que sumar 1).
- Cualquier llave extra (`por_que`, `_nota`) se ignora: úsala para dejar la justificación junto al número.
- Si no das `arquitecturas`, el script arma una por cada motor puntuado en todos los dominios y el
  híbrido «mejor motor por dominio».

## Ejemplos

| Archivo | Resultado esperado | Qué demuestra |
|---|---|---|
| `ferreteria.json` | Solo PostgreSQL, robusto en 17/17 escenarios | Escrituras multi-entidad con dinero: el relacional gana en todos los dominios |
| `tienda-en-linea.json` | Solo PostgreSQL con JSONB, margen 0.21; el híbrido gana solo si se ignora su costo | El híbrido gana en la suma base pero no paga su costo; la sensibilidad lo hace visible. También muestra un veto |
