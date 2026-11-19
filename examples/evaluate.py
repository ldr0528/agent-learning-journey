"""离线计算检索指标；可加载外部回答记录检查引用结构。"""

import argparse
import json
from pathlib import Path

from agent_learning.evaluation import run_evaluation


def main():
    parser = argparse.ArgumentParser(description="课程检索开发集评估，不调用模型 API")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--output", type=Path, help="另存 JSON 报告")
    parser.add_argument("--predictions", type=Path, help="外部回答 JSON 列表，字段格式见第9章")
    args = parser.parse_args()
    try:
        predictions = json.loads(args.predictions.read_text(encoding="utf-8")) if args.predictions else None
        if predictions is not None and (not isinstance(predictions, list) or any(not isinstance(item, dict) for item in predictions)):
            raise ValueError("预测文件顶层必须是对象列表。")
        result = run_evaluation(args.k, predictions)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        print(text)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        print(str(error))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
