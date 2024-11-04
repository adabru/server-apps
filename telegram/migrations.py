from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ChatConfig:
    trainer_language: str = "de-DE"
    learner_language: str = "en-US"
    suggestions: bool = False
    trainer_id: int = -1


@dataclass
class Database:
    version: int = 3
    chats: Dict[int, ChatConfig] = field(default_factory=dict)


def migrate(serialized: dict) -> Database:
    # empty
    if len(serialized) == 0:
        db = Database()
        return db

    # v1 => v2
    if "trainer_language" in serialized:
        serialized = {
            "version": 2,
            "chats": {},
            "default": {
                "trainer_language": serialized["trainer_language"],
                "learner_language": serialized["learner_language"],
            },
        }

    # v2 => v3
    if serialized["version"] == 2:
        serialized["version"] = 3
        del serialized["default"]
        for chat in serialized["chats"].values():
            chat["suggestions"] = False

    # v3
    db = Database(
        version=serialized["version"],
        chats={int(k): ChatConfig(**v) for k, v in serialized["chats"].items()},
    )
    return db
