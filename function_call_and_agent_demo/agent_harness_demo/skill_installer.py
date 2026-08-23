# -*- coding: utf-8 -*-
"""运行时 skill 安装器：install_skill 工具 + skill 清单热刷新。

deepagents 的 SkillsMiddleware 只在会话启动时扫描一次（before_agent 有 state 去重
守卫，无官方 reload 机制），但系统提示词里的 skill 清单每次模型调用都从
state["skills_metadata"] 重新渲染——本模块据此实现"装完即用"：

    install_skill 工具：校验（zip-slip / frontmatter 规范）→ 解压到 skills/<name>/
    → 重扫 sources → Command(update={"skills_metadata": ...}) 热刷新，
    下一轮模型调用 skill 清单即包含新装项，无需重启会话。

RefreshableSkillsMiddleware 以同名（"SkillsMiddleware"）替换官方中间件：
主 agent 获得 install_skill 工具，subagent 的 skills 继承路径保持官方行为。

注意：_list_skills_with_errors 是 deepagents 0.7.x 私有函数（重扫结果与官方扫描完全
一致的唯一途径），requirements.txt 已锁 deepagents>=0.7,<0.8，升级需同步适配。
"""
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

import yaml
from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.types import Command
from pydantic import BaseModel, Field

from deepagents.middleware.skills import SkillsMiddleware, _list_skills_with_errors

MAX_SKILL_MD_SIZE = 10 * 1024 * 1024     # 对齐 deepagents 的 SKILL.md 上限
MAX_DESCRIPTION_LENGTH = 1024            # 对齐 Agent Skills 规范
MAX_NAME_LENGTH = 64
MAX_ZIP_DEPTH = 3                        # SKILL.md 在 zip 内的最大目录深度
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class SkillInstallError(Exception):
    """校验/安装失败，message 面向学员可读，直接回传给模型。"""


# ---------------------------------------------------------------- 校验

def parse_frontmatter(text: str) -> dict:
    """解析 SKILL.md 的 YAML frontmatter，格式非法时抛 SkillInstallError。"""
    if not text.startswith("---"):
        raise SkillInstallError("SKILL.md 必须以 YAML frontmatter 开头（第一行是 `---`，"
                                "随后是 name/description 字段，再以 `---` 结束）。")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SkillInstallError("SKILL.md 的 frontmatter 没有闭合：需要第二个 `---` 结束 frontmatter。")
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        raise SkillInstallError(f"SKILL.md 的 frontmatter 不是合法 YAML：{e}")
    if not isinstance(data, dict):
        raise SkillInstallError("SKILL.md 的 frontmatter 必须是键值对（name、description 等）。")
    return data


def validate_skill_md(md_path: Path, dir_name: str) -> dict:
    """校验单个 skill 目录的 SKILL.md，返回解析出的 frontmatter。

    校验规则对齐 Agent Skills 规范与 deepagents 行为；deepagents 对缺字段是
    静默跳过，安装器必须显式报错——否则用户以为装好了实际清单里没有。
    """
    if not md_path.is_file():
        raise SkillInstallError(f"目录 {dir_name}/ 里没有 SKILL.md——skill 的必备文件。")
    if md_path.stat().st_size > MAX_SKILL_MD_SIZE:
        raise SkillInstallError(f"SKILL.md 超过 10MB 上限（当前 {md_path.stat().st_size // 1024 // 1024}MB）。")
    fm = parse_frontmatter(md_path.read_text(encoding="utf-8", errors="replace"))

    name = str(fm.get("name") or "").strip()
    if not name:
        raise SkillInstallError("frontmatter 缺少 name 字段（或为空）。")
    if len(name) > MAX_NAME_LENGTH:
        raise SkillInstallError(f"name 超过 {MAX_NAME_LENGTH} 字符（当前 {len(name)}）。")
    if not NAME_RE.match(name):
        raise SkillInstallError(f"name '{name}' 不合规：只能用小写字母、数字和单个连字符，"
                                "且不能以连字符开头/结尾（例如 annual-report-to-kb）。")
    if name != dir_name:
        raise SkillInstallError(f"name '{name}' 与目录名 '{dir_name}' 不一致——"
                                "把目录改名为 name，或改 frontmatter 的 name，二者必须相同。")

    description = str(fm.get("description") or "").strip()
    if not description:
        raise SkillInstallError("frontmatter 缺少 description 字段：这是第 1 层披露中 agent "
                                "判断『要不要加载这个 skill』的唯一依据，必填。")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise SkillInstallError(f"description 超过 {MAX_DESCRIPTION_LENGTH} 字符"
                                f"（当前 {len(description)}），请收敛到一句话+触发场景。")
    return fm


# ---------------------------------------------------------------- zip / 目录安装

def _check_zip_entries(zf: zipfile.ZipFile) -> None:
    """zip-slip 防护：逐条目拒绝绝对路径、`..` 路径段、符号链接。"""
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = PurePosixPath(info.filename)
        if info.filename.startswith(("/", "\\")) or (len(info.filename) > 1 and info.filename[1] == ":"):
            raise SkillInstallError(f"zip 内出现绝对路径条目：{info.filename}（疑似 zip-slip 攻击，已拒绝）。")
        if ".." in name.parts:
            raise SkillInstallError(f"zip 内条目含 `..` 路径段：{info.filename}（疑似 zip-slip 攻击，已拒绝）。")
        mode = (info.external_attr >> 16) & 0o170000
        if mode == stat.S_IFLNK:
            raise SkillInstallError(f"zip 内条目是符号链接：{info.filename}（不允许，已拒绝）。")


def _locate_skill_root_in_zip(zf: zipfile.ZipFile) -> PurePosixPath:
    """定位 zip 内唯一的 SKILL.md 所在目录（支持 .qoder/skills/<name>/ 等嵌套布局）。"""
    roots = set()
    for info in zf.infolist():
        if info.is_dir():
            continue
        p = PurePosixPath(info.filename)
        if p.name == "SKILL.md":
            roots.add(p.parent)
    if not roots:
        raise SkillInstallError("zip 里找不到 SKILL.md——确认打包的是 skill 目录本身。")
    if len(roots) > 1:
        raise SkillInstallError(f"zip 里有 {len(roots)} 个 SKILL.md（{', '.join(map(str, sorted(roots)))}），"
                                "一次只装一个 skill，请重新打包。")
    root = roots.pop()
    if len(root.parts) > MAX_ZIP_DEPTH:
        raise SkillInstallError(f"SKILL.md 嵌套层级过深（{root}，超过 {MAX_ZIP_DEPTH} 层）。")
    return root


def install_from_zip(zip_path: Path, skills_dir: Path) -> tuple[str, int]:
    """校验并解压 zip 到 skills/<name>/，返回 (skill 名, 文件数)。任一步失败零残留。"""
    with zipfile.ZipFile(zip_path) as zf:
        _check_zip_entries(zf)
        root = _locate_skill_root_in_zip(zf)
        with tempfile.TemporaryDirectory(prefix="skill_install_") as tmp:
            staging = Path(tmp) / root.name
            count = 0
            for info in zf.infolist():
                if info.is_dir():
                    continue
                p = PurePosixPath(info.filename)
                # 只解压 skill 根子树；目标路径由我们自己拼接，不走 zipfile 的路径解析
                if p.parent != root and root not in p.parents:
                    continue
                rel = p.relative_to(root)
                target = staging.joinpath(*rel.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                count += 1
            validate_skill_md(staging / "SKILL.md", root.name)
            dest = skills_dir / root.name
            if dest.exists():
                raise SkillInstallError(f"skills/{root.name}/ 已存在——先删除旧目录再安装"
                                        f"（卸载即删除目录：rm -rf skills/{root.name}/）。")
            skills_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staging), str(dest))
            return root.name, count


def install_from_dir(src: Path, skills_dir: Path) -> tuple[str, int]:
    """校验并拷贝目录型 skill（src 指向 skill 根或其上层一层目录均可）。"""
    root = src if (src / "SKILL.md").is_file() else None
    if root is None:
        candidates = [c for c in src.iterdir() if c.is_dir() and (c / "SKILL.md").is_file()]
        if len(candidates) == 1:
            root = candidates[0]
        elif not candidates:
            raise SkillInstallError(f"{src} 下找不到 SKILL.md（当前目录或一级子目录都没有）。")
        else:
            raise SkillInstallError(f"{src} 下有 {len(candidates)} 个含 SKILL.md 的子目录，"
                                    "请把 source_path 指向具体的某个 skill 目录。")
    validate_skill_md(root / "SKILL.md", root.name)
    dest = skills_dir / root.name
    if dest.exists():
        raise SkillInstallError(f"skills/{root.name}/ 已存在——先删除旧目录再安装。")
    skills_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root, dest)
    count = sum(1 for _ in dest.rglob("*") if _.is_file())
    return root.name, count


# ---------------------------------------------------------------- Middleware

class InstallSkillArgs(BaseModel):
    source_path: str = Field(description="skill 来源路径（相对工作目录）：zip 包或 skill 目录，"
                                         "如 skill_submissions/annual-report-to-kb.zip")


class RefreshableSkillsMiddleware(SkillsMiddleware):
    """SkillsMiddleware 的可安装扩展：贡献 install_skill 工具 + 装后热刷新。

    name 覆写为父类名，使 create_deep_agent 里它原地替换默认 SkillsMiddleware
    （避免两个 skills 中间件各注入一段重复的系统提示词清单）。
    """

    def __init__(self, *, skills_root: Path, install_root: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._skills_root = skills_root      # 真实文件系统上的 skills/ 目录
        self._install_root = install_root    # source_path 的解析根（本 demo 目录）
        self.tools = [self._create_install_tool()]

    @property
    def name(self) -> str:  # noqa: D102 - 见类 docstring
        return "SkillsMiddleware"

    def _rescan_sources(self) -> tuple[list[dict], list[str]]:
        """重扫全部 sources，与官方 before_agent 相同的合并语义（后源覆盖同名）。"""
        merged: dict[str, dict] = {}
        load_errors: list[str] = []
        for source in self.sources:
            skills, error = _list_skills_with_errors(self._backend, source)
            if error:
                load_errors.append(error)
            for skill in skills:
                merged[skill["name"]] = skill
        return list(merged.values()), load_errors

    def _create_install_tool(self) -> BaseTool:
        middleware = self

        def install_skill(source_path: str, runtime: ToolRuntime) -> ToolMessage | Command:
            """安装一个第三方 Agent Skill（zip 包或目录），装完立即可用。

            校验并解压到 skills/<name>/，随后热刷新 skill 清单——安装成功后的
            下一轮对话即可按渐进式披露使用（先 read_file 它的 SKILL.md）。
            校验失败返回可读的错误原因，不做任何落盘。
            """
            # 解析并限定 source_path 在 harness 工作目录内
            src = (middleware._install_root / source_path.lstrip("/")).resolve()
            try:
                if middleware._install_root not in src.parents:
                    raise SkillInstallError(f"source_path 越界：{source_path}（只允许工作目录内的路径）。")
                if src.suffix.lower() == ".zip":
                    if not src.is_file():
                        raise SkillInstallError(f"找不到 zip 包：{source_path}")
                    name, count = install_from_zip(src, middleware._skills_root)
                elif src.is_dir():
                    name, count = install_from_dir(src, middleware._skills_root)
                else:
                    raise SkillInstallError(f"source_path 既不是 .zip 也不是目录：{source_path}")
            except SkillInstallError as e:
                return ToolMessage(content=f"安装失败：{e}", name="install_skill",
                                   tool_call_id=runtime.tool_call_id, status="error")
            except Exception as e:  # noqa: BLE001 - 未知异常也要以可读形式回传给模型
                return ToolMessage(content=f"安装失败（未预期的错误）：{type(e).__name__}: {e}",
                                   name="install_skill", tool_call_id=runtime.tool_call_id, status="error")

            # 热刷新：重扫 sources 并更新 state，下一次模型调用即生效
            skills, load_errors = middleware._rescan_sources()
            names = ", ".join(s["name"] for s in skills)
            summary = (f"已安装 skill '{name}'（{count} 个文件 → skills/{name}/）。\n"
                       f"当前 skill 清单：{names}\n"
                       f"建议下一步：read_file('skills/{name}/SKILL.md') 了解其用法后再执行任务。")
            return Command(update={
                "messages": [ToolMessage(content=summary, name="install_skill",
                                         tool_call_id=runtime.tool_call_id, status="success")],
                "skills_metadata": skills,
                "skills_load_errors": load_errors,
            })

        return StructuredTool.from_function(
            name="install_skill",
            description="安装一个第三方 Agent Skill（zip 包或目录）。source_path 为工作目录内的相对路径，"
                        "如 skill_submissions/annual-report-to-kb.zip。安装成功后 skill 立即可用。",
            func=install_skill,
            args_schema=InstallSkillArgs,
            infer_schema=False,
        )
