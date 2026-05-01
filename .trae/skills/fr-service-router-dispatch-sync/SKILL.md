---
name: "fr-service-router-dispatch-sync"
description: "将现有业务方法抽离为 FR service，并同步新增 subrouter 与 SERVICE_API_MAP 映射。遇到“下沉 service + 包装路由 + 分发配置”类需求时调用。"
---

# FR Service Router Dispatch Sync

用于把已有业务逻辑从调用侧抽离到 `src/services/figure_and_relation.py`，并完成 `subrouters/fr.py` 与 `service_dispatcher.py` 的成套联动改造。

## 触发时机

- 用户要求将某个 FR 相关方法“提炼为 service”
- 用户要求“补一层路由”并可被 HTTP 调用
- 用户要求更新 `SERVICE_API_MAP` 以支持共享数据库模式分发
- 调用侧当前直接访问数据库，需改为走 service/dispatcher 统一链路

## 输入

- 待抽离的方法位置与代码片段
- 目标 service 文件：`src/services/figure_and_relation.py`
- 目标路由文件：`src/server/subrouters/fr.py`
- 目标分发表：`src/service_dispatcher.py`
- 调用侧文件（如 `src/channels/lark/integration/utils.py`）

## 步骤

1. 读取源方法与调用点，确认入参与返回值约定。
2. 在 `figure_and_relation.py` 新增同名或语义一致的 service：
   - 必须做参数类型校验。
   - 返回统一 `dict` 结构（至少包含 `status` 与 `message`）。
3. 在 `fr.py` 新增对应路由：
   - 优先使用 `auth_required=True`。
   - `user_id` 由 `getUserIdByAccessToken(request)` 提取。
   - 查询参数统一使用 `request.query_params.get("key", None)`。
4. 在 `SERVICE_API_MAP` 的 `# fr_router` 区域新增条目：
   - key 使用 service 函数名。
   - method/path/auth_required 与路由保持一致。
5. 改造调用侧：
   - 删除重复数据库访问逻辑。
   - 通过 `dispatchServiceCall(<service_fn>, args)` 调用。
   - 对响应做兼容解析，返回调用侧所需类型。
6. 自检：
   - 全局搜索确认新 service、router、map 已互相连通。
   - 使用 `GetDiagnostics` 检查修改文件，无新增错误。

## 输出 / 质量门槛

- 输出必须同时包含 4 类变更：
  - service 层新增函数
  - fr 子路由新增接口
  - SERVICE_API_MAP 新增映射
  - 调用侧改为通过 dispatcher 调用
- 返回结构与原调用行为保持兼容，不引入行为回归。
- 变更文件应按职责分类，避免把业务逻辑留在 integration 层直接查库。
