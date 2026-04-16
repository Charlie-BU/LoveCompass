# FRBuildingGraph

这个 graph 用于根据用户输入的内容材料，抽取有价值的信息，完善当前 figure_and_relation 的信息。

## 完善方式包括

- 更新 FigureAndRelation:
  抽取有价值的字段并按照各字段格式更新到当前 figure_and_relation 中
- 添加细粒度信息 FineGrainedFeed：
  根据 recipe 按照 FineGrainedFeedDimension 抽取有价值的信息，写入 FineGrainedFeed 表
- 修改：
  根据当前 figure_and_relation 中的信息，判断用户是否需要修改当前 figure_and_relation 中的信息
  根据已有 fine_grained_feed，判断用户是否需要修改当前 figure_and_relation 中的信息

## 工作流设计

1. 首节点用户输入原始文本内容 raw_content（和原始图片url raw_images，如有），随当前 user_id 和 fr_id 一并作为初始 Request invoke
2. 首先使用 checkFigureAndRelationOwnership 根据 fr_id 得到当前 figure_and_relation
3. 得到当前 figure_and_relation.figure_role
4. 预处理 raw_content（和原始图片url raw_images，如有）：
   根据 figure_role 和内容理解得到 OriginalSourceType、confidence、included_dimensions、approx_date（如有）
   将文本清洗，得到 content。保证有价值内容必须 100% 完整，不能缺失任何重要信息。去除重复内容及废话。
   使用方法 src/services/fine_grained_feed.py addOriginalSource 落库
5. 更新 FigureAndRelation 中的固有字段：
   5.1 通过 original_source.content 抽取以下字段，只抽取明确提及或可显然推断的字段。
        - figure_mbti
        - figure_birthday
        - figure_occupation
        - figure_education
        - figure_residence
        - figure_hometown
        - figure_likes
        - figure_dislikes
        - figure_appearance
        - words_figure2user
        - words_user2figure
        - exact_relation
    5.2 匹配 FigureAndRelation 表中对应字段格式
    5.3 对于每个抽取的字段，和 FigureAndRelation 中现有值进行对比：
        - 若现有值为空，直接更新
        - 若新值是现有值的补充，合并到现有值中
        - 若新值与现有值存在矛盾，更新为新值
    方法：src/services/figure_and_relation.py updateFigureAndRelation
6. 添加 / 更新 FineGrainedFeed 细粒度信息
   6.1 根据当前 figure_role 取到相应的 prompt：`await getPrompt(os.getenv(f"FR_BUILDING_{figure_role.value.upper()}"))`
   6.2 根据当前 original_source.included_dimensions 中的维度，分别取到相应的 prompt：`await getPrompt(os.getenv(f"FR_BUILDING_{included_dimension.upper()}"))`
   6.3 根据 6.1 和 6.2 中的 prompt 组合，并行抽取各个维度信息。抽取后的每条信息格式如下：
   {
      "dimension": FineGrainedFeedDimension
      "sub_dimension": str
      "content": str
   }
   6.4 遍历每条抽取的信息
        6.4.1 使用其 content 作为 query 在 FineGrainedFeed 中召回相应维度的 fine_grained_feed，top-k 取 3-5（需测试，取决于响应速度），召回方法：src/services/fine_grained_feed.py recallFineGrainedFeeds
        6.4.2 遍历每条召回的 fine_grained_feed.content，使用方法 `_compareFieldViaLLM()` 与当前抽取的信息 content 进行对比，设置 handled_flag 为 False
            - 若二者无关（tag = "irrelevant"），continue 跳过
            - 若新 content 与召回 fine_grained_feed.content 相同（tag = "equivalent"），设置 handled_flag 为 True，break 跳出循环
            - 若新 content 是召回 fine_grained_feed.content 的补充（tag = "supplementary"），或判定使用新内容（tag = "new_adopted"），则将合并后的内容 final_value 更新到召回 fine_grained_feed.content 中，使用方法：src/services/fine_grained_feed.py updateFineGrainedFeed；设置 handled_flag 为 True，之后 break 跳出循环
            <!-- - **重要**若新 content 与召回 fine_grained_feed.content 存在矛盾（tag = "conflictive"），**触发一次 interrupt**，待用户决定采用新内容还是召回内容。之后根据用户的选择确定是否更新。若更新，使用方法：src/services/fine_grained_feed.py updateFineGrainedFeed；设置 handled_flag 为 True，之后 break 跳出循环 -->
            - **降级方案**若新 content 与召回 fine_grained_feed.content 存在矛盾（tag = "conflictive"），加入 Conflict 表中，status 设为 pending，之后 fine_grained_feed.content 更新为 final_value（是 new_value，但未经用户确认），具体待后续处理；设置 handled_flag 为 True，之后 break 跳出循环
        6.4.3 若 handled_flag 仍为 False，说明当前抽取的信息 content 与召回 fine_grained_feed.content 无关，直接添加到 FineGrainedFeed 表中
            方法：src/services/fine_grained_feed.py addFineGrainedFeed
7. graph 完成，返回日志

【过程中实时记录日志】