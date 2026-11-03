#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
十一步超级学习法 - 学习会话进度管理

用法:
  python session.py init  --workspace <工作区绝对路径> --topic "<主题>" [--type skill|industry] [--goal "<终点目标>"]
  python session.py show  --workspace <工作区绝对路径> [--topic "<主题>"]
  python session.py list  --workspace <工作区绝对路径>
  python session.py set   --workspace <工作区绝对路径> --step 3 [--status done] [--summary "<产出摘要>"] [--topic "<主题>"]
  python session.py note  --workspace <工作区绝对路径> --step 3 --text "<踩坑/偏好记录>" [--topic "<主题>"]
  python session.py retry --workspace <工作区绝对路径> --step 3 --reason "<未通过的断言>" [--topic "<主题>"]
  python session.py reset --workspace <工作区绝对路径> --topic "<主题>"

状态文件: <workspace>/.workbuddy/learning/<主题slug>/progress.json
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TOTAL_STEPS = 11

STEP_NAMES = {
    1: "动态专家视角拆解",
    2: "矛盾与盲区清单",
    3: "精炼行动简报",
    4: "可信度评分与验证规划",
    5: "精选资料与一周路线",
    6: "5阶通关卡牌（微实践）",
    7: "20小时攻坚 + S级实战项目",
    8: "10道实战场景考核",
    9: "费曼学习法（角色互换）",
    10: "战地速查表与Skill沉淀",
    11: "艾宾浩斯15核心知识点记忆系统",
}

STATUS_ICON = {"pending": "○", "in_progress": "◐", "done": "●"}


def slugify(topic: str) -> str:
    s = re.sub(r'[\\/:*?"<>|\s]+', "-", topic.strip())
    s = re.sub(r"-+", "-", s).strip("-")
    return (s[:40] or "topic")


def learning_root(workspace: str) -> Path:
    return Path(workspace) / ".workbuddy" / "learning"


def state_file(workspace: str, topic: str) -> Path:
    return learning_root(workspace) / slugify(topic) / "progress.json"


def resolve_state(workspace: str, topic: str = None) -> Path:
    if topic:
        p = state_file(workspace, topic)
        if not p.exists():
            raise SystemExit(f"[错误] 未找到主题「{topic}」的状态文件：{p}\n请先运行 init，或用 list 查看已有主题。")
        return p
    root = learning_root(workspace)
    if not root.exists():
        raise SystemExit(f"[错误] 工作区下还没有任何学习会话：{root}\n请先运行 init。")
    files = sorted(root.glob("*/progress.json"))
    if len(files) == 0:
        raise SystemExit("[错误] 未找到任何 progress.json，请先运行 init。")
    if len(files) > 1:
        names = [f.parent.name for f in files]
        raise SystemExit("[错误] 存在多个学习主题，请用 --topic 指定。已有主题：" + "、".join(names))
    return files[0]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def new_state(topic: str, ltype: str, goal: str) -> dict:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return {
        "topic": topic,
        "type": ltype,
        "goal": goal,
        "created_at": now,
        "updated_at": now,
        "current_step": 1,
        "steps": {str(i): {"status": "pending", "summary": "", "retries": 0, "updated_at": ""} for i in range(1, TOTAL_STEPS + 1)},
        "notes": [],
    }


def render_panel(data: dict, path: Path) -> str:
    topic = data["topic"]
    ltype = data.get("type", "-")
    cur = data.get("current_step", 1)
    done = sum(1 for v in data["steps"].values() if v.get("status") == "done")
    lines = []
    lines.append("")
    lines.append(f"主题：{topic} | 类型：{ltype} | 进度：Step {cur}/11 | 已完成：{done}/11")
    if data.get("goal"):
        lines.append(f"终点目标：{data['goal']}")
    lines.append(f"状态文件：{path}")
    lines.append("")
    lines.append("| # | 步骤 | 状态 | 产出摘要 | 重试 |")
    lines.append("|---|---|---|---|---|")
    for i in range(1, TOTAL_STEPS + 1):
        v = data["steps"].get(str(i), {})
        icon = STATUS_ICON.get(v.get("status", "pending"), "○")
        mark = " ← 当前" if i == cur else ""
        lines.append(f"| {i} | {STEP_NAMES[i]}{mark} | {icon} {v.get('status','pending')} | {v.get('summary','')} | {v.get('retries',0)} |")
    lines.append("")
    return "\n".join(lines)


def cmd_init(args):
    path = state_file(args.workspace, args.topic)
    if path.exists() and not args.force:
        print(f"[提示] 该主题已存在：{path}")
        print(render_panel(load(path), path))
        return
    data = new_state(args.topic, args.type, args.goal or "")
    save(path, data)
    print(f"[OK] 已初始化学习会话：{path}")
    print(render_panel(data, path))
    print("规则：11 步单步推进，每步输出前执行自我验证（不通过则重写，最多 5 次），一步一确认。")
    print('👉 请回复确认后进入 Step 1：动态专家视角拆解')


def cmd_show(args):
    path = resolve_state(args.workspace, args.topic)
    print(render_panel(load(path), path))


def cmd_list(args):
    root = learning_root(args.workspace)
    if not root.exists():
        print("[提示] 暂无学习会话。")
        return
    files = sorted(root.glob("*/progress.json"))
    if not files:
        print("[提示] 暂无学习会话。")
        return
    print("| 主题 | 类型 | 当前步骤 | 已完成 | 更新时间 |")
    print("|---|---|---|---|---|")
    for f in files:
        d = load(f)
        done = sum(1 for v in d["steps"].values() if v.get("status") == "done")
        print(f"| {d['topic']} | {d.get('type','-')} | Step {d.get('current_step',1)} | {done}/11 | {d.get('updated_at','')} |")


def cmd_set(args):
    path = resolve_state(args.workspace, args.topic)
    data = load(path)
    key = str(args.step)
    if key not in data["steps"]:
        raise SystemExit(f"[错误] step 必须在 1-{TOTAL_STEPS} 之间")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    st = data["steps"][key]
    st["status"] = args.status
    if args.summary:
        st["summary"] = args.summary
    st["updated_at"] = now
    data["updated_at"] = now
    if args.status == "done" and data.get("current_step", 1) == args.step and args.step < TOTAL_STEPS:
        data["current_step"] = args.step + 1
        data["steps"][str(args.step + 1)]["status"] = "in_progress"
    save(path, data)
    print(f"[OK] Step {args.step} → {args.status}")
    print(render_panel(data, path))


def cmd_note(args):
    path = resolve_state(args.workspace, args.topic)
    data = load(path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    data.setdefault("notes", []).append({
        "step": args.step,
        "at": now,
        "text": args.text,
    })
    data["updated_at"] = now
    save(path, data)
    print(f"[OK] 已记录备注（Step {args.step}）：{args.text}")


def cmd_retry(args):
    path = resolve_state(args.workspace, args.topic)
    data = load(path)
    key = str(args.step)
    st = data["steps"].setdefault(key, {"status": "pending", "summary": "", "retries": 0, "updated_at": ""})
    st["retries"] = int(st.get("retries", 0)) + 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    st["updated_at"] = now
    data.setdefault("notes", []).append({"step": args.step, "at": now, "text": f"[自检未通过] {args.reason}"})
    data["updated_at"] = now
    save(path, data)
    n = st["retries"]
    print(f"[OK] Step {args.step} 自检重试计数：{n}/5 —— {args.reason}")
    if n >= 5:
        print("[提醒] 已达 5 次上限：必须向用户透明说明卡点、给出当前最优解，并说明需要用户补充什么。")


def cmd_reset(args):
    if not args.topic:
        raise SystemExit("[错误] reset 必须指定 --topic")
    path = state_file(args.workspace, args.topic)
    if not path.exists():
        print("[提示] 该主题不存在，无需重置。")
        return
    path.unlink()
    print(f"[OK] 已删除：{path}")


def main():
    p = argparse.ArgumentParser(description="十一步超级学习法 进度管理")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("init", help="初始化学习会话")
    g.add_argument("--workspace", required=True)
    g.add_argument("--topic", required=True)
    g.add_argument("--type", default="skill", choices=["skill", "industry", "mixed"])
    g.add_argument("--goal", default="")
    g.add_argument("--force", action="store_true")
    g.set_defaults(func=cmd_init)

    g = sub.add_parser("show", help="查看进度面板")
    g.add_argument("--workspace", required=True)
    g.add_argument("--topic")
    g.set_defaults(func=cmd_show)

    g = sub.add_parser("list", help="列出所有学习主题")
    g.add_argument("--workspace", required=True)
    g.set_defaults(func=cmd_list)

    g = sub.add_parser("set", help="更新步骤状态")
    g.add_argument("--workspace", required=True)
    g.add_argument("--topic")
    g.add_argument("--step", type=int, required=True)
    g.add_argument("--status", default="done", choices=["pending", "in_progress", "done"])
    g.add_argument("--summary", default="")
    g.set_defaults(func=cmd_set)

    g = sub.add_parser("note", help="追加备注")
    g.add_argument("--workspace", required=True)
    g.add_argument("--topic")
    g.add_argument("--step", type=int, required=True)
    g.add_argument("--text", required=True)
    g.set_defaults(func=cmd_note)

    g = sub.add_parser("retry", help="记录一次自检重试")
    g.add_argument("--workspace", required=True)
    g.add_argument("--topic")
    g.add_argument("--step", type=int, required=True)
    g.add_argument("--reason", required=True)
    g.set_defaults(func=cmd_retry)

    g = sub.add_parser("reset", help="删除某个主题的状态")
    g.add_argument("--workspace", required=True)
    g.add_argument("--topic")
    g.set_defaults(func=cmd_reset)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
