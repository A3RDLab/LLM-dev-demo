# 本体与知识图谱实验

结算服务直接依赖哪些计算资源，各由哪个团队负责？这个实验用一份虚构的资源台账，演示如何把对「计算资源」和「负责关系」的定义写进本体，让同一条查询用上可推导的事实。

## 运行

在仓库根目录的 Python 虚拟环境中运行。安装依赖后，默认实验在本地完成，无需 API Key。

```bash
python -m pip install -r ontology_demo/requirements.txt
python ontology_demo/ontology_demo.py
```

```text
结算服务直接依赖哪些计算资源，各由哪个团队负责？

推理前（1 条）
  - 批处理节点（平台组）

推理后（3 条）
  - 批处理节点（平台组）
  - 结算虚拟机（平台组）
  - 结算容器工作负载（应用组）
```

## 跟踪查询结果

- 本体声明 `VirtualMachine` 和 `ContainerWorkload` 都是 `ComputeResource` 的子类。`manages` 和 `managedBy` 表达方向相反的同一负责关系。[查看本体定义](ontology.ttl)
- 资源台账记录实例及其关系。`checkoutVm` 的类型是 `VirtualMachine`，应用组通过 `manages` 关联到结算容器工作负载。本体和台账都用 Turtle 表示 RDF 三元组。[查看台账数据](assets.ttl)，[RDF 1.1 Turtle](https://www.w3.org/TR/turtle/)
- 脚本用 RDFLib 执行 SPARQL，匹配结算服务直接依赖且类型为 `ComputeResource` 的资源，再用 `OPTIONAL` 查询负责团队。团队关系缺失时，该资源仍可返回。[查看查询代码](ontology_demo.py)，[SPARQL 1.1 查询语言](https://www.w3.org/TR/sparql11-query/)

`owlrl` 在内存图里补出可推导的三元组。比如 `ex:checkoutVm a ex:VirtualMachine` 与 `ex:VirtualMachine rdfs:subClassOf ex:ComputeResource` 可推出 `ex:checkoutVm a ex:ComputeResource`。同样，应用组管理容器工作负载，可推出容器工作负载由应用组负责。查询因此能找到新增资源和负责团队。[RDF Schema 的子类语义](https://www.w3.org/TR/rdf-schema/#ch_subclassof)，[OWL 2 RL 的推理规则](https://www.w3.org/TR/owl2-profiles/#Reasoning_in_OWL_2_RL_and_RDF_Graphs_using_Rules)

### 动手试试

1. 在 `ontology.ttl` 中暂时去掉 `VirtualMachine` 的 `rdfs:subClassOf` 声明，保留 `ex:VirtualMachine a owl:Class .`。重跑后，结算虚拟机应从结果中消失。恢复原定义后再做下一步。
2. 暂时去掉 `owl:inverseOf ex:managedBy` 声明，把前一行的分号改成句号。重跑后，容器工作负载仍会出现，负责团队会显示为「图中尚未记录负责团队」。思考这个查询结果能说明什么，再恢复原定义。

## 选做 · 用模型讲解固定查询

按实验 0 设置根目录 `.env` 中的 `API_KEY`、`API_BASE`、`MODEL`，再运行下面的命令。也可以用 `--api_key`、`--base_url`、`--model` 覆盖配置。

```bash
python ontology_demo/ontology_demo.py --llm
```

模型收到问题与两次查询的 JSON 结果，用自然语言总结变化。对照终端里的查询输出，检查模型提到的资源与团队是否都有图数据依据。

## 自然语言问答 · Text2SPARQL

沿用上面的模型配置，用 `--query` 提出自己的问题。先查明细，再把问题改成计数。

```bash
python ontology_demo/ontology_demo.py --query "结算服务直接依赖哪些计算资源，各由哪个团队负责？"
python ontology_demo/ontology_demo.py --query "结算服务直接依赖多少个计算资源？"
```

1. **生成查询。** 模型读取问题、本体定义和实体名称索引。索引把「结算服务」对应到图中的标识符 `ex:checkout`，本体提供直接依赖关系 `ex:dependsOn` 和计算资源类 `ex:ComputeResource`。
2. **执行并核对。** 脚本打印模型生成的 SPARQL，在完成 OWL 推理的本地内存图上执行 `SELECT` 并显示结果。第一题应查到三个资源，负责团队可逐项对照上面的离线输出。
3. **用结果回答。** 模型依据查询结果作答。第二题应答 3 个。查看生成的查询是否同时限定了结算服务的直接依赖和计算资源类型。如果只统计直接依赖，就会把结算数据库也算进去，得到 4 个。明细查询返回空结果时，现有图数据不足以给出相应明细。

终端会显示实际返回的列名和数据行。明细过多时，脚本最多展示并交给模型 50 行，同时标记截断。像第二题这样的聚合先在图里完成，模型收到的是计数结果。

下面是计数题的一种等价写法，可与模型生成的语句对照。

```sparql
PREFIX ex: <https://example.org/llm-dev-demo/ontology#>
SELECT (COUNT(DISTINCT ?resource) AS ?count)
WHERE {
    ex:checkout ex:dependsOn ?resource .
    ?resource a ex:ComputeResource .
}
```
