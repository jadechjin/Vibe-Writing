# Chat Provider 重构总结

## 问题背景

G1 图表规划的 AI Agent 对话功能存在以下问题：
1. 用户发送消息后，只看到 session ID，没有实际对话内容
2. 根本原因：CLI 输出协议与后端解析器不匹配

## 已完成的修复

### 1. 修复前缀匹配问题（短期止血）✅

**文件**: `backend/app/modules/evidence/service.py`

**修改**:
```python
# 行 1347
# 修改前：
if chunk.startswith("__SESSION_ID__:"):

# 修改后：
if chunk.strip().startswith("__SESSION_ID__:"):
```

**效果**: session ID 不再泄露到前端

### 2. 添加详细调试日志（高优先级）✅

**文件**: `backend/app/modules/evidence/chat_provider.py`

**新增功能**:
- 记录 CLI 命令
- 记录前 20 行原始 stdout 输出
- 记录 JSON 事件类型和字段
- 记录 session ID 提取过程
- 记录总结统计信息

**日志级别**:
- `INFO`: CLI 调用和完成信息
- `DEBUG`: 详细的输出解析过程
- `WARNING`: session ID 未找到等异常情况

### 3. 按 provider 拆分独立解析器（高优先级）✅

**文件**: `backend/app/modules/evidence/chat_provider.py`

**新增函数**:

#### `_parse_claude_stream_event(line: str) -> tuple[str | None, str | None]`
解析 Claude Code CLI 的 stream-json 事件：
- `{"type":"content_block_delta","delta":{"text":"..."}}`
- `{"type":"message","role":"assistant","content":"..."}`
- `{"type":"result","result":"..."}`
- 同时提取 `session_id` 或 `sessionId` 字段

#### `_parse_gemini_stream_event(line: str) -> tuple[str | None, str | None]`
解析 Gemini CLI 的 JSONL 事件流：
- `{"type":"message","role":"assistant","content":"..."}`
- 兼容旧格式 `{"text":"..."}`
- 兼容 fallback `{"content":"..."}`
- 同时提取 `session_id` 或 `sessionId` 字段

#### `_parse_codex_stream_line(line: str) -> tuple[str | None, str | None]`
解析 Codex (codeagent-wrapper) 的纯文本输出：
- 直接返回文本内容
- 过滤包含 session ID 的行
- 提取 session ID

**重构逻辑**:
- 每个 provider 使用独立的解析器
- 解析器返回 `(text_content, session_id)` 元组
- 在流式处理过程中同时提取内容和 session ID
- 避免了原来的"一个函数兼容多个协议"的脆弱设计

### 4. 修复 Claude CLI 命令（高优先级）✅

**文件**: `backend/app/modules/evidence/chat_provider.py`

**修改**:
```python
# 行 50
# 添加 --include-partial-messages 参数
cmd = ["claude", "-p", "--verbose", "--output-format", "stream-json",
       "--include-partial-messages"]
```

**效果**: 启用流式输出的部分内容，提高响应速度

### 5. 新增单元测试（高优先级）✅

**文件**: `backend/tests/modules/evidence/test_chat_provider_parsers.py`

**测试覆盖**:
- Claude 解析器：6 个测试用例
- Gemini 解析器：4 个测试用例
- Codex 解析器：3 个测试用例

**测试结果**: 13/13 通过 ✅

## 架构改进

### 修改前
```
invoke_chat_stream()
  ├─ if provider == CODEX: 纯文本处理
  └─ else: _extract_text_from_stream_json()
       └─ 尝试匹配多种 JSON 格式（脆弱）
```

### 修改后
```
invoke_chat_stream()
  ├─ if provider == CLAUDE: _parse_claude_stream_event()
  ├─ if provider == GEMINI: _parse_gemini_stream_event()
  └─ if provider == CODEX: _parse_codex_stream_line()
       └─ 每个解析器专注于自己的协议
```

## 验证步骤

### 1. 单元测试
```bash
cd backend
python -m pytest tests/modules/evidence/test_chat_provider_parsers.py -v
python -m pytest tests/modules/evidence/test_chat_provider.py -v
```

**结果**: 30/30 通过 ✅

### 2. 集成测试（待执行）
1. 重启后端服务
2. 打开 G1 图表规划页面
3. 发送测试消息
4. 观察：
   - 是否能看到 AI 的正常回复（不是 session ID）
   - 是否能正确续接对话
   - 检查后端日志中的调试信息

### 3. 日志验证
启用 DEBUG 日志级别，检查：
- CLI 原始输出格式
- JSON 事件类型
- 文本提取过程
- session ID 提取过程

## 后续优化（可选）

### 中优先级
- [ ] 优化前端 UI 状态管理，避免内容闪烁
- [ ] 添加更多真实 CLI 输出样本测试

### 低优先级
- [ ] 考虑统一 wrapper 输出协议（工程量大）

## 技术债务清理

### 已清理
- ✅ 移除了 `_extract_text_from_stream_json` 的脆弱协议猜测逻辑
- ✅ 统一了 session ID 提取方式
- ✅ 添加了完整的单元测试覆盖

### 保留（向后兼容）
- `_extract_text_from_stream_json` 函数保留但不再使用
- `extract_session_id` 函数作为 fallback 保留

## 参考资料

### 分析报告
- Gemini 分析：前端 UI 体验和前缀匹配问题
- Codex 分析：CLI 协议不匹配的根本原因

### 相关文档
- Claude Code SDK: https://docs.anthropic.com/en/docs/claude-code/sdk
- Gemini CLI README: `C:/Users/17162/AppData/Roaming/npm/node_modules/@google/gemini-cli/README.md`

## 总结

本次重构完成了以下目标：
1. ✅ 修复了 session ID 泄露问题
2. ✅ 重构了解析器架构，提高了可维护性
3. ✅ 添加了详细的调试日志
4. ✅ 添加了完整的单元测试
5. ✅ 修复了 Claude CLI 命令参数

**预期效果**:
- 用户能够正常看到 AI 的回复内容
- session ID 正确保存用于后续对话
- 代码更易维护和扩展
- 问题更容易调试和定位
