from app.mq.example_consumers import AnnotationNotifyConsumer, AudioProcessConsumer, SystemLogConsumer, TrackIngestConsumer


CONSUMER_REGISTRY = {
    "track:ingest": TrackIngestConsumer,
    "audio:process": AudioProcessConsumer,
    "annotation:notify": AnnotationNotifyConsumer,
    "system:log": SystemLogConsumer,
}


def list_consumers() -> list[dict]:
    items = []
    for queue_name, consumer_cls in CONSUMER_REGISTRY.items():
        items.append(
            {
                "queue_name": queue_name,
                "consumer_name": consumer_cls.consumer_name,
                "enabled": True,
            }
        )
    return items
