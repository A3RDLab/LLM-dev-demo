# Third-Party Notices and License Scope

This file explains the scope of the repository-level Apache License 2.0 and identifies material that remains subject to separate terms.

## Repository license scope

Unless a file or directory is identified below or carries its own notice, code and documentation authored by A³ R&D Lab contributors are licensed under the [Apache License 2.0](LICENSE).

The repository-level license does **not** grant rights that A³ R&D Lab does not own. Third-party software, model artifacts, datasets, reports, scraped content, and other source material remain subject to their original licenses, terms, and copyrights.

## Bundled third-party software and artifacts

### Anthropic `xlsx` Skill

- Path: `function_call_and_agent_demo/agent_harness_demo/skills/xlsx/`
- Source: [anthropics/skills](https://github.com/anthropics/skills)
- Copyright: © 2025 Anthropic, PBC
- Terms: `function_call_and_agent_demo/agent_harness_demo/skills/xlsx/LICENSE.txt`

This material is **not** licensed under Apache-2.0. Its bundled license contains restrictions on copying, retention, derivative works, and redistribution. Users must review and comply with Anthropic’s terms. Repository maintainers should not treat this directory as open-source material.

### DeepSeek tokenizer artifacts

- Path: `archive/deepseek_v3_tokenizer/`
- Origin: DeepSeek tokenizer/model distribution

Tokenizer artifacts and accompanying configuration remain subject to the terms published with their original DeepSeek distribution. They are excluded from this repository’s Apache-2.0 grant unless an individual file clearly states otherwise.

## Public datasets and example data

### Chinook sample database

- Path: `Chinook.sqlite`
- Project: [Chinook Database](https://github.com/lerocha/chinook-database)

The database is a third-party sample dataset and remains subject to the terms of its upstream project.

### Online Shoppers Purchasing Intention Dataset

- Path: `function_call_and_agent_demo/agent_harness_demo/data/public_online_shoppers_intention.csv`
- Source: [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset)

The dataset remains subject to the license and citation requirements stated by UCI.

### Public power-demand and weather sample

- Path: `archive/AI_Coding_demo/powerdemand_5min_2021_to_2024_with_weather.csv`

This file is retained as public example data. Its provenance is not currently documented in the repository, so it is excluded from the Apache-2.0 grant pending a source and license note.

### AI-generated or project-created samples

The synthetic sales workbooks, generated summaries, and fine-tuning examples created for this project are covered by the repository license only to the extent that A³ R&D Lab contributors hold the relevant rights. Files that embed third-party source material remain governed by the source material’s terms.

## Public reports and crawled documentation

The following materials are included as demonstration corpora or archived examples. Public availability does not transfer copyright or imply an open-source license:

- `PDF_RAG_demo/ICBC_2024_FYR.pdf`
- `archive/pdf_rag_demo_corpus/`
- `AliyunQA_RAG_demo/scrapy-prj-aliyunecs/qa.json`

These materials remain the property of their respective publishers or rights holders and are excluded from the repository’s Apache-2.0 grant. Users are responsible for complying with the original sites’ terms, copyright notices, and applicable law.

## Dependencies

Python packages installed through `requirements.txt` or `pyproject.toml` are not redistributed merely by being named as dependencies. Each dependency remains subject to its own upstream license.

## Corrections

If an attribution, source, or license entry is incomplete or inaccurate, please open an issue with the relevant upstream source and license evidence.
