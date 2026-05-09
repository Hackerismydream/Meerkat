from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AlertStatus, ApprovalStatus
from app.db.base import ActionProposal, ApprovalTask, Coupon, LiveComment, LiveSessionProduct, OpsAlert, Product, SkuInventory, StreamHealthSample, StreamIncident
from app.services.serialization import dumps, model_to_dict


class MeerkatTools:
    def __init__(self, db: AsyncSession, trace_id: str, knowledge_dir: Path):
        self.db = db
        self.trace_id = trace_id
        self.knowledge_dir = knowledge_dir

    async def search_recent_comments(
        self,
        session_id: int,
        q: str | None = None,
        since_minutes: int = 3,
        limit: int = 50,
    ) -> dict[str, Any]:
        query = select(LiveComment).where(LiveComment.session_id == session_id).order_by(LiveComment.created_at.desc()).limit(limit)
        comments = list((await self.db.scalars(query)).all())
        if q:
            comments = [comment for comment in comments if q in comment.body or q in (comment.matched_type or "")]
        return {"items": [model_to_dict(comment) for comment in comments], "since_minutes": since_minutes}

    async def get_live_products(self, session_id: int) -> dict[str, Any]:
        rows = (
            await self.db.execute(
                select(LiveSessionProduct, Product)
                .join(Product, Product.id == LiveSessionProduct.product_id)
                .where(LiveSessionProduct.session_id == session_id)
                .order_by(LiveSessionProduct.display_order)
            )
        ).all()
        return {
            "items": [
                {
                    **model_to_dict(product),
                    "anchor_alias": live_product.anchor_alias,
                    "display_order": live_product.display_order,
                }
                for live_product, product in rows
            ]
        }

    async def get_product_detail(self, product_id: int) -> dict[str, Any]:
        product = await self.db.get(Product, product_id)
        if product is None:
            return {"error": "product_not_found", "product_id": product_id}
        return model_to_dict(product)

    async def get_product_inventory(self, product_id: int) -> dict[str, Any]:
        inventory = list((await self.db.scalars(select(SkuInventory).where(SkuInventory.product_id == product_id))).all())
        return {"items": [model_to_dict(item) for item in inventory], "total_available": sum(item.available_stock for item in inventory)}

    async def get_coupon_detail(self, coupon_id: int) -> dict[str, Any]:
        coupon = await self.db.get(Coupon, coupon_id)
        if coupon is None:
            return {"error": "coupon_not_found", "coupon_id": coupon_id}
        return model_to_dict(coupon)

    async def get_stream_incident_context(self, stream_incident_id: int) -> dict[str, Any]:
        incident = await self.db.get(StreamIncident, stream_incident_id)
        if incident is None:
            return {"error": "stream_incident_not_found", "stream_incident_id": stream_incident_id}
        samples = list(
            (
                await self.db.scalars(
                    select(StreamHealthSample)
                    .where(StreamHealthSample.session_id == incident.session_id)
                    .order_by(StreamHealthSample.id.desc())
                    .limit(5)
                )
            ).all()
        )
        return {"incident": model_to_dict(incident), "recent_samples": [model_to_dict(sample) for sample in samples]}

    async def search_policy_docs(self, query: str, top_k: int = 3) -> dict[str, Any]:
        terms = [term for term in query.replace("/", " ").split() if term]
        hits: list[dict[str, Any]] = []
        for path in sorted(self.knowledge_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            score = sum(text.count(term) for term in terms)
            if score or any(token in path.name for token in terms):
                lines = text.splitlines()
                hits.append({"source_file": path.name, "score": score or 1, "snippet": "\n".join(lines[:6])})
        hits.sort(key=lambda item: item["score"], reverse=True)
        return {"items": hits[:top_k]}

    async def create_ops_alert(
        self,
        session_id: int,
        alert_type: str,
        severity: str,
        title: str,
        summary: str,
        evidence: dict[str, Any],
        product_id: int | None = None,
        coupon_id: int | None = None,
    ) -> dict[str, Any]:
        dedupe_target = product_id if product_id is not None else coupon_id if coupon_id is not None else "none"
        dedupe_key = f"session:{session_id}:type:{alert_type}:target:{dedupe_target}:trace:{self.trace_id}"
        alert = OpsAlert(
            session_id=session_id,
            alert_type=alert_type,
            severity=severity,
            status=AlertStatus.OPEN.value,
            title=title,
            summary=summary,
            evidence_json=dumps(evidence),
            product_id=product_id,
            coupon_id=coupon_id,
            dedupe_key=dedupe_key,
            created_by="agent",
            trace_id=self.trace_id,
        )
        self.db.add(alert)
        await self.db.flush()
        return model_to_dict(alert)

    async def create_speaker_note(
        self,
        session_id: int,
        body: str,
        target: str = "anchor",
        alert_id: int | None = None,
    ) -> dict[str, Any]:
        from app.db.base import SpeakerNote

        note = SpeakerNote(
            session_id=session_id,
            alert_id=alert_id,
            body=body,
            target=target,
            status="DRAFT",
            created_by="agent",
            trace_id=self.trace_id,
        )
        self.db.add(note)
        await self.db.flush()
        return model_to_dict(note)

    async def create_action_proposal(
        self,
        session_id: int,
        action_type: str,
        risk_level: str,
        arguments: dict[str, Any],
        reason: str,
        status: str = "PROPOSED",
        alert_id: int | None = None,
        created_by_agent: str = "commander",
    ) -> dict[str, Any]:
        proposal = ActionProposal(
            session_id=session_id,
            alert_id=alert_id,
            action_type=action_type,
            risk_level=risk_level,
            arguments_json=dumps(arguments),
            reason=reason,
            status=status,
            created_by_agent=created_by_agent,
            trace_id=self.trace_id,
        )
        self.db.add(proposal)
        await self.db.flush()
        return model_to_dict(proposal)

    async def create_approval_task(
        self,
        session_id: int,
        title: str,
        reason: str,
        payload: dict[str, Any],
        risk_level: str = "HIGH_RISK_WRITE",
        proposal_id: int | None = None,
    ) -> dict[str, Any]:
        approval = ApprovalTask(
            proposal_id=proposal_id,
            session_id=session_id,
            risk_level=risk_level,
            title=title,
            reason=reason,
            payload_json=dumps(payload),
            status=ApprovalStatus.PENDING.value,
            trace_id=self.trace_id,
        )
        self.db.add(approval)
        await self.db.flush()
        return model_to_dict(approval)
