"""code.py 的长期记忆可视化版本。

保留原 s09 Agent 的长期记忆实现，并在存储、召回、注入、提取和整合
五个阶段输出可读的记忆状态。运行时输入 /memory 可随时查看记忆库。
"""

import importlib.util
import json
import os
from collections import Counter
from pathlib import Path


def _load_base_module():
    """按文件路径加载 code.py，避免和 Python 标准库 code 模块冲突。"""
    source = Path(__file__).with_name("code.py")
    spec = importlib.util.spec_from_file_location("agent_09_base", source)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load base agent: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_base_module()

MEMORY_PREVIEW_CHARS = int(os.getenv("MEMORY_PREVIEW_CHARS", "120"))


def _one_line(value, limit: int = MEMORY_PREVIEW_CHARS) -> str:
    text = " ".join(str(value).replace("\x1b", "<ESC>").split())
    return text if len(text) <= limit else text[:limit] + "..."


def _record_map(records: list[dict]) -> dict[str, dict]:
    return {record["filename"]: record for record in records}


def print_memory_store(stage: str, records: list[dict] | None = None) -> None:
    """打印磁盘长期记忆库的目录、分类和内容预览。"""
    records = base.list_memory_files() if records is None else records
    type_counts = Counter(record.get("type", "unknown") for record in records)
    total_chars = sum(len(record.get("body", "")) for record in records)
    index = base.read_memory_index()

    print("\n" + "=" * 84)
    print(f"[长期记忆可视化] {stage}")
    print(f"存储目录 : {base.MEMORY_DIR}")
    print(f"索引文件 : {base.MEMORY_INDEX}")
    print(
        f"记录数量 : {len(records)}  类型统计={dict(type_counts)}  "
        f"正文总量={total_chars} chars"
    )
    print(f"索引大小 : {len(index)} chars")
    print("-" * 84)
    if not records:
        print("  （长期记忆库为空）")
    for number, record in enumerate(records, 1):
        body = record.get("body", "")
        print(
            f"  {number:02d}. [{record.get('type', 'unknown')}] "
            f"{record.get('name', '(unnamed)')}"
        )
        print(
            f"      文件={record.get('filename')}  正文={len(body)} chars  "
            f"描述={_one_line(record.get('description', ''))}"
        )
        print(f"      预览={_one_line(body)}")
    print("=" * 84)


def print_store_change(
    before: list[dict], after: list[dict], stage: str
) -> None:
    """比较一次操作前后的长期记忆文件。"""
    old = _record_map(before)
    new = _record_map(after)
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    changed = sorted(
        filename
        for filename in old.keys() & new.keys()
        if old[filename] != new[filename]
    )

    print(f"\n[长期记忆变化] {stage}")
    print(f"  新增={added or '无'}")
    print(f"  更新={changed or '无'}")
    print(f"  删除={removed or '无'}")
    print(f"  记录数={len(before)} -> {len(after)}")
    print_memory_store(f"{stage}后的记忆库", after)


def load_memories_visual(messages: list) -> str:
    """选择并加载与当前请求相关的长期记忆，同时展示召回过程。"""
    records = base.list_memory_files()
    query = base.recent_user_text(messages)

    print_memory_store("召回前：磁盘中的全部长期记忆", records)
    print("\n[长期记忆召回]")
    print(f"  查询依据: {_one_line(query, 240) or '（无用户文本）'}")
    print(f"  候选记录: {len(records)}")

    selected = base.select_relevant_memories(messages)
    print(f"  选中记录: {selected or '无'}")

    loaded = []
    remaining = base.RECALL_CHAR_LIMIT
    for filename in selected:
        content = base.read_memory_file(filename)
        if not content or remaining <= 0:
            continue
        recalled = content[:remaining]
        loaded.append({"source": filename, "content": recalled})
        remaining -= len(recalled)
        print(
            f"  加载 {filename}: {len(recalled)} chars，"
            f"剩余预算 {remaining}/{base.RECALL_CHAR_LIMIT}"
        )

    if not loaded:
        print("  注入结果: 本轮没有相关长期记忆")
        return ""

    result = json.dumps(loaded, ensure_ascii=False, indent=2)
    print(f"  注入结果: {len(loaded)} 条，共 {len(result)} chars")
    print(f"  内容预览: {_one_line(result, 300)}")
    return result


def extract_memories_visual(messages: list) -> int:
    """调用原提取算法，并打印实际写入长期记忆库的变化。"""
    before = base.list_memory_files()
    dialogue = base.dialogue_text(messages)
    print("\n[长期记忆提取]")
    print(f"  检查对话: {len(dialogue)} chars")
    print(f"  对话预览: {_one_line(dialogue, 300)}")
    print("  判定规则: 只保存跨会话仍有价值的稳定事实、偏好、反馈或引用")

    stored = base.extract_memories(messages)
    after = base.list_memory_files()
    print(f"  提取结果: 写入 {stored} 条记录")
    print_store_change(before, after, "提取")
    return stored


def consolidate_memories_visual() -> int:
    """调用原整合算法，并展示去重/合并造成的文件变化。"""
    before = base.list_memory_files()
    print("\n[长期记忆整合]")
    print(
        f"  当前记录={len(before)}，触发阈值={base.CONSOLIDATE_THRESHOLD}"
    )
    if len(before) < base.CONSOLIDATE_THRESHOLD:
        print("  未达到阈值，本轮不整合")
        return 0

    result = base.consolidate_memories()
    after = base.list_memory_files()
    print_store_change(before, after, "整合")
    return result


def agent_loop(messages: list) -> None:
    """运行 Agent，并可视化每一轮长期记忆的数据流。"""
    relevant_memories = load_memories_visual(messages)
    system = base.build_system(relevant_memories)
    print("\n[长期记忆注入 System Prompt]")
    print(f"  System Prompt 总长度: {len(system)} chars")
    print(f"  相关记忆长度: {len(relevant_memories)} chars")

    while True:
        response = base.client.messages.create(
            model=base.MODEL,
            system=system,
            messages=messages,
            tools=base.TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [
            block
            for block in response.content
            if getattr(block, "type", None) == "tool_use"
        ]
        if not tool_calls:
            force = base.trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": force})
                continue
            if extract_memories_visual(messages):
                consolidate_memories_visual()
            else:
                print("\n[长期记忆] 本轮没有新增持久记忆")
            return

        results = []
        for block in tool_calls:
            print(f"\033[36m> {block.name}\033[0m")
            output = base.execute_tool(block)
            print(output[:200])
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })
        messages.append({"role": "user", "content": results})


def print_final_answer(history: list) -> None:
    if not history:
        return
    content = history[-1].get("content", [])
    if not isinstance(content, list):
        return
    for block in content:
        if getattr(block, "type", None) == "text":
            print(block.text)


def main() -> None:
    print("agent_09: Long-term Memory Visualization")
    print("输入问题开始任务；输入 /memory 查看长期记忆；输入 q 退出。\n")
    print_memory_store("启动时的长期记忆库")

    history = []
    while True:
        try:
            query = input("\001\033[36m\002s09 >> \001\033[0m\002")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        if query.strip().lower() in ("/memory", "memory"):
            print_memory_store("用户主动查看")
            continue

        base.trigger_hooks("UserPromptSubmit", query)
        history.append({"role": "user", "content": query})
        agent_loop(history)
        print_final_answer(history)
        print()


if __name__ == "__main__":
    main()
