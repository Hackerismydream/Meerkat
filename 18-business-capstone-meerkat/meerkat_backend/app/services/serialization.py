import json
from datetime import datetime
from decimal import Decimal
from typing import Any


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=to_jsonable)


def loads(value: str | None) -> Any:
    if not value:
        return None
    return json.loads(value)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


def model_to_dict(obj: Any) -> dict[str, Any]:
    data = {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
    for key in list(data):
        data[key] = to_jsonable(data[key])
    for json_key in ("evidence_json", "arguments_json", "payload_json", "input_json", "output_json", "comment_ids_json", "final_output_json", "raw_payload_json", "target_json"):
        if json_key in data:
            data[json_key.removesuffix("_json")] = loads(data[json_key])
    return data
