## Embedding 召回策略

`recallEmbeddingFromDB` 的召回流程由「参数校验 → 源范围归一化 → 向量召回 → 业务过滤 → 打分排序」组成。

### 召回来源归一化规则

- 当 `recall_from` 包含 `all` 时，会被重写为：
    - `["knowledge", "crush_profile", "event", "chat_topic", "derived_insight"]`
- 当 `recall_from` 包含 `non-knowledge` 时，会被重写为：
    - `["crush_profile", "event", "chat_topic", "derived_insight"]`

注意：`non-knowledge` 逻辑在 `all` 之后执行，如果两者同时出现，最终以 `non-knowledge` 的重写结果为准（不含 `knowledge`）。

### 向量候选集查询

- 将来源字符串映射为 `EmbeddingType`：
    - `knowledge` -> `FROM_KNOWLEDGE`
    - `crush_profile` -> `FROM_CRUSH_PROFILE`
    - `event` -> `FROM_EVENT`
    - `chat_topic` -> `FROM_CHAT_TOPIC`
    - `derived_insight` -> `FROM_DERIVED_INSIGHT`
- 使用 `ContextEmbedding.embedding.cosine_distance(vector)` 计算距离
- 查询条件与顺序：
    - `ContextEmbedding.type in selected_types`
    - 按距离升序（越小越相似）
    - 候选数限制：`limit(int(os.getenv("VECTOR_CANDIDATES")))`

### 候选逐条业务过滤与字段抽取

每条候选会根据 `embedding.type` 分支读取关联对象并抽取：

- 公共输出字段：
    - `data`：对应实体的 `toJson()` 结果
    - `weight`：对应实体权重，默认 `1.0`
    - `created_at`：仅部分类型参与时间衰减

分支规则：

- `FROM_KNOWLEDGE`：
    - 使用 `embedding.knowledge`
    - `weight = knowledge.weight`
    - 不做 relation_chain 过滤
- `FROM_CRUSH_PROFILE`：
    - 使用 `embedding.crush`
    - 若存在 `crush_id` 且 `embedding.crush.id != crush_id`，跳过
    - `weight = crush.weight`
    - 不参与时间衰减
- `FROM_EVENT`：
    - 使用 `embedding.event`
    - 若传入 `relation_chain_id` 且不等于 `event.relation_chain_id`，跳过
    - `weight = event.weight`
    - `created_at = event.created_at`
- `FROM_CHAT_TOPIC`：
    - 使用 `embedding.chat_topic`
    - 若传入 `relation_chain_id` 且不等于 `chat_topic.relation_chain_id`，跳过
    - `weight = chat_topic.weight`
    - `created_at = chat_topic.created_at`
- `FROM_DERIVED_INSIGHT`：
    - 使用 `embedding.derived_insight`
    - 若传入 `relation_chain_id` 且不等于 `derived_insight.relation_chain_id`，跳过
    - `weight = derived_insight.weight`
    - `created_at = derived_insight.created_at`

若类型与关联对象不匹配，直接跳过该候选。

### 评分公式

- 语义分：`semantic_score = 1 - distance`
- 时间衰减：
    - 若有 `created_at`：`time_decay = exp(-delta_days / HALF_LIFE_DAYS)`
    - 若无 `created_at`：`time_decay = 1.0`
- 融合分（未衰减）：
    - `raw_score = semantic_score * 0.8 + weight * 0.2`
- 最终分：
    - `score = raw_score * time_decay`

其中：

- `delta_days = (now_utc - created_at).days`
- 若 `created_at` 无时区信息，会按 UTC 处理
- `HALF_LIFE_DAYS` 来自环境变量

### 排序与截断

- 所有有效候选按 `score` 降序排序
- 取前 `top_k` 条作为返回 `items`
