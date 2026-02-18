在本项目中，Agent 和 Ark Client 都应当设计为全局单例。

### 1. 为什么？

- 无状态的定义 (Stateless Definition) ：
    - 你的 ReActAgent (即 CompiledStateGraph ) 实际上是一个 执行引擎的定义 。它包含了图的结构（Nodes, Edges）、绑定的工具（Tools）和系统提示词（Prompt）。这些配置对所有用户都是通用的，不会随请求改变。
    - 因此，没有必要为每个请求重新编译这个图。

- 性能优化 (Performance) ：
    - LLM 初始化昂贵 ： prepareLLM() 会初始化 ChatOpenAI 客户端，这通常涉及连接池的建立。频繁创建销毁会增加延迟。
    - 图编译开销 ： create_agent 涉及 LangGraph 的图编译过程（包括状态定义的校验），这是一个计算密集型操作。单例模式只需在启动时执行一次。

- 并发安全 (Thread Safety) ：
    - LangGraph 的 CompiledStateGraph 本身是不可变的（Immutable）。
    - 当你调用 astream 或 ainvoke 时，LangGraph 会为这次特定的执行创建一个新的 Runner 。
    - 状态隔离 ：我在 agent/adapter.py 中确认了 convertReqToMessages 函数的存在，这证明了 对话状态（Context）是随请求传入的 ，而不是存储在 Agent 实例内部。因此，多个用户并发调用同一个 Agent 单例互不干扰。

### 2. 实现方式

`@lru_cache`装饰器缓存实例

### 3. 潜在的调整场景

虽然单例是目前最佳选择，但如果未来你的需求发生以下变化，可能需要利用 LangGraph 的 configurable 特性（依然保持单例，但注入配置）：

- 用户级工具 ：如果某个工具需要使用特定用户的 API Key（例如用户的 Gmail 访问权限）。
- 动态人设 ：如果 SYSTEM_PROMPT 需要根据用户的性格测试结果动态变化（目前的 Prompt 是固定的）。

