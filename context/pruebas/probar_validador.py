"""Prueba revisar_fases (D-22) con KG sintéticos en una carpeta temporal; no toca el KG real.

Uso: python3 context/pruebas/probar_validador.py    (sale con código 1 si algún caso falla)
"""

from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import validar_kg as vkg  # noqa: E402

PLAN = "\n".join(vkg.ENCABEZADOS_PLAN) + "\n"
PUERTA = {"estado": "aprobada", "fecha": "2026-11-22", "decision": "D-01"}


def base() -> tuple[dict, list]:
    nodos = {
        "RF-001": {"id": "RF-001", "tipo": "RequerimientoFuncional", "mvp": True},
        "D-01": {"id": "D-01", "tipo": "Decision", "estado": "tomada"},
        "T-01": {"id": "T-01", "tipo": "Tarea", "estado": "cerrada"},
        "EV-01": {"id": "EV-01", "tipo": "Evidencia", "estado": "vigente", "commit": "abc1234", "comando": "pytest", "resultado": "ok"},
        "E1": {"id": "E1", "tipo": "Etapa", "estado": "cerrada"},
        "E2": {"id": "E2", "tipo": "Etapa", "estado": "en_curso", "puerta_a": {**PUERTA, "plan": "context/etapas/etapa-2.md"}},
        "E3": {"id": "E3", "tipo": "Etapa", "estado": "pendiente"},
    }
    aristas = [
        {"origen": "RF-001", "relacion": "se_planea_en", "destino": "E2"},
        {"origen": "T-01", "relacion": "pertenece_a", "destino": "E2"},
        {"origen": "EV-01", "relacion": "respalda", "destino": "E2"},
    ]
    return nodos, aristas


def cerrada(n, a):
    n["E2"]["estado"] = "cerrada"
    n["E2"]["puerta_b"] = dict(PUERTA)


def sin_puerta_a(n, a): del n["E2"]["puerta_a"]
def decision_falsa(n, a): n["E2"]["puerta_a"]["decision"] = "D-99"
def sin_puerta_b(n, a): cerrada(n, a); del n["E2"]["puerta_b"]
def sin_evidencia(n, a): cerrada(n, a); a.pop()
def tarea_abierta(n, a): cerrada(n, a); n["T-01"]["estado"] = "en_curso"
def puerta_mal_tipada(n, a): n["E2"]["puerta_a"] = "aprobada"
def rf_sin_fase(n, a): a.pop(0)
def rf_dos_fases(n, a): a.append({"origen": "RF-001", "relacion": "se_planea_en", "destino": "E3"})
def anterior_abierta(n, a):
    n["E3"].update(estado="en_curso", puerta_a={**PUERTA, "plan": "context/etapas/etapa-3.md"})
    n["E2"]["estado"] = "en_curso"


# (nombre, modificación, fragmento esperado en los errores; None = sin errores, plan con encabezados)
CASOS = [
    ("válido en curso", lambda n, a: None, None),
    ("válido cerrado", cerrada, None),
    ("sin Puerta A", sin_puerta_a, "E2: puerta_a falta"),
    ("puerta mal tipada", puerta_mal_tipada, "E2: puerta_a falta o está mal tipada"),
    ("decisión inexistente", decision_falsa, "«decision» debe ser una Decision"),
    ("cerrada sin Puerta B", sin_puerta_b, "E2: puerta_b"),
    ("cerrada sin evidencia", sin_evidencia, "sin Evidencia vigente"),
    ("tarea abierta", tarea_abierta, "la tarea T-01 sigue en_curso"),
    ("anterior sin cerrar", anterior_abierta, "E3: la etapa anterior E2"),
    ("RF sin fase", rf_sin_fase, "RF-001: debe tener exactamente una arista"),
    ("RF con dos fases", rf_dos_fases, "RF-001: debe tener exactamente una arista"),
]


def main() -> int:
    fallos = 0
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp)
        (raiz / "context" / "etapas").mkdir(parents=True)
        (raiz / "context/etapas/etapa-2.md").write_text(PLAN, "utf-8")
        (raiz / "context/etapas/etapa-3.md").write_text(PLAN, "utf-8")
        vkg.RAIZ = raiz
        extra = [  # plan sin encabezado: caso aparte
            ("plan sin encabezado", "etapa-2.md", "## Reafirmación\n", "no tiene el encabezado «## Dictamen»"),
        ]
        for nombre, cambio, esperado in CASOS:
            nodos, aristas = copy.deepcopy(base())
            cambio(nodos, aristas)
            errores = vkg.revisar_fases(nodos, aristas)
            ok = not errores if esperado is None else any(esperado in e for e in errores)
            fallos += not ok
            print(f"{'OK  ' if ok else 'FALLA'} {nombre}: {errores or 'sin errores'}")
        for nombre, archivo, texto, esperado in extra:
            (raiz / "context/etapas" / archivo).write_text(texto, "utf-8")
            nodos, aristas = base()
            errores = vkg.revisar_fases(nodos, aristas)
            ok = any(esperado in e for e in errores)
            fallos += not ok
            print(f"{'OK  ' if ok else 'FALLA'} {nombre}: {errores or 'sin errores'}")
    print(f"{fallos} fallo(s)" if fallos else "todos los casos pasan")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
