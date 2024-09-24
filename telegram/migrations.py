from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ChatConfig:
    trainer_language: str = "de-DE"
    learner_language: str = "en-US"


@dataclass
class Database:
    version: int = 2
    chats: Dict[int, ChatConfig] = field(default_factory=dict)
    default: ChatConfig = field(default_factory=ChatConfig)


def migrate(serialized: dict) -> Database:
    # empty
    if len(serialized) == 0:
        db = Database()
        return db

    # v1 => v2
    elif "trainer_language" in serialized:
        db = Database(
            default=ChatConfig(
                trainer_language=serialized["trainer_language"],
                learner_language=serialized["learner_language"],
            )
        )
        return db

    # v2
    elif serialized["version"] == 2:
        db = Database(
            version=serialized["version"],
            chats={int(k): ChatConfig(**v) for k, v in serialized["chats"].items()},
            default=ChatConfig(**serialized["default"]),
        )
        return db
