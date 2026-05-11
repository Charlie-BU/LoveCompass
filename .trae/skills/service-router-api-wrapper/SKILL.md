---
name: "service-router-api-wrapper"
description: "将 service 层方法按项目既有规范包装为 Robyn router 并暴露 HTTP API。用户提出“给 service 包一层 router”“暴露 http 接口”“按 user router 风格补接口”时必须触发；适用于 user、figure_and_relation、fine_grained_feed、knowledge 等模块。"
---

# Service Router API Wrapper（SOP）

用于把 `src/services/*.py` 的能力按项目约定包装到 `src/server/routers/*.py`，保证接口行为、返回格式、鉴权方式、代码风格一致，并可复用到多个业务模块。

## 适用范围

- 需要把 service 方法暴露成 HTTP API。
- 需要补齐或重构 router 层，但不能改变 service 层语义。
- 目标模块包括但不限于：`user`、`figure_and_relation`、`fine_grained_feed`、`knowledge`。

## 事实来源优先级

1. 目标 `service` 文件当前实现（第一依据）。
2. 目标 `router` 文件当前实现与风格（第二依据）。
3. 同项目其他 router（仅用于补充共性，不覆盖前两项）。

若三者冲突，以当前模块 `service + router` 现状为准，禁止按“理想结构”强行改写。

## 强制规范（必须执行）

1. 涉及用户 id 的获取，统一写法：
   `id = getUserIdByAccessToken(request=request)`
2. `GET` 请求参数一律走 query，统一写法：
   `request.query_params.get("xxx", None)`  
   必须传第二参数 `None`。
3. `POST` 请求参数一律走 body，统一写法：
   `body = request.json()`
4. service 返回值直接透传：
   `return service_method(...)`
5. router 层若需要直接返回错误，结构必须是：
    ```python
    {
        "status": int,      # 成功 200，失败负数
        "message": str,
        # 其他字段按场景补充
    }
    ```
6. 智能判断是否鉴权：
    - 需要用户上下文（尤其要拿用户 id）时：`auth_required=True`
    - 不需要鉴权时：不写 `auth_required` 参数
    - 凡是调用 `getUserIdByAccessToken(request=request)` 的接口，必须鉴权
7. 全局可复用的 util 方法沉淀到 `src/utils/index.py`，例如：
   - `parseInt()`
   - `parseFloat()`

## Router 包装步骤（标准流程）

1. 读取目标 `service`，列出候选暴露方法。
2. 过滤内部方法（仅内部调用、风险接口、注释标注不对外）不暴露。
3. 为每个方法定义 HTTP 语义：
    - 查询类优先 `GET`
    - 新增/登录/变更类优先 `POST`
4. 设计路由函数签名与命名，保持 `<serviceMethodName>Router` 风格。
5. 补齐参数读取与最小类型校验：
    - `GET` 从 `request.query_params.get("x", None)` 取值
    - `POST` 从 `body = request.json()` 后 `body.get("x", default)` 取值
6. 根据是否依赖当前用户决定 `auth_required`。
7. 若依赖当前用户，先取 id，再调用 service：
   `id = getUserIdByAccessToken(request=request)`
8. 调用 service 并直接返回结果，不二次包装。
9. 保留模块级异常处理、鉴权中间件、注释风格一致性。
10. 完成后做静态检查，确保无诊断错误。

## 代码模板（可直接套用）

```python
@xxx_router.get("/queryPath", auth_required=True)
async def queryRouter(request: Request):
    keyword = request.query_params.get("keyword", None)
    if keyword is None or not isinstance(keyword, str):
        return {"status": -1, "message": "Keyword is required"}
    id = getUserIdByAccessToken(request=request)
    return queryService(id=id, keyword=keyword)
```

```python
@xxx_router.post("/actionPath")
async def actionRouter(request: Request):
    body = request.json()
    field = body.get("field", "")
    if not isinstance(field, str):
        return {"status": -1, "message": "Field is invalid"}
    return actionService(field=field)
```

## 与现有风格对齐要点

- import 分组保持简洁稳定，先标准库再三方再本地模块。
- 路由定义延续 `SubRouter(__file__, prefix="/xxx")`。
- 全局异常处理保留统一行为，避免各接口重复 try/except。
- 函数注释保持中文短句，描述“做什么”，不写冗余实现细节。
- 变量命名沿用项目习惯：`res`、`body`、`user_id`、`keyword`。
- 返回字段命名与 service 保持一致，不做 router 层“翻译”。

## 跨模块复用清单

- `figure_and_relation`：先分查询接口与写入接口，查询走 `GET + query`，写入走 `POST + json`。
- `fine_grained_feed`：若有用户个性化逻辑，默认需要鉴权并从 token 拿用户 id。
- `knowledge`：纯公共检索可免鉴权；涉及用户态配置或个人视图必须鉴权。
- 任意模块：只要接口逻辑依赖当前登录用户，必须启用 `auth_required=True`。

## 自检清单（交付前）

- 是否所有 `GET` 参数都使用了 `request.query_params.get("x", None)`。
- 是否所有 `POST` 参数都来自 `request.json()`。
- 是否所有“拿用户 id”的地方都使用了 `getUserIdByAccessToken(request=request)`。
- 是否所有需要用户上下文的路由都加了 `auth_required=True`。
- 是否 service 返回结果被直接 `return`，未做二次改写。
- 是否 router 直接返回的错误结构符合 `{status, message, ...}`。
- 是否与目标 router 现有风格一致（命名、注释、结构、异常处理）。

## 禁止事项

- 禁止在 router 层重写 service 业务逻辑。
- 禁止使用 `request` 位置参数调用 `getUserIdByAccessToken`。
- 禁止 `GET` 参数读取省略 `None` 默认值。
- 禁止 `POST` 参数从 query/path 读取。
- 禁止把 service 的返回改成其他格式。
