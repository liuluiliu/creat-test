"""agent_08 的记忆可视化版本。

本文件复用 agent_08.py 的工具、Hook 和上下文压缩逻辑，只增加观察代码：
每次用户输入、模型回复、工具结果和上下文压缩时，都通过 print 输出当前记忆状态。
"""

import json
import os
from typing import Any

import agent_08 as base


MEMORY_VIEW_MAX_MESSAGES = int(os.getenv("MEMORY_VIEW_MAX_MESSAGES", "20"))
MEMORY_PREVIEW_CHARS = int(os.getenv("MEMORY_PREVIEW_CHARS", "100"))


def _block_type(block: Any) -> str:
    if isinstance(block, dict):
        return str(block.get("type", "dict"))
    return str(getattr(block, "type", type(block).__name__))


def _block_value(block: Any, name: str, default: Any = "") -> Any:
    if isinstance(block, dict):
        return block.get(name, default)
    return getattr(block, name, default)


def _one_line(value: Any, limit: int = MEMORY_PREVIEW_CHARS) -> str:
    """把记忆内容变成适合终端查看的单行预览。"""
    if not isinstance(value, str):
        try:
            value = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            value = str(value)
    value = " ".join(value.replace("\x1b", "<ESC>").split())
    return value if len(value) <= limit else value[:limit] + "..."


def _message_description(message: dict) -> tuple[str, str]:
    content = message.get("content", "")
    if isinstance(content, str):
        return "text", _one_line(content)
    if not isinstance(content, list):
        return type(content).__name__, _one_line(content)

    kinds = []
    previews = []
    for block in content:
        kind = _block_type(block)
        kinds.append(kind)
        if kind == "text":
            previews.append(_one_line(_block_value(block, "text")))
        elif kind == "tool_use":
            name = _block_value(block, "name", "unknown")
            tool_input = _block_value(block, "input", {})
            previews.append(f"调用 {name}({_one_line(tool_input, 60)})")
        elif kind == "tool_result":
            result = _block_value(block, "content", "")
            previews.append(f"结果 {_one_line(result, 70)}")
        else:
            previews.append(_one_line(block, 70))
    return "+".join(kinds) or "empty", " | ".join(previews)


def _visible_indexes(count: int) -> list[int | None]:
    """长会话只显示头尾，中间用 None 表示省略行。"""
    if count <= MEMORY_VIEW_MAX_MESSAGES:
        return list(range(count))
    head = max(2, MEMORY_VIEW_MAX_MESSAGES // 3)
    tail = max(2, MEMORY_VIEW_MAX_MESSAGES - head)
    return [*range(head), None, *range(count - tail, count)]


def print_memory_state(messages: list, stage: str, previous_chars: int | None = None) -> None:
    """打印模型当前可见的短期记忆，不修改 messages。"""
    chars = base.ContextCompactor.estimate_chars(messages)
    limit = base.ContextCompactor.CONTEXT_CHAR_LIMIT
    ratio = chars / limit if limit else 0
    filled = min(30, round(ratio * 30))
    bar = "#" * filled + "-" * (30 - filled)

    role_counts: dict[str, int] = {}
    tool_uses = 0
    tool_results = 0
    for message in messages:
        role = str(message.get("role", "unknown"))
        role_counts[role] = role_counts.get(role, 0) + 1
        content = message.get("content")
        if isinstance(content, list):
            tool_uses += sum(_block_type(block) == "tool_use" for block in content)
            tool_results += sum(_block_type(block) == "tool_result" for block in content)

    print("\n" + "=" * 78)
    print(f"[记忆可视化] {stage}")
    delta = "" if previous_chars is None else f"  变化={chars - previous_chars:+d} chars"
    print(f"容量 [{bar}] {chars}/{limit} chars ({ratio:.1%}){delta}")
    print(
        f"消息={len(messages)}  角色={role_counts}  "
        f"工具调用={tool_uses}  工具结果={tool_results}"
    )
    print("-" * 78)

    omitted = max(0, len(messages) - MEMORY_VIEW_MAX_MESSAGES)
    for index in _visible_indexes(len(messages)):
        if index is None:
            print(f"  ... 中间 {omitted} 条消息未展开 ...")
            continue
        message = messages[index]
        role = str(message.get("role", "unknown"))
        kind, preview = _message_description(message)
        size = len(json.dumps(message, ensure_ascii=False, default=str))
        print(f"  M{index:03d} [{role:<9}] [{kind:<20}] {size:>6} chars | {preview}")
    print("=" * 78)


class VisualContextCompactor(base.ContextCompactor):
    """在原压缩算法的关键边界打印记忆状态。"""

    def save_output(self, tool_use_id: str, output: str):
        path = super().save_output(tool_use_id, output)
        print(f"[长期记忆] 大工具结果已落盘: {path} ({len(output)} chars)")
        return path

    def write_transcript(self, messages: list):
        path = super().write_transcript(messages)
        print(f"[长期记忆] 完整会话已归档: {path} ({len(messages)} messages)")
        return path

    def prepare(self, messages: list, active_request: str) -> list:
        before_chars = self.estimate_chars(messages)
        prepared = super().prepare(messages, active_request)
        after_chars = self.estimate_chars(prepared)
        action = "压缩后" if after_chars != before_chars else "发送模型前（无需压缩）"
        print_memory_state(prepared, action, previous_chars=before_chars)
        return prepared

    def compact_history(self, messages: list, active_request: str) -> list:
        print_memory_state(messages, "手动/自动压缩前")
        compacted = super().compact_history(messages, active_request)
        print_memory_state(
            compacted,
            "摘要记忆生成后",
            previous_chars=self.estimate_chars(messages),
        )
        return compacted

    def reactive_compact(self, messages: list, active_request: str) -> list:
        print_memory_state(messages, "超出模型上下文后的应急压缩前")
        compacted = super().reactive_compact(messages, active_request)
        print_memory_state(
            compacted,
            "应急压缩后",
            previous_chars=self.estimate_chars(messages),
        )
        return compacted


COMPACTOR = VisualContextCompactor(
    base.client,
    base.MODEL,
    base.TRANSCRIPT_DIR,
    base.TOOL_RESULTS_DIR,
)


def agent_loop(messages: list, active_request: str) -> None:
    """运行 Agent，并在每次记忆发生变化后输出可视化。"""
    reactive_retries = 0
    while True:
        # 切片赋值保证发生摘要压缩后，主程序的 history 也同步更新。
        messages[:] = COMPACTOR.prepare(messages, active_request)
        try:
            response = base.client.messages.create(
                model=base.MODEL,
                system=base.SYSTEM,
                messages=messages,
                tools=base.TOOLS,
                max_tokens=8000,
            )
            reactive_retries = 0
        except Exception as error:
            too_long = any(
                text in str(error).lower()
                for text in ("prompt_too_long", "too many tokens")
            )
            if too_long and reactive_retries < base.MAX_REACTIVE_RETRIES:
                print("[reactive compact]")
                messages[:] = COMPACTOR.reactive_compact(messages, active_request)
                reactive_retries += 1
                continue
            raise

        messages.append({"role": "assistant", "content": response.content})
        print_memory_state(messages, "模型回复写入记忆后")

        tool_calls = [
            block for block in response.content
            if getattr(block, "type", None) == "tool_use"
        ]
        if not tool_calls:
            force = base.trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": force})
                print_memory_state(messages, "Stop Hook 追加继续指令后")
                continue
            print_memory_state(messages, "本轮结束时的最终记忆")
            return

        results = []
        compact_requested = False
        for block in tool_calls:
            print(f"\033[36m> {block.name}\033[0m")
            if block.name == "compact":
                output = "Compaction requested after this tool batch."
                compact_requested = True
            else:
                output = base.execute_tool(block)
                print(output[:200])
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })

        messages.append({"role": "user", "content": results})
        print_memory_state(messages, "工具结果写入记忆后")
        if compact_requested:
            messages[:] = COMPACTOR.compact_history(messages, active_request)


def main() -> None:
    print("agent_08t: Context Memory Visualization")
    print("输入问题后，可观察短期记忆、工具结果落盘和上下文压缩。输入 q 退出。\n")

    history = []
    while True:
        try:
            query = input("\001\033[36m\002s08t >> \001\033[0m\002")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})
        print_memory_state(history, "用户请求写入记忆后")
        agent_loop(history, active_request=query)

        content = history[-1].get("content", [])
        if isinstance(content, list):
            for block in content:
                if getattr(block, "type", None) == "text":
                    print(block.text)
        print()


if __name__ == "__main__":
    main()
