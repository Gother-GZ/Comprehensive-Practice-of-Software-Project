import csv
import io
import json

from app.common.exceptions import bad_request
from app.mq.registry import CONSUMER_REGISTRY, list_consumers


class ConsumerService:
    def list_consumers(self) -> list[dict]:
        return list_consumers()

    def consume_once(self, queue_name: str) -> dict:
        consumer_cls = CONSUMER_REGISTRY.get(queue_name)
        if consumer_cls is None:
            raise bad_request(f"unsupported consumer queue: {queue_name}")
        consumer = consumer_cls()
        consumed = consumer.consume_once()
        return {"queue_name": queue_name, "consumer_name": consumer.consumer_name, "consumed": consumed}


def export_rows(items: list[dict], export_format: str) -> tuple[str, str]:
    if export_format == "jsonl":
        content = "\n".join(json.dumps(item, ensure_ascii=False) for item in items)
        return content, "application/x-ndjson"
    if export_format == "csv":
        buffer = io.StringIO()
        fieldnames = sorted({key for item in items for key in item.keys()}) if items else []
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            for item in items:
                writer.writerow(item)
        return buffer.getvalue(), "text/csv; charset=utf-8"
    raise bad_request("unsupported export format")
