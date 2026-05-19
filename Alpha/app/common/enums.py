from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    ANNOTATOR = "annotator"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"


class LogLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class QueueName(str, Enum):
    TRACK_INGEST = "track:ingest"
    AUDIO_PROCESS = "audio:process"
    ANNOTATION_NOTIFY = "annotation:notify"
    SYSTEM_LOG = "system:log"

