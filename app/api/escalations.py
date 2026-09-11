"""Escalations API — list and acknowledge (completes the escalation lifecycle)."""
from flask import Blueprint, jsonify, request

from app.models.escalation import EscalationEvent
from app.services.escalation_service import acknowledge_escalation

escalations_bp = Blueprint("escalations", __name__, url_prefix="/api/escalations")


@escalations_bp.get("")
def list_escalations():
    status = request.args.get("status")
    query = EscalationEvent.query
    if status:
        query = query.filter_by(status=status)
    escalations = query.order_by(EscalationEvent.triggered_at.desc()).all()
    return jsonify([e.to_dict() for e in escalations])


@escalations_bp.post("/<int:escalation_id>/acknowledge")
def acknowledge(escalation_id):
    escalation = EscalationEvent.query.get_or_404(escalation_id)
    payload = request.get_json(silent=True) or {}

    updated = acknowledge_escalation(
        escalation,
        acknowledged_by=payload.get("acknowledged_by", "on_call_nurse"),
        note=payload.get("note"),
    )
    return jsonify(updated.to_dict())
