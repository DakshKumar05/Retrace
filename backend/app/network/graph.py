"""Fraud network analysis over the transaction graph.

Builds a directed multi-type graph with NetworkX, finds clusters that share a
sender or a refund destination, and returns a laid-out graph the frontend can
render directly as SVG (layout is computed here so the client needs no
additional graph library).
"""
from __future__ import annotations

import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RefundRequest, Transaction, User


def build_graph(db: Session) -> nx.DiGraph:
    g = nx.DiGraph()

    users = {u.id: u for u in db.scalars(select(User)).all()}
    transactions = db.scalars(select(Transaction).where(Transaction.direction == "credit")).all()
    refunds = db.scalars(select(RefundRequest)).all()
    refunds_by_tx: dict[int, list[RefundRequest]] = {}
    for r in refunds:
        refunds_by_tx.setdefault(r.transaction_id, []).append(r)

    for tx in transactions:
        sender = f"upi:{tx.sender_handle}"
        victim = f"user:{tx.user_id}"
        txn = f"tx:{tx.reference}"

        g.add_node(
            sender,
            type="sender",
            label=tx.sender_handle,
            suspicious=bool(tx.sender_suspicious_history or tx.sender_prior_reports),
        )
        user = users.get(tx.user_id)
        g.add_node(
            victim,
            type="victim",
            label=(user.full_name if user else f"User {tx.user_id}"),
            handle=(user.upi_id if user else ""),
        )
        g.add_node(txn, type="transaction", label=tx.reference, amount=tx.amount, risk=tx.risk_score)

        g.add_edge(sender, txn, relation="sent_payment", amount=tx.amount)
        g.add_edge(txn, victim, relation="credited")

        for r in refunds_by_tx.get(tx.id, []):
            dest = f"upi:{r.refund_destination}"
            g.add_node(dest, type="destination", label=r.refund_destination, suspicious=True)
            g.add_edge(victim, dest, relation="refunded_to", amount=r.amount, status=r.status)
            if not r.destination_matches_sender:
                g.add_edge(sender, dest, relation="connected_to", reason="destination_mismatch")

    return g


def _cluster_risk(victims: int, destinations: int, txn_count: int, flagged: int) -> int:
    score = min(victims * 9, 45) + min(destinations * 7, 28) + min(txn_count * 2, 16)
    score += 11 if flagged else 0
    return min(score, 100)


def analyse(db: Session) -> dict:
    """Return every suspicious cluster, largest first."""
    g = build_graph(db)
    clusters: list[dict] = []

    senders = [n for n, d in g.nodes(data=True) if d.get("type") == "sender"]
    for sender in senders:
        reachable = nx.descendants(g, sender) | {sender}
        sub = g.subgraph(reachable)
        victims = [n for n, d in sub.nodes(data=True) if d.get("type") == "victim"]
        destinations = [n for n, d in sub.nodes(data=True) if d.get("type") == "destination"]
        txns = [n for n, d in sub.nodes(data=True) if d.get("type") == "transaction"]
        flagged = bool(g.nodes[sender].get("suspicious"))

        if len(victims) < 2 and not flagged:
            continue

        clusters.append(
            {
                "cluster_key": sender,
                "suspect_handle": g.nodes[sender]["label"],
                "victim_count": len(victims),
                "destination_count": len(destinations),
                "transaction_count": len(txns),
                "risk_score": _cluster_risk(len(victims), len(destinations), len(txns), flagged),
                "graph": serialise(sub, root=sender),
            }
        )

    clusters.sort(key=lambda c: (-c["risk_score"], -c["victim_count"]))
    return {
        "clusters": clusters,
        "totals": {
            "nodes": g.number_of_nodes(),
            "edges": g.number_of_edges(),
            "suspicious_senders": sum(
                1 for _, d in g.nodes(data=True) if d.get("type") == "sender" and d.get("suspicious")
            ),
        },
    }


def serialise(graph: nx.Graph, root: str | None = None, width: int = 900, height: int = 560) -> dict:
    """Lay the graph out and emit plain JSON with pixel coordinates."""
    if graph.number_of_nodes() == 0:
        return {"nodes": [], "edges": []}

    try:
        pos = nx.spring_layout(graph, seed=42, k=1.15, iterations=140)
    except Exception:  # pragma: no cover
        pos = nx.circular_layout(graph)

    xs = [p[0] for p in pos.values()] or [0.0]
    ys = [p[1] for p in pos.values()] or [0.0]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = (max_x - min_x) or 1.0
    span_y = (max_y - min_y) or 1.0
    pad = 70

    nodes = []
    for n, data in graph.nodes(data=True):
        px = pad + (pos[n][0] - min_x) / span_x * (width - 2 * pad)
        py = pad + (pos[n][1] - min_y) / span_y * (height - 2 * pad)
        nodes.append(
            {
                "id": n,
                "label": data.get("label", n),
                "type": data.get("type", "unknown"),
                "suspicious": bool(data.get("suspicious", False)),
                "amount": data.get("amount"),
                "risk": data.get("risk"),
                "degree": graph.degree(n),
                "is_root": n == root,
                "x": round(px, 1),
                "y": round(py, 1),
            }
        )

    edges = [
        {"source": u, "target": v, "relation": d.get("relation", "connected_to"), "amount": d.get("amount")}
        for u, v, d in graph.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges, "width": width, "height": height}


def network_risk_for_handle(db: Session, handle: str) -> tuple[int, str | None]:
    """Cluster risk contribution for a single UPI handle."""
    if not handle:
        return 0, None
    result = analyse(db)
    for cluster in result["clusters"]:
        if cluster["suspect_handle"].lower() == handle.lower():
            detail = (
                f"{cluster['suspect_handle']} is linked to {cluster['victim_count']} accounts and "
                f"{cluster['destination_count']} refund destinations across "
                f"{cluster['transaction_count']} payments."
            )
            return cluster["risk_score"], detail
    return 0, None
