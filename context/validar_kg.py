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
import unicodedata
from collections import Counter
from fnmatch import fnmatchcase
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


def es_local(ruta: str) -> bool:
    return ".." not in ruta and bool(SOLO_LOCAL.fullmatch(ruta))


def omitir(ruta: str) -> bool:
    return es_local(ruta) and not (RAIZ / "docs").is_dir()


def resolver(ruta: str) -> Path | None:
    hallados = [RAIZ / ruta]
    if es_local(ruta):  # solo estas rutas admiten «*»
        carpeta, _, patron = ruta.rpartition("/")
        # macOS puede guardar las tildes descompuestas: se comparan en NFC
        nfc = lambda texto: unicodedata.normalize("NFC", texto)
        hallados = [a for a in (RAIZ / carpeta).glob("*") if fnmatchcase(nfc(a.name), nfc(patron))]
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


ENCABEZADOS_PLAN = ("## Reafirmación", "## Dictamen", "## Criterios por RF", "## Puerta A", "## Puerta B")


def revisar_puerta(puerta, num: int, nodos: dict[str, dict], plan: bool) -> list[str]:
    if not isinstance(puerta, dict):
        return ["falta o está mal tipada"]
    errores = []
    estado, fecha, dec = (puerta.get(c) for c in ("estado", "fecha", "decision"))
    if estado not in ("aprobada", "delegada"):
        errores.append("«estado» debe ser aprobada o delegada")
    if not (isinstance(fecha, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha)):
        errores.append("«fecha» debe ser AAAA-MM-DD")
    if not (isinstance(dec, str) and nodos.get(dec, {}).get("tipo") == "Decision" and nodos[dec].get("estado") == "tomada"):
        errores.append("«decision» debe ser una Decision con estado tomada")
    if plan:
        ruta = puerta.get("plan")
        if ruta != f"context/etapas/etapa-{num}.md":
            errores.append(f"«plan» debe ser context/etapas/etapa-{num}.md")
        elif not (RAIZ / ruta).is_file():
            errores.append(f"«plan» {ruta} no existe")
        else:
            texto = (RAIZ / ruta).read_text("utf-8", "ignore")
            errores += [f"«plan» no tiene el encabezado «{h}»" for h in ENCABEZADOS_PLAN if h not in texto]
    return errores


def revisar_fases(nodos: dict[str, dict], aristas: list[dict]) -> list[str]:
    errores = []
    etapas = {i for i, n in nodos.items() if n["tipo"] == "Etapa"}
    for id_, nodo in nodos.items():
        if nodo["tipo"] == "RequerimientoFuncional" and nodo.get("mvp") is not False:
            destinos = [a.get("destino") for a in aristas if a.get("origen") == id_ and a.get("relacion") == "se_planea_en"]
            if len(destinos) != 1 or destinos[0] not in etapas:
                errores.append(f"{id_}: debe tener exactamente una arista se_planea_en hacia una Etapa (tiene {destinos})")
    for id_, etapa in nodos.items():
        num = re.fullmatch(r"E(\d+)", id_)
        if etapa["tipo"] != "Etapa" or not num or int(num[1]) < 2:
            continue
        n, estado = int(num[1]), etapa.get("estado")
        if estado in ("en_curso", "cerrada"):
            errores += [f"{id_}: puerta_a {e}" for e in revisar_puerta(etapa.get("puerta_a"), n, nodos, True)]
            if n >= 3 and nodos.get(f"E{n - 1}", {}).get("estado") != "cerrada":
                errores.append(f"{id_}: la etapa anterior E{n - 1} no está cerrada")
        if estado == "cerrada":
            errores += [f"{id_}: puerta_b {e}" for e in revisar_puerta(etapa.get("puerta_b"), n, nodos, False)]
            if not any(
                a.get("relacion") == "respalda" and a.get("destino") == id_
                and nodos.get(a.get("origen"), {}).get("tipo") == "Evidencia"
                and nodos[a["origen"]].get("estado") == "vigente"
                and all(isinstance(nodos[a["origen"]].get(c), str) and nodos[a["origen"]][c].strip() for c in ("commit", "comando", "resultado"))
                for a in aristas
            ):
                errores.append(f"{id_}: sin Evidencia vigente (con commit, comando y resultado) que la respalde")
            for a in aristas:
                tarea = nodos.get(a.get("origen"), {})
                if a.get("relacion") == "pertenece_a" and a.get("destino") == id_ and tarea.get("tipo") == "Tarea" \
                        and tarea.get("estado") in ("pendiente", "en_curso"):
                    errores.append(f"{id_}: la tarea {a['origen']} sigue {tarea['estado']}")
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
        or {e: n for e, n in resumen["conflictos_por_estado"].items() if n} != dict(estados)
    ):
        errores.append("«estadisticas» no coincide con el contenido")
    if kg["meta"]["historial"][-1]["version"] != kg["meta"]["version"]:
        errores.append("meta.version no es la última de meta.historial")
    return errores + revisar_fases(nodos, aristas) + revisar_tabla(nodos)


if __name__ == "__main__":
    if not (RAIZ / "docs").is_dir():
        print("kg: aviso, sin docs/ no se comprueban los documentos locales (D-09)", file=sys.stderr)
    problemas = validar(json.loads(KG.read_text("utf-8")))
    for problema in problemas:
        print(f"kg: {problema}")
    sys.exit(1 if problemas else 0)
