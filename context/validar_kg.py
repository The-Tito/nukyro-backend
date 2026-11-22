"""Valida context/proyecto/kg.json: esquema, integridad, archivos y vistas.

Uso: python3 context/validar_kg.py    (sale con código 1 si hay errores)

Lo que solo existe en local (D-09) no se comprueba en un clon sin docs/. Sus rutas pueden
llevar «*» en lugar de un dato personal: el patrón debe dar con un solo archivo.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
KG = RAIZ / "context" / "proyecto" / "kg.json"

# Seguimiento: patrón del ID -> (tipo, estados permitidos)
SEGUIMIENTO = {
    r"E\d+": ("Etapa", {"pendiente", "en_curso", "cerrada"}),
    r"T-\d{2,}": ("Tarea", {"pendiente", "en_curso", "cerrada", "descartada"}),
    r"D-\d{2,}": ("Decision", {"tomada", "reemplazada", "descartada"}),
    r"A-\d{2,}": ("Decision", {"abierta", "cerrada", "descartada"}),
    r"S-\d{2,}": ("Supuesto", {"por_verificar", "confirmado", "refutado", "resuelto"}),
    r"EV-\d{2,}": ("Evidencia", {"vigente", "obsoleta"}),
    r"CA-\d{2,}": ("CambioAlcance", {"vigente", "retirado"}),
}
TIPOS_SEGUIMIENTO = {"Etapa", "Tarea", "Supuesto", "Evidencia", "CambioAlcance"}
RUTA = re.compile(r"(docs|bd|context)/.+\.\w{2,5}")
SOLO_LOCAL = re.compile(r"docs/.+|bd/presentacion/[^/]+\.docx")


def revisar_seguimiento(nodo: dict) -> list[str]:
    regla = next((r for p, r in SEGUIMIENTO.items() if re.fullmatch(p, nodo["id"])), None)
    if not regla:
        return ["ID con formato inválido"] if nodo["tipo"] in TIPOS_SEGUIMIENTO else []
    tipo, estados = regla
    if nodo["tipo"] != tipo or nodo.get("estado") not in estados:
        return [f"se esperaba {tipo} con estado en {sorted(estados)}"]
    ruta, buscar = nodo.get("ruta"), nodo.get("buscar")
    if not ruta or not buscar:
        return ["faltan «ruta» o «buscar»"]
    archivo = RAIZ / ruta
    if not archivo.is_file() or buscar not in archivo.read_text("utf-8", "ignore"):
        return [f"«{buscar}» no aparece en {ruta}"]
    return []


def omitir(ruta: str) -> bool:
    return bool(SOLO_LOCAL.fullmatch(ruta)) and not (RAIZ / "docs").is_dir()


def resolver(ruta: str) -> Path | None:
    hallados = list(RAIZ.glob(ruta)) if "*" in ruta else [RAIZ / ruta]
    return hallados[0] if len(hallados) == 1 and hallados[0].is_file() else None


def revisar_archivos(nodo: dict) -> list[str]:
    errores = []
    for campo, valor in nodo.items():
        if campo in ("nombre", "texto", "resumen", "nota", "validacion", "contenido"):
            continue  # prosa, no rutas
        for ruta in valor if isinstance(valor, list) else [valor]:
            if isinstance(ruta, str) and RUTA.fullmatch(ruta) and not omitir(ruta):
                if not resolver(ruta):
                    errores.append(f"{campo}: «{ruta}» no existe o no es único")
    archivo = resolver(nodo["archivo"]) if nodo.get("archivo") else None
    if archivo:
        if "sha256" in nodo and hashlib.sha256(archivo.read_bytes()).hexdigest() != nodo["sha256"]:
            errores.append("el sha256 no coincide: los documentos no se sobrescriben (Regla 2)")
        if nodo["tipo"] == "ADR":
            estado = re.search(r"^estado: *(.+)$", archivo.read_text("utf-8"), re.M)
            if not estado or estado[1].strip() != nodo.get("estado"):
                errores.append("el estado difiere entre el ADR y el KG")
    return errores


def revisar_tabla(nodos: dict[str, dict]) -> list[str]:
    tabla = RAIZ / "context" / "decisiones.md"
    if not tabla.is_file():
        return ["falta context/decisiones.md"]
    filas, errores = {}, []
    for linea in tabla.read_text("utf-8").splitlines():
        hallado = re.match(r"\|\s*([A-Z][A-Z0-9-]+)\s*\|", linea)
        if hallado and hallado[1] != "ID":
            if hallado[1] in filas:
                errores.append(f"{hallado[1]}: fila repetida en decisiones.md")
            filas[hallado[1]] = [celda.strip() for celda in linea.split("|")]
    decisiones = {i: n for i, n in nodos.items() if n["tipo"] in ("Decision", "ADR")}
    for id_ in sorted(set(filas) | set(decisiones)):
        if id_ not in decisiones:
            errores.append(f"{id_}: está en decisiones.md y no en el KG")
        elif id_ not in filas:
            errores.append(f"{id_}: está en el KG y no en decisiones.md")
        elif re.fullmatch(r"[DA]-\d+", id_) and decisiones[id_].get("estado") not in filas[id_]:
            errores.append(f"{id_}: el estado difiere entre el KG y decisiones.md")
    return errores


def validar(kg: dict) -> list[str]:
    lista, aristas, conflictos = kg["nodos"], kg["aristas"], kg["conflictos"]
    tipos, relaciones = set(kg["esquema"]["tipos_nodo"]), set(kg["esquema"]["tipos_relacion"])
    errores, nodos = [], {}
    for i, nodo in enumerate(lista):
        if not {"id", "tipo", "nombre", "fuente"} <= set(nodo):
            errores.append(f"nodo #{i}: faltan id, tipo, nombre o fuente")
            continue
        id_ = nodo["id"]
        if id_ in nodos:
            errores.append(f"{id_}: ID repetido")
        nodos[id_] = nodo
        if nodo["tipo"] not in tipos:
            errores.append(f"{id_}: tipo desconocido «{nodo['tipo']}»")
        errores += [f"{id_}: {e}" for e in revisar_seguimiento(nodo) + revisar_archivos(nodo)]
    for id_, nodo in nodos.items():
        for fuente in nodo["fuente"]:
            if fuente["doc"] != "DECISION-USUARIO" and fuente["doc"] not in nodos:
                errores.append(f"{id_}: la fuente «{fuente['doc']}» no existe")
    for arista in aristas:
        de, rel, a = arista.get("origen"), arista.get("relacion"), arista.get("destino")
        if rel not in relaciones:
            errores.append(f"arista {de}->{a}: relación desconocida «{rel}»")
        for extremo in (de, a):
            if extremo not in nodos:
                errores.append(f"arista {de}->{a}: «{extremo}» no existe")
    for conflicto in conflictos:
        if conflicto["estado"] not in ("resuelto", "propuesta", "pendiente"):
            errores.append(f"{conflicto['id']}: estado no válido")
        for id_ in conflicto.get("afecta", []):
            if id_ not in nodos:
                errores.append(f"{conflicto['id']}: afecta a «{id_}», que no existe")
    resumen = kg["estadisticas"]
    estados = Counter(c["estado"] for c in conflictos)
    if (
        (resumen["nodos"], resumen["aristas"], resumen["conflictos"])
        != (len(lista), len(aristas), len(conflictos))
        or Counter(resumen["por_tipo"]) != Counter(n.get("tipo") for n in lista)
        or Counter(resumen["conflictos_por_estado"]) != estados
    ):
        errores.append("«estadisticas» no coincide con el contenido")
    if kg["meta"]["historial"][-1]["version"] != kg["meta"]["version"]:
        errores.append("meta.version no es la última de meta.historial")
    return errores + revisar_tabla(nodos)


if __name__ == "__main__":
    if not (RAIZ / "docs").is_dir():
        print("kg: aviso, sin docs/ no se comprueban los documentos locales (D-09)", file=sys.stderr)
    problemas = validar(json.loads(KG.read_text("utf-8")))
    for problema in problemas:
        print(f"kg: {problema}")
    sys.exit(1 if problemas else 0)
