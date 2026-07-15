# Codex Feishu Auto

把 Codex 定时任务、飞书 CLI、状态文件和可选的高频截图组合成一套可交接的监控工作流。

它适合三类任务：

- **发布会直播**：10 秒保留现场，1 至 5 分钟判断价值，只把重要材料写进飞书。
- **夜间选题值班**：定时扫描多个信号源，去重、分级提醒，早晨自动收官。
- **服务器巡检**：按日或按周读取容器、日志、数据库和 API，输出有证据的状态结论。

这不是“到点生成一段文字”的提示词包。它实现的是同一条有状态循环：

```text
定时唤醒 -> 读取现场 -> 采集新增 -> 判断价值 -> 写入飞书
         -> 回读验证 -> 保存状态 -> 告警或收官
```

## 安装

### 依赖

- Codex Desktop，或其他能加载 Codex Skill 的环境
- Python 3.9+
- Node.js 16+（仅用于安装 `lark-cli`）
- [lark-cli](https://github.com/larksuite/cli) 可执行文件及有效飞书授权
- macOS 截图模式额外需要 Google Chrome、`osascript`、`screencapture` 和 `swift`

尚未安装飞书 CLI 时：

```bash
npm install -g @larksuite/cli
lark-cli config init --new
```

### 从 GitHub 安装

```bash
git clone https://github.com/xiaoyao-tech/codex_feishu_auto.git
cd codex_feishu_auto
./install.sh
```

也可以从 [Releases](https://github.com/xiaoyao-tech/codex_feishu_auto/releases/latest) 下载打包好的 `codex-feishu-auto.skill`。

默认安装到：

```text
${CODEX_HOME:-$HOME/.codex}/skills/codex-feishu-auto
```

检查依赖：

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-feishu-auto/scripts/doctor.py"
```

更新已有安装：

```bash
git pull
./install.sh --force
```

## 30 秒快速开始

下面以一场 AI 发布会为例。先初始化独立工作目录：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/codex-feishu-auto"
WATCH_DIR="${CODEX_HOME:-$HOME/.codex}/state/codex-feishu-auto/demo-launch"

python3 "$SKILL_DIR/scripts/init_watch.py" \
  --name "Demo AI 发布会" \
  --mode live-event \
  --output-dir "$WATCH_DIR" \
  --feishu-doc "https://example.feishu.cn/wiki/REPLACE_ME" \
  --source "官方直播字幕|https://example.com/live" \
  --source "官方博客|https://example.com/news" \
  --source "媒体 liveblog|https://example.com/liveblog" \
  --capture \
  --capture-keyword "Demo AI" \
  --capture-keyword "YouTube"
```

再生成适合交给 Codex Automation 的提示词：

```bash
python3 "$SKILL_DIR/scripts/render_prompt.py" \
  --config "$WATCH_DIR/config.json" \
  --format markdown \
  --output "$WATCH_DIR/automation_prompt.md"
```

最后在 Codex 中说：

```text
读取这个 Skill 和 automation_prompt.md，帮我启动发布会监控。
```

Skill 会优先使用 Codex 的 automation 工具创建真实任务；如果当前环境没有调度工具，它会明确给出建议频率和完整提示词，不会假装任务已经启动。

## 高频截图（macOS，可选）

先检查权限与依赖：

```bash
"$SKILL_DIR/scripts/capture_watch.sh" --check
```

启动截图循环：

```bash
"$SKILL_DIR/scripts/capture_watch.sh" \
  --output-dir "$WATCH_DIR/captures" \
  --interval 10 \
  --keywords "Demo AI,YouTube,liveblog"
```

脚本只在 Chrome 当前标签标题命中关键词时截图。停止方式：

```bash
touch "$WATCH_DIR/captures/STOP_CAPTURE"
```

截图循环和 Codex 判断循环是两只不同的时钟。脚本负责不漏画面，Codex 负责筛选、解释和写入飞书。

## 状态管理

每个工作目录都包含：

```text
config.json             任务边界、来源、频率和飞书目标
state.json              阶段、去重集合、连续无新增次数、最新 revision
duty_log.md             每轮最重要的判断与收官材料
automation_prompt.md     渲染后的自动化提示词
captures/raw_watch/      原始截图
captures/selected/       人或 Codex 选出的关键图
logs/                    本地运行日志
```

更新状态示例：

```bash
python3 "$SKILL_DIR/scripts/statectl.py" record \
  --state "$WATCH_DIR/state.json" \
  --new-count 2 \
  --seen "official:gpt-x" \
  --revision "42" \
  --next-watch "API 价格"

python3 "$SKILL_DIR/scripts/statectl.py" should-close \
  --state "$WATCH_DIR/state.json" \
  --threshold 3
```

## 三种模式

| 模式 | 适用任务 | 建议频率 | 重点 |
|---|---|---:|---|
| `live-event` | 发布会、直播、财报会 | 30 分钟逐步升至 1-5 分钟 | 来源等级、关键画面、事件阶段、退出条件 |
| `topic-duty` | 夜间选题、热点雷达 | 15-60 分钟 | 去重、二次评分、低噪声、早晨 TOP3 |
| `ops-check` | 服务器和数据链路巡检 | 每天或每周 | 只读优先、分层健康、生产真相、密钥脱敏 |

详细规则见：

- [`references/live-event.md`](codex-feishu-auto/references/live-event.md)
- [`references/topic-duty.md`](codex-feishu-auto/references/topic-duty.md)
- [`references/ops-check.md`](codex-feishu-auto/references/ops-check.md)
- [`references/feishu-cli.md`](codex-feishu-auto/references/feishu-cli.md)

## 飞书原则

1. 写之前读取当前文档。
2. 普通直播日志用 `append`，精确位置用最新 block ID。
3. 图片路径使用当前目录下的相对路径。
4. 写完必须再读取，确认 revision、位置、图片、链接和结构。
5. 飞书当前版本优先于自动化旧记忆；人工删除的内容不要擅自恢复。
6. 未经确认，不向任何群或个人发送提醒。

## 安全边界

- 仓库不包含飞书 token、chat ID、服务器地址或 API key。
- `config.json` 可能含内部文档地址，默认不要提交任务工作目录。
- 运维模式默认只读。任何删除、重启、部署或高风险飞书操作都要再次取得用户确认。
- 截图前使用标题关键词限制目标窗口，避免把无关或私密页面收入素材目录。
- 日志输出前屏蔽 `sk-`、token、cookie、webhook 和私钥路径。

## 开发与验证

```bash
python3 -m unittest discover -s tests -v
python3 /path/to/skill-creator/scripts/quick_validate.py ./codex-feishu-auto
```

真实场景测试定义在 [`codex-feishu-auto/evals/evals.json`](codex-feishu-auto/evals/evals.json)。

## License

MIT
