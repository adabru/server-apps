import json
from pathlib import Path

base = Path(__file__).resolve().parent
db_dir = base.joinpath("db")
db_dir.mkdir(parents=True, exist_ok=True)


def load_db(name: str) -> dict:
    try:
        with open(db_dir.joinpath(name + ".json"), "r") as file:
            content = json.load(file)
    except FileNotFoundError:
        content = {}
    return content


def save_db(name: str, content: dict) -> None:
    with open(db_dir.joinpath(name + ".json.tmp"), "w") as file:
        json.dump(content, file, indent=2)
    db_dir.joinpath(name + ".json.tmp").replace(db_dir.joinpath(name + ".json"))
