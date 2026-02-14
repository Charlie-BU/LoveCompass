## Context 衰减策略

- 有效权重公式 ：effective_weight = effective_weight = weight \* confidence \* decay_factor
- 衰减函数 ：decay_factor = exp(-ln(2) \* delta_days / half_life_days)
- 半衰期建议
    - CHAT_LOG：7–14 天
    - INTERACTION_SIGNAL：14–30 天
    - DERIVED_INSIGHT：30–60 天
    - STATIC_PROFILE：180–365 天
    - STAGE_EVENT：90–180 天
- 更新规则
    - 当 context 被检索/引用/进入提示词时，更新 last_used_at
    - 当系统识别为冲突或被更高置信度替代，weight 乘以 0.3–0.6 或设 is_active=false
- 淘汰阈值
    - effective_weight < 0.1 且 last_used_at 超过半衰期 2–4 倍时，自动失活
- 调度频率
    - 每日批处理更新衰减因子与失活状态
- 核心原则
    - “不修改内容，只改变影响力与可用性”，与你的不可变语义一致
