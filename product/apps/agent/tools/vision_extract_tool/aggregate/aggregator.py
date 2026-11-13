# vision_extract_tool/aggregate/aggregator.py
import json
from octochains import Aggregator
from ..schema import PrescriptionExtract
from .consensus import build_consensus

class FieldConsensus(Aggregator):
    def __init__(self):
        super().__init__(role="field_consensus", goal="Đối chiếu từng trường giữa các lần đọc độc lập")

    def execute(self, agent_reports: dict[str, str]) -> str:
        parsed = []
        for text in agent_reports.values():
            data = json.loads(text)
            if "error" not in data:
                parsed.append(PrescriptionExtract.model_validate(data))
        if len(parsed) < 2:
            errors = [json.loads(t).get("error") for t in agent_reports.values()]
            return json.dumps({"status": "insufficient", "readers_ok": len(parsed), "errors": errors},
                              ensure_ascii=False)
        return json.dumps(build_consensus(parsed), ensure_ascii=False)