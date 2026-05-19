from pydantic import BaseModel, ConfigDict


class QueueStatusOut(BaseModel):
    queue_name: str
    queue_length: int | None = None
    last_consumed_at: str | None = None
    last_failure_at: str | None = None
    last_dead_letter_at: str | None = None
    last_failure_message_id: str | None = None
    last_dead_letter_message_id: str | None = None
    failure_count: int = 0
    dead_letter_count: int = 0
    redis_available: bool = True
    error: str | None = None


class QueuePublishRequest(BaseModel):
    queue_name: str
    message: dict


class QueuePublishOut(BaseModel):
    queue_name: str
    queue_length: int
    message_id: str | None = None
    event_type: str | None = None
    trace_id: str | None = None


class ConsumerRunRequest(BaseModel):
    queue_name: str


class ConsumerRunOut(BaseModel):
    queue_name: str
    consumer_name: str
    consumed: bool


class ConsumerStatusOut(BaseModel):
    queue_name: str
    consumer_name: str
    enabled: bool = True


class FailureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    failure_id: str
    queue_name: str
    message_id: str
    event_type: str
    consumer_name: str
    retry_count: int
    error_message: str
    payload_json: str
    failed_at: str


class DeadLetterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dead_letter_id: str
    queue_name: str
    message_id: str
    event_type: str
    payload_json: str
    last_error_message: str
    retry_count: int
    created_at: str


class SystemLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: str
    log_level: str
    source: str
    message: str
    trace_id: str | None = None
    context_json: str | None = None
    created_at: str


class SystemConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    config_key: str
    config_value: str
    description: str | None = None
    updated_at: str


class SystemConfigUpsert(BaseModel):
    config_value: str
    description: str | None = None
