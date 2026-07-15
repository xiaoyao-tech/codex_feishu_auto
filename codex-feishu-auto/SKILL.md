---
name: codex-feishu-auto
description: "Build and run stateful Codex automations that monitor live launches, perform overnight topic duty, or inspect server health, then write verified updates to Feishu through lark-cli. Use this skill whenever the user asks to盯发布会、抓文字直播、定时截图、持续更新飞书、今天值班、监控热点到明早、设置每日/每周巡检、检查服务器定时任务，或希望把 Codex Automations 与飞书 CLI 组合起来。即使用户只说‘帮我定时盯着并写进飞书’，也应使用本 skill，把任务设计成读现场、去重、判断、写入、回读验证、保存状态和按条件退出的完整循环。"
compatibility: "Python 3.9+; lark-cli for Feishu operations; Codex automation tools when scheduling is requested; macOS and Google Chrome only for the optional screenshot loop."
---

# Codex + 飞书 CLI 自动化

把定时任务做成一个可以持续接班、可被人工随时接管的循环。定时器只负责叫醒；每轮醒来后必须重新读取现场、判断新增、写入目标、回读验证并保存状态。

## 核心协议

每轮按这个顺序执行：

1. 确认当前时间、时区和任务阶段。
2. 读取 `config.json`、`state.json`、`duty_log.md` 和飞书当前版本。
3. 从配置中的来源收集本轮新增；单个来源失败时记录错误并继续。
4. 去重并区分 `官方确认 / 媒体报道 / 社区线索 / 待验证`。
5. 判断为什么现在重要、是否值得打断用户、还缺什么证据。
6. 只有产生新价值时才写飞书；无新增时保持短报。
7. 写后重新读取飞书，验证 revision、位置、链接、图片或表格结构。
8. 更新状态和下一轮关注点。
9. 达到结束时间或连续无新增阈值时收官，并暂停或删除高频自动化。

不要把旧聊天上下文当作当前现场。飞书当前版本和生产系统当前状态优先；人工删除或改写的内容不要擅自恢复。

## 选择模式

根据用户目标选择一种主模式：

- **`live-event`**：发布会、直播、财报会、赛事或政策发布。读取 [`references/live-event.md`](references/live-event.md)。
- **`topic-duty`**：夜间选题、热点巡逻、次日早晨收官。读取 [`references/topic-duty.md`](references/topic-duty.md)。
- **`ops-check`**：服务器、数据链路、定时任务和产物巡检。读取 [`references/ops-check.md`](references/ops-check.md)。

涉及飞书读写时同时读取 [`references/feishu-cli.md`](references/feishu-cli.md)。需要设计调度和停止条件时读取 [`references/automation-design.md`](references/automation-design.md)。

## 首次初始化

当用户明确要求开始监控或建立任务时，直接创建工作目录，不停留在方案描述。

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/codex-feishu-auto"
WATCH_DIR="${CODEX_HOME:-$HOME/.codex}/state/codex-feishu-auto/<task-slug>"

python3 "$SKILL_DIR/scripts/init_watch.py" \
  --name "<任务名>" \
  --mode <live-event|topic-duty|ops-check> \
  --output-dir "$WATCH_DIR" \
  --timezone "<IANA 时区>" \
  --feishu-doc "<用户提供或确认的文档 URL>" \
  --source "<来源名>|<URL或命令说明>"
```

只有发布会确实需要高频画面时才加 `--capture` 和多个 `--capture-keyword`。服务器巡检不要启用截图。

如果工作目录已存在，先读取并复用；除非用户明确要求重建，不要用 `--force` 覆盖状态。

## 生成自动化提示词

```bash
python3 "$SKILL_DIR/scripts/render_prompt.py" \
  --config "$WATCH_DIR/config.json" \
  --format markdown \
  --output "$WATCH_DIR/automation_prompt.md"
```

检查渲染结果是否包含：

- 明确的时区与任务阶段；
- 来源和来源等级；
- 飞书读后写、写后读；
- 状态文件路径；
- 低噪声规则和强提醒阈值；
- 收官时间与自动化清理动作。

## 创建真实调度

用户要求“开始”“设置”“帮我盯着”时，应创建真实自动化，不要只返回一段 cron 文本。

1. 先查找并使用当前环境提供的 `automation_update` 或等价自动化工具。
2. 发布会和夜间值班优先用当前任务的 heartbeat，便于用户随时纠偏。
3. 每日/每周分析巡检可用本地 Codex cron。
4. 数据、代码和凭据本来就在服务器且不能依赖本机在线时，使用服务器原生 cron/systemd；写入前先检查已有调度，避免重复。
5. 当前环境没有调度工具时，输出完整提示词和建议频率，并明确说明“尚未启动”，不能假装任务已经运行。

同一任务尽量只维持一个活跃 heartbeat。巡逻和固定时间收官可以合并进同一提示词：每轮先检查当前时间，再选择巡逻或收官分支。

## 飞书写入规则

明确指定 `--api-version v2` 和身份：

- 用户自有材料通常用 `--as user`。
- 机器人维护的共享表格通常用 `--as bot`。
- 身份和权限不确定时先只读测试；不要因为 user 授权噪声放弃一个已经可用的 bot 路径。

每次写入：

1. `docs +fetch --detail full` 获取最新 revision 和 block ID。
2. 直播时间线优先 `append`。
3. 顶部判断使用本轮新取得的 block ID 做 `block_insert_after`。
4. 结构化表格使用 XML 整块 `block_replace`，不要用 Markdown 字符串拼接破坏表格。
5. 图片从图片所在目录执行 `docs +media-insert --file ./relative.png`。
6. 再次 `fetch` 验证结果。

未经用户确认，不向任何飞书 chat ID 发提醒。高风险写操作遇到确认门禁时，展示动作和参数，等用户明确同意后再重试。

## 可选高频截图

截图和判断使用不同频率。截图负责不漏，Codex 负责取舍。

```bash
"$SKILL_DIR/scripts/capture_watch.sh" \
  --output-dir "$WATCH_DIR/captures" \
  --interval 10 \
  --keywords "<标题关键词1>,<标题关键词2>"
```

只在 macOS + Google Chrome 使用。先运行 `--check`，确认屏幕录制权限。标题关键词必须足够窄，避免截取无关页面。停止时创建：

```bash
touch "$WATCH_DIR/captures/STOP_CAPTURE"
```

不要声称所有原始截图都被审完。报告原始数量、进入候选区数量和最终使用数量时分别计数。

## 状态操作

用脚本原子更新 `state.json`，避免并发写坏 JSON：

```bash
python3 "$SKILL_DIR/scripts/statectl.py" record \
  --state "$WATCH_DIR/state.json" \
  --new-count <本轮新增数> \
  --seen "<稳定ID>" \
  --revision "<飞书revision>" \
  --next-watch "<下一轮线索>"
```

连续无新增达到阈值时：

```bash
python3 "$SKILL_DIR/scripts/statectl.py" should-close \
  --state "$WATCH_DIR/state.json" --threshold 3
```

值班日志保存编辑判断，不只保存链接。每轮最多追加 1 至 3 条真正会影响排序的内容。

## 告警

只有会改变优先级、需要用户立即决策的信号才强提醒。普通补料记录到日志即可。

```bash
python3 "$SKILL_DIR/scripts/alert.py" \
  --title "<任务>强提醒" \
  --message "<为什么现在必须看>"
```

只有用户已经确认 `CODEX_FEISHU_ALERT_CHAT_ID` 时才允许额外发送飞书消息。

## 错误处理

- 单个来源 403、429、502、超时或需登录：记录该路失败，继续使用其他来源。
- 飞书写入失败：不要更新成功 revision；保留本轮材料，下一轮重试前重新 fetch。
- block ID 失效：重新 fetch，不要拿旧 ID 连续重试。
- 公共 API 401：运维模式继续从生产 DB、容器日志或认证 API 验证，不要据此宣布服务宕机。
- macOS 后台截图权限失败：退回可见、可停止的终端或 `screen` 会话，不要声称 launchd 已可靠运行。
- 到期后仍被唤醒：立刻收官并清理自动化，不再做普通巡逻。

## 完成标准

只有同时满足以下条件才算完成：

- 真实自动化已创建，或明确说明当前环境无法创建；
- 工作目录、配置和状态文件可读；
- 飞书写入经过回读验证，或清楚记录未写入原因；
- 无新增时没有制造长篇噪声；
- 有明确退出条件；
- 没有泄露 token、cookie、chat ID、私钥路径或内部服务器地址；
- 给用户一段简短交接：当前阶段、最后成功时间、下一轮盯什么、如何停止。
