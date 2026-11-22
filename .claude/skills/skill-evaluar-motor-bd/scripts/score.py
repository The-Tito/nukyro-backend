#!/usr/bin/env python3
"""Matriz ponderada para elegir motor de base de datos (un motor o híbrido).

Uso:
    python3 score.py evaluacion.json            # informe en markdown
    python3 score.py evaluacion.json --json     # resultado en JSON

Solo usa la biblioteca estándar. El formato de entrada está documentado en
examples/ y en SKILL.md (fase 5).
"""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy

CRITERIOS_DEFECTO = {
    "forma": 0.15,
    "lectura": 0.20,
    "integridad": 0.25,
    "imprevistas": 0.10,
    "escala": 0.10,
    "especial": 0.10,
    "operacion": 0.10,
}
PARAMETROS_DEFECTO = {
    "castigo_motor_extra": 0.30,
    "castigo_cruce": 0.40,
    "castigo_cruce_mitigado": 0.15,
    "umbral_empate": 0.15,
    "criterio_veto": "integridad",
    "umbral_veto": 1,
}
NOMBRES_CRITERIOS = {
    "forma": "Forma",
    "lectura": "Lectura",
    "integridad": "Integridad",
    "imprevistas": "Imprevistas",
    "escala": "Escala",
    "especial": "Especial",
    "operacion": "Operación",
}


class ErrorEntrada(Exception):
    pass


# --------------------------------------------------------------------------- carga y validación
def normalizar(pesos: dict) -> dict:
    total = sum(pesos.values())
    if total <= 0:
        raise ErrorEntrada("La suma de pesos debe ser mayor que cero.")
    return {k: v / total for k, v in pesos.items()}


def cargar(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)

    criterios = datos.get("criterios") or dict(CRITERIOS_DEFECTO)
    if not isinstance(criterios, dict) or not criterios:
        raise ErrorEntrada("'criterios' debe ser un objeto {id: peso}.")
    parametros = {**PARAMETROS_DEFECTO, **(datos.get("parametros") or {})}

    dominios = datos.get("dominios")
    if not dominios:
        raise ErrorEntrada("Falta la lista 'dominios'.")
    ids_dom = [d["id"] for d in dominios]
    if len(set(ids_dom)) != len(ids_dom):
        raise ErrorEntrada("Hay ids de dominio repetidos.")
    for d in dominios:
        if d.get("peso", 0) <= 0:
            raise ErrorEntrada(f"El dominio '{d['id']}' necesita 'peso' > 0.")
        d.setdefault("criticidad", "media")
        if d["criticidad"] not in ("alta", "media", "baja"):
            raise ErrorEntrada(f"Criticidad inválida en '{d['id']}': usa alta, media o baja.")

    puntajes = datos.get("puntajes") or {}
    for d in ids_dom:
        if d not in puntajes or not puntajes[d]:
            raise ErrorEntrada(f"No hay puntajes para el dominio '{d}'.")
        if len(puntajes[d]) < 2:
            print(f"Aviso: el dominio '{d}' tiene un solo motor puntuado; "
                  "no hay contra qué comparar.", file=sys.stderr)
        for motor, celdas in puntajes[d].items():
            for c in criterios:
                if c not in celdas:
                    raise ErrorEntrada(f"Falta '{c}' para {motor} en el dominio '{d}'.")
                v = celdas[c]
                if not isinstance(v, (int, float)) or not 1 <= v <= 5:
                    raise ErrorEntrada(f"Puntaje fuera de 1–5: {d}/{motor}/{c} = {v!r}.")

    cruces = datos.get("cruces") or []
    for c in cruces:
        if c.get("de") not in ids_dom or c.get("a") not in ids_dom:
            raise ErrorEntrada(f"Cruce con dominio desconocido: {c}.")

    arquitecturas = datos.get("arquitecturas") or generar_arquitecturas(ids_dom, puntajes, criterios)
    for a in arquitecturas:
        for d in ids_dom:
            motor = a["asignacion"].get(d)
            if motor is None:
                raise ErrorEntrada(f"La arquitectura '{a['id']}' no asigna motor al dominio '{d}'.")
            if motor not in puntajes[d]:
                raise ErrorEntrada(f"'{motor}' no está puntuado en el dominio '{d}' "
                                   f"(arquitectura '{a['id']}').")

    return {
        "proyecto": datos.get("proyecto", "(sin nombre)"),
        "criterios": criterios,
        "parametros": parametros,
        "dominios": dominios,
        "puntajes": puntajes,
        "cruces": cruces,
        "arquitecturas": arquitecturas,
    }


def generar_arquitecturas(ids_dom, puntajes, criterios):
    """Si no se dan arquitecturas: un motor único por cada motor puntuado en todos los
    dominios, más el híbrido 'mejor por dominio'."""
    pesos = normalizar(criterios)
    comunes = set.intersection(*(set(puntajes[d]) for d in ids_dom))
    arqs = [{"id": f"solo-{m}", "nombre": f"Solo {m}", "asignacion": {d: m for d in ids_dom}}
            for m in sorted(comunes)]
    mejor = {d: max(puntajes[d], key=lambda m: puntaje_motor(puntajes[d][m], pesos)) for d in ids_dom}
    if len(set(mejor.values())) > 1:
        arqs.append({"id": "hibrido-mejor-por-dominio", "nombre": "Híbrido: mejor por dominio",
                     "asignacion": mejor})
    return arqs


# --------------------------------------------------------------------------- cálculo
def puntaje_motor(celdas: dict, pesos: dict) -> float:
    return sum(pesos[c] * celdas[c] for c in pesos)


def vetado(dominio: dict, celdas: dict, parametros: dict) -> bool:
    c = parametros["criterio_veto"]
    return dominio["criticidad"] == "alta" and c in celdas and celdas[c] <= parametros["umbral_veto"]


def evaluar(e: dict, pesos_crit=None, factor_castigo=1.0) -> dict:
    pesos = normalizar(pesos_crit or e["criterios"])
    peso_dom = normalizar({d["id"]: d["peso"] for d in e["dominios"]})
    dom_por_id = {d["id"]: d for d in e["dominios"]}
    p = e["parametros"]

    por_dominio = {}
    for d in e["dominios"]:
        filas = {}
        for motor, celdas in e["puntajes"][d["id"]].items():
            filas[motor] = {
                "total": puntaje_motor(celdas, pesos),
                "vetado": vetado(d, celdas, p),
            }
        por_dominio[d["id"]] = filas

    resultados = []
    for a in e["arquitecturas"]:
        asign = a["asignacion"]
        base = sum(peso_dom[d] * por_dominio[d][asign[d]]["total"] for d in asign)
        motores = sorted(set(asign.values()))
        castigo_motores = factor_castigo * p["castigo_motor_extra"] * (len(motores) - 1)
        castigo_cruces = 0.0
        cruces_activos = []
        for c in e["cruces"]:
            if asign[c["de"]] != asign[c["a"]]:
                valor = p["castigo_cruce_mitigado"] if c.get("mitigado") else p["castigo_cruce"]
                castigo_cruces += factor_castigo * valor
                cruces_activos.append(c)
        vetos = [d for d in asign if por_dominio[d][asign[d]]["vetado"]]
        resultados.append({
            "id": a["id"],
            "nombre": a.get("nombre", a["id"]),
            "asignacion": asign,
            "motores": motores,
            "base": base,
            "castigo_motores": castigo_motores,
            "castigo_cruces": castigo_cruces,
            "cruces_activos": cruces_activos,
            "final": base - castigo_motores - castigo_cruces,
            "vetada_en": vetos,
        })

    validas = sorted((r for r in resultados if not r["vetada_en"]), key=lambda r: -r["final"])
    ganador, empate = None, False
    if validas:
        ganador = validas[0]
        if len(validas) > 1 and validas[0]["final"] - validas[1]["final"] < p["umbral_empate"]:
            empate = True
    return {
        "pesos": pesos,
        "peso_dominio": peso_dom,
        "por_dominio": por_dominio,
        "arquitecturas": sorted(resultados, key=lambda r: (bool(r["vetada_en"]), -r["final"])),
        "ganador": ganador["id"] if ganador else None,
        "empate": empate,
        "dom_por_id": dom_por_id,
    }


def sensibilidad(e: dict) -> dict:
    escenarios = []
    for c in e["criterios"]:
        for f in (0.5, 1.5):
            pesos = dict(e["criterios"])
            pesos[c] = pesos[c] * f
            r = evaluar(e, pesos_crit=pesos)
            escenarios.append({"escenario": f"{c} ×{f}", "ganador": r["ganador"], "empate": r["empate"]})
    for f in (0.0, 0.5, 2.0):
        r = evaluar(e, factor_castigo=f)
        escenarios.append({"escenario": f"castigo híbrido ×{f}", "ganador": r["ganador"], "empate": r["empate"]})
    base = evaluar(e)["ganador"]
    iguales = sum(1 for s in escenarios if s["ganador"] == base)
    return {"escenarios": escenarios, "estable": iguales, "total": len(escenarios)}


# --------------------------------------------------------------------------- salida
def informe_md(e: dict, r: dict, s: dict) -> str:
    out = [f"# Matriz de puntuación · {e['proyecto']}", ""]
    crit = list(e["criterios"])
    out.append("**Pesos de criterio (normalizados):** " +
               " · ".join(f"{NOMBRES_CRITERIOS.get(c, c)} {r['pesos'][c]:.2f}" for c in crit))
    out.append("")
    out.append("**Peso de dominio:** " + " · ".join(
        f"{r['dom_por_id'][d]['nombre'] if 'nombre' in r['dom_por_id'][d] else d} {w:.2f}"
        for d, w in r["peso_dominio"].items()))
    out.append("")

    out.append("## Puntaje por dominio")
    for d in e["dominios"]:
        out.append("")
        out.append(f"### {d.get('nombre', d['id'])} (criticidad {d['criticidad']})")
        out.append("")
        out.append("| Motor | " + " | ".join(NOMBRES_CRITERIOS.get(c, c) for c in crit) + " | **Total** | Veto |")
        out.append("|---|" + "---:|" * len(crit) + "---:|---|")
        filas = sorted(e["puntajes"][d["id"]].items(), key=lambda kv: -r["por_dominio"][d["id"]][kv[0]]["total"])
        for motor, celdas in filas:
            info = r["por_dominio"][d["id"]][motor]
            out.append(f"| {motor} | " + " | ".join(f"{celdas[c]:g}" for c in crit) +
                       f" | **{info['total']:.2f}** | {'**VETADO**' if info['vetado'] else '—'} |")

    out += ["", "## Arquitecturas", "",
            "| # | Arquitectura | Motores | Base | − Motores extra | − Cruces | **Final** | Estado |",
            "|---|---|---|---:|---:|---:|---:|---|"]
    for i, a in enumerate(r["arquitecturas"], 1):
        estado = f"Vetada ({', '.join(a['vetada_en'])})" if a["vetada_en"] else (
            "**Ganadora**" if a["id"] == r["ganador"] else "Válida")
        out.append(f"| {i} | {a['nombre']} | {', '.join(a['motores'])} | {a['base']:.2f} | "
                   f"{a['castigo_motores']:.2f} | {a['castigo_cruces']:.2f} | **{a['final']:.2f}** | {estado} |")

    out += ["", "## Resultado", ""]
    validas = [a for a in r["arquitecturas"] if not a["vetada_en"]]
    if not validas:
        out.append("**Ninguna arquitectura es válida**: todas quedaron vetadas. Revisa la integridad "
                   "de los dominios de criticidad alta o agrega una rama que la garantice.")
    else:
        g = validas[0]
        if r["empate"]:
            seg = validas[1]
            out.append(f"**Empate técnico** entre «{g['nombre']}» ({g['final']:.2f}) y «{seg['nombre']}» "
                       f"({seg['final']:.2f}): margen {g['final'] - seg['final']:.2f} < umbral "
                       f"{e['parametros']['umbral_empate']:.2f}. No hay ganador por puntaje: elige la opción "
                       "más simple (menos motores, lo que el equipo domina) y nombra el dato que desempataría.")
        else:
            margen = g["final"] - validas[1]["final"] if len(validas) > 1 else float("nan")
            out.append(f"**Ganadora:** «{g['nombre']}» con {g['final']:.2f}"
                       + (f" (margen {margen:.2f} sobre la segunda)." if len(validas) > 1 else "."))
        if len(g["motores"]) > 1:
            out.append("")
            out.append("La ganadora es un **híbrido**: verifica las tres condiciones de `references/hibridos.md` "
                       "(variante en un solo motor y escrituras cruzadas) antes de recomendarlo.")
            for c in g["cruces_activos"]:
                out.append(f"- Escritura cruzada {c['de']} → {c['a']}"
                           f"{' (mitigada)' if c.get('mitigado') else ' (SIN mitigar)'}: {c.get('descripcion', '')}")

    out += ["", "## Sensibilidad", "",
            f"El ganador se mantiene en **{s['estable']} de {s['total']}** escenarios "
            "(cada peso de criterio ×0.5 y ×1.5; castigo del híbrido ×0, ×0.5 y ×2).", ""]
    cambios = [x for x in s["escenarios"] if x["ganador"] != r["ganador"]]
    if cambios:
        out.append("Escenarios donde **cambia** el ganador:")
        out.append("")
        out.append("| Escenario | Ganador en ese escenario |")
        out.append("|---|---|")
        for x in cambios:
            out.append(f"| {x['escenario']} | {x['ganador']}{' (empate)' if x['empate'] else ''} |")
        out.append("")
        out.append("Interpreta: si el ganador depende de un peso, la decisión depende de **ese criterio**. "
                   "Justifica su peso con el caso o trátalo como supuesto crítico.")
    else:
        out.append("Ningún escenario cambia al ganador: la decisión es **robusta** frente a los pesos.")
    return "\n".join(out) + "\n"


def a_json(r: dict, s: dict) -> dict:
    r = deepcopy(r)
    r.pop("dom_por_id", None)
    return {"resultado": r, "sensibilidad": s}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada", help="archivo JSON con la evaluación")
    ap.add_argument("--json", action="store_true", help="imprime el resultado en JSON")
    args = ap.parse_args()
    try:
        e = cargar(args.entrada)
    except (ErrorEntrada, KeyError, json.JSONDecodeError) as exc:
        print(f"Error en la entrada: {exc}", file=sys.stderr)
        return 2
    r = evaluar(e)
    s = sensibilidad(e)
    if args.json:
        print(json.dumps(a_json(r, s), ensure_ascii=False, indent=2))
    else:
        print(informe_md(e, r, s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
