"""Resumen de la sesión terminada (T-15): una transacción de solo lectura."""

from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Engine

from nukyro.auth import Auth
from nukyro.modules.assessment import queries as assessment_queries
from nukyro.modules.assessment import service as assessment_service
from nukyro.modules.assessment.scoring import difference
from nukyro.modules.entry import queries as entry_queries
from nukyro.modules.summary import queries


def _reference(r) -> dict:
    legal = r["ref_category"] == "legal"
    return {
        "category": r["ref_category"],
        "title": r["title"],
        "source": r["source"],
        "url": r["url"],
        "section": r["section"],
        "version_label": r["version_label"],
        "is_law": legal,
        "jurisdiction": r["jurisdiction"] if legal else None,
        "scope_note": f"Aplica solo en {r['jurisdiction']}" if legal else None,
        "valid_from": r["valid_from"],
    }


def _applicable(sets: dict, r) -> int:
    s = sets.get(r["set_type"])
    return len(s["questions"]) if s else r["answered_count"]


def get_summary(engine: Engine, auth: Auth, session_id: str) -> dict:
    try:
        session = UUID(session_id)
    except ValueError:
        raise HTTPException(404) from None
    with engine.begin() as conn:
        # El UPDATE bloquea al participante antes de leer la sesión (RF-080)
        participant = entry_queries.touch_participant(conn, auth)
        if participant is None:
            raise HTTPException(401)
        row = assessment_queries.session_row(conn, participant, session, lock=False)
        if row is None:
            raise HTTPException(404)
        if row["completed_at"] is None:
            raise HTTPException(409)  # antes de terminar revelaría respuestas (defecto 11)
        queries_hitos = assessment_queries.hitos(conn, session)
        reasons, feedback, refs = defaultdict(list), defaultdict(list), defaultdict(list)
        for r in queries.chosen_reasons(conn, session):
            reasons[r["session_decision_id"]].append({"key": r["key"], "label": r["label"]})
        for f in queries.feedback(conn, session):
            scope = "decision" if f["general"] else "option"
            feedback[f["decision_id"]].append(
                {"category": f["category"], "scope": scope, "body": f["body"]}
            )
        for r in queries.references(conn, session):
            refs[r["decision_id"]].append(_reference(r))
        decisions = [
            {
                "node_key": d["key"],
                "title": d["title"],
                "option_key": d["option_key"],
                "option_label": d["option_label"],
                "reasons": reasons[d["id"]],
                "feedback": feedback[d["id"]],
                "references": refs[d["id"]],
            }
            for d in queries.decisions(conn, session)
        ]
        causes = defaultdict(list)
        for c in queries.causes(conn, session):
            causes[c["session_event_id"]].append({"node_key": c["key"], "title": c["title"]})
        consequences = [
            {
                "kind": e["rule_type"],
                "relation_type": e["relation_type"],
                "node_key": e["key"],
                "title": e["title"],
                "explanation": e["explanation"],
                "causes": causes[e["id"]],
            }
            for e in queries.events(conn, session)
        ]
        # total: preguntas aplicables a esta sesión (RF-058); answered: las respondidas
        sets = assessment_service._load(conn, session, queries_hitos["version"])
        results = [
            {
                "type": r["set_type"],
                "score": None if r["score"] is None else float(r["score"]),
                "correct_count": r["correct_count"],
                "answered": r["answered_count"],
                "total": _applicable(sets, r),
            }
            for r in queries.results(conn, session)
        ]
        by_type = {r["set_type"]: r["score"] for r in queries.results(conn, session)}
        pre, post = by_type.get("pretest"), by_type.get("posttest")
        diff = difference(pre, post)
        j = queries.justifications(conn, session)
        return {
            "decisions": decisions,
            "consequences": consequences,
            "results": results,
            "pretest_score": None if pre is None else float(pre),
            "posttest_score": None if post is None else float(post),
            "difference": None if diff is None else float(diff),
            "justifications": {
                "correct_count": j["correct"],
                "total": j["total"],
                "rubric_version": j["rubric_version"],
            },
        }
