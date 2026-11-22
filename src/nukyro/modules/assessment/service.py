"""Reglas de las evaluaciones (P6): guardar y enviar, una transacción por operación."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Connection, Engine

from nukyro.modules.assessment import queries, scoring
from nukyro.modules.entry import queries as entry_queries
from nukyro.security import hash_secret


def _load(conn: Connection, session, version) -> dict:
    """Conjuntos de la versión con sus preguntas aplicables a esta sesión (RF-058)."""
    path, targets = queries.path_nodes(conn, session), queries.event_targets(conn, session)
    sets: dict = {}
    for r in queries.question_rows(conn, version):
        s = sets.setdefault(
            r["set_type"], {"id": r["set_id"], "all": r["requires_all_answers"], "questions": []}
        )
        if r["question_id"] is not None and scoring.applies(r["requires_node_id"], path, targets):
            s["questions"].append(r)
    return sets


def _present(sets: dict) -> set[str]:
    """Conjuntos finales que la versión tiene y que esta sesión puede responder."""
    return {k for k in scoring.FINAL if k in sets and sets[k]["questions"]}


def settle(conn: Connection, session) -> None:
    """Fija completed_at cuando ya hay desenlace y todos los conjuntos finales están enviados.
    Una versión sin conjuntos finales se completa al llegar al desenlace."""
    row = queries.hitos(conn, session)
    if row["outcome_reached_at"] is None or row["completed_at"] is not None:
        return
    sets = _load(conn, session, row["version"])
    attempts = queries.attempts(conn, session)
    submitted = {k for k, s in sets.items() if attempts.get(s["id"], {}).get("submitted_at")}
    if scoring.is_complete(_present(sets), submitted):
        queries.mark_completed(conn, session)


def _view(conn: Connection, session, kind, s, attempt) -> dict:
    answers = queries.answers(conn, attempt["id"]) if attempt else {}
    by_question: dict = {}
    for o in queries.options(conn, session, s["id"]):
        by_question.setdefault(o["question_id"], []).append({"key": o["key"], "label": o["label"]})
    submitted = bool(attempt and attempt["submitted_at"])
    score = attempt["score"] if submitted else None
    return {
        "type": kind,
        "submitted": submitted,
        "answered": len(answers),
        "total": len(s["questions"]),
        "score": None if score is None else float(score),
        "questions": [
            {
                "key": q["key"],
                "prompt": q["prompt"],
                "options": by_question.get(q["question_id"], []),
                "selected_option_key": answers.get(q["question_id"]),
            }
            for q in s["questions"]
        ],
    }


def _run(engine: Engine, secret: str, session_id: str, kind: str, write: bool, act):
    """Autentica, bloquea (participante, luego sesión) y ejecuta `act` sobre el conjunto."""
    try:
        session = UUID(session_id)
    except ValueError:
        raise HTTPException(404) from None
    if kind not in scoring.TYPES:
        raise HTTPException(404)
    with engine.begin() as conn:
        # El UPDATE bloquea al participante antes que la sesión y renueva su actividad (RF-080)
        participant = entry_queries.touch_participant(conn, hash_secret(secret))
        if participant is None:
            raise HTTPException(401)
        row = queries.session_row(conn, participant, session, lock=write)
        if row is None:
            raise HTTPException(404)
        sets = _load(conn, session, row["version"])
        if kind not in sets or (kind in scoring.FINAL and kind not in _present(sets)):
            raise HTTPException(404)
        s = sets[kind]
        attempts = queries.attempts(conn, session)
        attempt = attempts.get(s["id"])
        submitted = {k for k, x in sets.items() if attempts.get(x["id"], {}).get("submitted_at")}
        context = {
            "conn": conn,
            "session": session,
            "version": row["version"],
            "set": s,
            "attempt": attempt,
            "done": kind in submitted,
            "turn": scoring.is_turn(
                kind, row["outcome_reached_at"] is not None, _present(sets), submitted
            ),
        }
        result = act(context)  # una excepción revierte todo: rechazar no cambia nada
        if write:
            queries.touch_session(conn, session)
        return result


def get_assessment(engine: Engine, secret: str, session_id: str, kind: str) -> dict:
    def act(c):
        if not c["done"] and not c["turn"]:
            raise HTTPException(409)  # antes de su turno no se muestran las preguntas
        return _view(c["conn"], c["session"], kind, c["set"], c["attempt"])

    return _run(engine, secret, session_id, kind, False, act)


def put_answer(
    engine: Engine, secret: str, session_id: str, kind: str, question_key: str, body
) -> dict:
    def act(c):
        if c["done"] or not c["turn"]:
            raise HTTPException(409)
        question = next((q for q in c["set"]["questions"] if q["key"] == question_key), None)
        option = question and queries.option_id(c["conn"], question["question_id"], body.option_key)
        if question is None or option is None:
            raise HTTPException(422)  # pregunta que no aplica u opción de otra pregunta
        attempt = queries.ensure_attempt(
            c["conn"], c["session"], c["version"], c["set"]["id"], c["attempt"]
        )
        queries.upsert_answer(c["conn"], attempt, c["set"]["id"], question["question_id"], option)
        answered, _ = queries.tally(c["conn"], attempt)
        return {"answered": answered, "total": len(c["set"]["questions"]), "submitted": False}

    return _run(engine, secret, session_id, kind, True, act)


def submit(engine: Engine, secret: str, session_id: str, kind: str) -> dict:
    def act(c):
        conn, session, s = c["conn"], c["session"], c["set"]
        if c["done"]:  # enviar otra vez devuelve lo mismo y no recalifica (RN-19)
            return _view(conn, session, kind, s, c["attempt"])
        if not c["turn"]:
            raise HTTPException(409)
        attempt = queries.ensure_attempt(conn, session, c["version"], s["id"], c["attempt"])
        answered, correct = queries.tally(conn, attempt)
        if s["all"] and answered < len(s["questions"]):
            raise HTTPException(409)  # exige todas y falta alguna: sin puntuación
        queries.submit_attempt(conn, attempt, answered, correct, scoring.percent(correct, answered))
        if kind == "pretest":
            queries.mark_pretest(conn, session)
        else:
            settle(conn, session)
        return _view(conn, session, kind, s, queries.attempts(conn, session)[s["id"]])

    return _run(engine, secret, session_id, kind, True, act)
