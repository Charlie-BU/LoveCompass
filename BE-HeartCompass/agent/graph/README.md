## GraphState 字段是否可为 None

StateGraph 里，GraphState 本质上是**工作流全过程的状态快照**，而不是“单次输入的结构”。这意味着：

- 有些字段是**输入必需**，从第一个节点开始就应该存在（所以不可为 None）。
- 有些字段是**中间产物**，只有在某些节点执行后才会产生（所以在流程早期必须允许为 None）。
- 还有一些字段是**条件性产物**，比如可选召回、可选画像、可选偏好设置——在某些分支或异常路径下可能不存在（所以也应允许为 None）。

简化成一句话：  
**GraphState 表达的是“流程状态”，而不是“固定的最终结构”。**

---

举个例子：

- **request.user_id**  
  这是入口信息，没有它无法继续 → 不该允许 None

- **entities.crush**  
  这是通过 relation_chain 查询得出的中间产物  
  在 node_load_entities 之前当然可能为空 → 应允许 None

- **recall_query.embedding_vector**  
  是向量化后才会产生的 → 在 node_vectorize_query 之前必须是 None

- **profile_context.crush_mbti**  
  依赖 crush 是否填写 MBTI  
  即便节点执行完成，也可能没有 MBTI → 应允许 None

---

**GraphState 的字段“是否允许 None”由两件事决定：**

1. 该字段是“入口必需”还是“过程产物”
2. 该字段是“必须产生”还是“条件性产生”
