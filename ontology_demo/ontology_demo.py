"""观察本体推理前后的查询结果，或用 --query 体验自然语言问答。"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from owlrl import DeductiveClosure, OWLRL_Semantics
from rdflib import RDFS, Graph
from rdflib.plugins.sparql.algebra import translateQuery, traverse
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue


HERE = Path(__file__).resolve().parent
QUESTION = "结算服务直接依赖哪些计算资源，各由哪个团队负责？"
QUERY = """
PREFIX ex: <https://example.org/llm-dev-demo/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?resourceName ?teamName
WHERE {
    ex:checkout ex:dependsOn ?resource .
    ?resource a ex:ComputeResource ;
        rdfs:label ?resourceName .
    OPTIONAL {
        ?resource ex:managedBy ?team .
        ?team rdfs:label ?teamName .
    }
}
ORDER BY ?resource ?teamName
"""


def query_resources(graph: Graph) -> list[dict[str, str | None]]:
    return [
        {"资源": str(resource), "负责团队": str(team) if team is not None else None}
        for resource, team in graph.query(QUERY)
    ]


def print_results(title: str, rows: list[dict[str, str | None]]) -> None:
    print(f"\n{title}（{len(rows)} 条）")
    for row in rows:
        team = row["负责团队"] or "图中尚未记录负责团队"
        print(f"  - {row['资源']}（{team}）")


def complete(client: OpenAI, model: str, instruction: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt},
        ],
    )
    answer = response.choices[0].message.content if response.choices else None
    if not answer or not answer.strip():
        raise ValueError("模型未返回正文。")
    return answer.strip()


def check_local_pattern(node) -> None:
    # SELECT 也可以指定外部数据源。检查语法树会覆盖子查询及嵌套图模式。
    if isinstance(node, CompValue) and node.name in {"ServiceGraphPattern", "DatasetClause"}:
        raise ValueError("课堂查询只读取当前内存图，请使用本地图模式。")


def execute_select(graph: Graph, sparql: str) -> dict:
    parsed = parseQuery(sparql)
    if parsed[1].name != "SelectQuery":
        raise ValueError("课堂查询需要一条 SELECT。")
    traverse(parsed[1], visitPre=check_local_pattern)
    query = translateQuery(parsed, initNs=dict(graph.namespaces()))
    max_rows = 50
    # 在查询自身的聚合、排序、LIMIT/OFFSET 之后多取一行，用来判断展示结果是否截断。
    query.algebra["p"] = CompValue("Slice", p=query.algebra.p, start=0, length=max_rows + 1)
    result = graph.query(query)
    # 直接读绑定能保留 OPTIONAL 所有投影列均为 null 的行。
    bindings = result.bindings
    rows = [
        [str(binding[col]) if col in binding else None for col in result.vars]
        for binding in bindings[:max_rows]
    ]
    return {
        "列名": [str(col) for col in result.vars],
        "数据行": rows,
        "结果已截断": len(bindings) > max_rows,
    }


def answer_question(client: OpenAI, model: str, question: str, ontology: str, graph: Graph) -> str:
    # 给模型实体标识与中文标签，关系和类型的匹配交给实际查询。
    labels = sorted(
        f"{entity.n3(graph.namespace_manager)}  {label.n3()}"
        for entity, label in graph.subject_objects(RDFS.label)
    )
    instruction = (
        "根据问题、本体定义（Turtle）和实体索引，生成一条可在本地 RDF 图运行的 SPARQL 1.1 SELECT。"
        "图已经过 OWL 2 RL 推理。使用给定的类和属性，按实体标识定位，返回明细时尽量选择中文标签。"
        "计数时留意去重。只输出完整查询，包含所需 PREFIX。使用默认图，避免 FROM 和 SERVICE。"
        "如本体缺少回答问题所需的概念或属性，只输出 NO_QUERY。\n\n"
        f"本体定义\n{ontology}\n实体索引\n" + "\n".join(labels)
    )
    generated = complete(client, model, instruction, question)
    if generated == "NO_QUERY":
        return "当前本体缺少回答这个问题所需的概念或属性。"
    fence = re.fullmatch(r"```(?:sparql)?\s*\n(.*?)\n```", generated, flags=re.IGNORECASE | re.DOTALL)
    sparql = fence.group(1).strip() if fence else generated
    print(f"\n模型生成的 SPARQL\n{sparql}", flush=True)

    DeductiveClosure(OWLRL_Semantics).expand(graph)
    try:
        result = execute_select(graph, sparql)
    except Exception as exc:
        # RDFLib 的语法、前缀解析和执行错误有多种异常类型。
        raise ValueError(f"SPARQL 查询失败（{exc}）") from exc
    print(f"\n查询结果\n{json.dumps(result, ensure_ascii=False, indent=2)}", flush=True)
    if not result["数据行"]:
        return "查询未匹配到记录，当前图中的资料不足以回答这个问题。"

    return complete(
        client, model,
        "用中文回答原问题。以查询返回的列名和数据行为事实依据。null 表示该项未知。"
        "结果已截断时，说明回答只覆盖所示行。若结果不足以回答，指出缺少的资料。",
        json.dumps({"问题": question, "SPARQL": sparql, "查询结果": result}, ensure_ascii=False),
    )


def compare_resources(graph: Graph) -> dict:
    print(QUESTION)
    before = query_resources(graph)
    print_results("推理前", before)
    DeductiveClosure(OWLRL_Semantics).expand(graph)
    after = query_resources(graph)
    print_results("推理后", after)
    return {"问题": QUESTION, "推理前": before, "推理后": after}


def main() -> None:
    load_dotenv(HERE.parent / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--llm", action="store_true", help="用模型解释固定查询的推理前后结果")
    mode.add_argument("--query", metavar="问题", help="让模型根据本体生成 SPARQL 并回答问题")
    parser.add_argument("--model", default=os.getenv("MODEL"), help="模型名称（默认读 MODEL）")
    parser.add_argument("--api_key", default=os.getenv("API_KEY"), help="API Key（默认读 API_KEY）")
    parser.add_argument(
        "--base_url", default=os.getenv("API_BASE", "https://api.siliconflow.cn/v1"),
        help="API 基础地址（默认读 API_BASE，未设置时用硅基流动）",
    )
    args = parser.parse_args()
    if args.query is not None and not args.query.strip():
        parser.error("--query 需要一个非空问题。")
    if (args.llm or args.query) and not (args.api_key and args.model):
        parser.error("调用模型时，请设置 API_KEY 和 MODEL，或传入 --api_key 和 --model。")

    graph = Graph()
    ontology = (HERE / "ontology.ttl").read_text(encoding="utf-8")
    graph.parse(data=ontology, format="turtle", publicID=(HERE / "ontology.ttl").as_uri())
    graph.parse(HERE / "assets.ttl", format="turtle")

    if args.query:
        print(args.query, flush=True)
    else:
        context = compare_resources(graph)
        if not args.llm:
            return

    try:
        with OpenAI(api_key=args.api_key, base_url=args.base_url, timeout=60.0) as client:
            if args.query:
                answer = answer_question(client, args.model, args.query, ontology, graph)
            else:
                answer = complete(
                    client, args.model, "请依据推理后的查询结果回答问题，并指出新增的资源。"
                    "负责团队为 null 表示图中尚未记录。", json.dumps(context, ensure_ascii=False),
                )
    except OpenAIError as exc:
        parser.exit(1, f"模型调用失败（{type(exc).__name__}）。请检查模型、密钥和端点配置。\n")
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")
    title = "最终回答" if args.query else "模型回答"
    print(f"\n{title}\n{answer}")


if __name__ == "__main__":
    main()
