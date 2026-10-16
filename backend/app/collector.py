"""Capture short-lived RSS entries before they leave upstream feeds."""
import json
from datetime import timedelta
from sqlalchemy import select
from .clock import utcnow
from .feeds import fetch_feed, parse_feed, source_error
from .models import RuntimeState, Source
from .pipeline import persist_news


def collect_recent(factory, settings, fetcher=fetch_feed):
    end = utcnow()
    results = []
    with factory() as session:
        sources = list(session.scalars(select(Source).where(Source.enabled.is_(True))))
    for source in sources:
        try:
            items, counts = parse_feed(fetcher(source, settings), source, end - timedelta(hours=48), end)
            for item in items:
                persist_news(factory, item)
            results.append({"id": source.id, "status": "ok", **counts})
        except Exception as exc:
            results.append({"id": source.id, "status": "error", "message": source_error(exc)})
    with factory.begin() as session:
        session.merge(RuntimeState(key="last_collection", value=json.dumps({"at": end.isoformat(), "results": results})))
