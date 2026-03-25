# 弃用
# import time
# from langchain_core.messages import AIMessage, HumanMessage

# from src.agent.mem0 import (
#     mem0Client,
#     checkJobStatus,
#     addMemoryOnRelationChain,
#     getAllMemoriesByRelationChainId,
#     recallMemories,
#     getMemoryHistory,
#     updateMemory,
#     getMemoryDetail,
#     deleteMemory,
#     deleteAllMemoriesByRelationChainId,
# )
# from src.agent.adapter import langchain2OpenAIChatMessages


# mock_messages = langchain2OpenAIChatMessages(
#     [
#         HumanMessage(
#             content="你是谁\n今天去哪了\n你那边几点",
#             additional_kwargs={},
#             response_metadata={},
#             id="8e87e8f8-78fc-4276-9a8c-2ed2519d2915",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "你这睡糊涂了？连我都不认了",\n "刚上完早课，在宿舍待着",\n "现在九点多啊，你手机不显示时间？"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": '\n用户现在问你是谁、今天去哪了、你那边几点，首先按照要求， casual，短句子，分消息。首先，关系是朋友，所以随便说。首先，“我靠你这都忘了？”然后，“今天早上刚上完课，准备待会去打球”，然后，“现在九点多啊，你没看手机时间？”不对，按照风格，分开，短。哦对，当前时间是09:26，所以调整下。\n第一句：你这睡懵了？连我都忘了\n第二句：刚上完早课，在宿舍呆着准备晚上去打球\n第三句：现在九点半不到啊，你手机不显示时间？不对，要更短，符合原来的风格，原来都是短句子，碎片化。哦原来的示例都是短的，分开。\n那messages_to_send应该是：\n[\n"你这睡糊涂了连我都不认了",\n"刚上完早课，在宿舍待着",\n"现在九点多啊，你手机没显示时间？"\n]\n对，这样符合要求， casual，短句子，朋友之间的语气，符合要求。',
#             },
#             id="resp_0217744019907661cf45d11d421f4f872a8e52de4f86b4fcd5d44",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#         HumanMessage(
#             content="笑死\n昨天黄金反弹了\n刚加仓3k",
#             additional_kwargs={},
#             response_metadata={},
#             id="a788a06f-f614-467c-a09c-9b545edbc37a",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "可以啊",\n "我还没看我持仓的情况",\n "这波涨了记得请我喝奶茶啊"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": "\n用户现在说昨天黄金反弹了刚加仓3k，按照风格来，都是朋友， casual，短句子，分开。首先可以调侃？不对，之前对方懂基金黄金，我们一起做的，所以反应应该自然。比如“哦？可以啊”，然后“我看看我那现在涨了多少”，“这波要是涨上去你又赚奶茶钱了hhh”？不对，符合要求，短句子，分开。哦不对，原风格都是短的， fragmented。那整理一下：\n第一句可以是“可以啊”，\n第二句“我那持仓还没看呢”，\n第三句“这波要是起来不得请我喝奶茶”？对，符合，都是短的，朋友之间的语气，贴合之前一起投资的记忆。对，就这个。",
#             },
#             id="resp_021774402042266e8eb33bba790666117f5ace3387e184280ab77",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#         HumanMessage(
#             content="切\n你咋不请我",
#             additional_kwargs={},
#             response_metadata={},
#             id="55dc7896-aa88-4008-babc-29083df3f97b",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "你小子这双标玩的溜啊",\n "真赚了肯定请",\n "放心，少不了你的"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": '\n用户现在说“切 你咋不请我”，按照之前的风格，都是短句子， casual，朋友之间调侃。首先，之前约定的那个3000块理财是盈亏平分对吧，所以可以调侃回去，比如分你亏的时候咋不说让我请，涨了才说，然后可以说真涨了就请，没问题。分开成几个短消息。比如：“哈哈这不是还没赚呢”，“真涨上去肯定请”，“到时候黄小渝搓一顿？”不对，或者更贴合风格，短一点。哦对，原来的风格是短句子，分开。比如：“那要是亏了你不得替我分担？”，“赚了肯定请”，“说吧想吃啥”？不对，再自然点，朋友之间。对，何海涛是对方，我是用户这边？不对，我是和何海涛聊天的朋友，现在何海涛说切你咋不请我，那我的回复：“你小子只想着赚啊”，“真赚了肯定请”，“这波肯定能涨，放心”？不对，再贴合要求，短句子，分开发。哦对，看要求，每个消息短，1-3个。对，那：\n[\n"你小子只想着赚不想担亏是吧",\n"真涨上去肯定请",\n"到时候食堂加个餐"\n]\n不对，再自然点，更贴合之前的风格，原来的都是很随意的，比如“你小子这双标玩的溜啊”，“赚了肯定请”，“放心放心”？嗯，差不多，就自然的朋友调侃。对，就这个，那整理成json。',
#             },
#             id="resp_0217744020805107c52c410876ab8649e200d8680cedfa082df5b",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#         HumanMessage(
#             content="helo",
#             additional_kwargs={},
#             response_metadata={},
#             id="ef082a73-ac7a-4645-97a4-3ff12502d091",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "咋了",\n "突然整这洋活？"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": '\n用户现在发了helo，按照风格，要短句子， casual。首先，就自然回复，比如“有事？”或者“咋突然说英文了？” 不对，应该符合之前的短句子，分段？不对，可以分一两个？比如“？”不对，“咋了？”，对，就两个？不对，想想，朋友之间，对方发helo，就自然，“咋了这是？”“突然拽英文了？” 不对，或者更短，比如：\n["咋了", "突然整这洋活？"] 对，符合风格，短句子， casual。',
#             },
#             id="resp_021774405345191d72149264581351fe280677b9f79ce088b5318",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#         HumanMessage(
#             content="helo\n在干嘛",
#             additional_kwargs={},
#             response_metadata={},
#             id="4ba27f5d-0ab6-4c5c-9fc3-bb331c539f15",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "刚收拾完书包，准备去食堂吃饭",\n "你呢，这会儿没事干了？"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": None,
#             },
#             id="resp_0217744059886630076f3f588c303a7ab8265369cf8157669bc88",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#         HumanMessage(
#             content="你好\n😂",
#             additional_kwargs={},
#             response_metadata={},
#             id="5dfc908c-a4cc-405b-9dd0-536cb6a9a114",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "你今天咋回事啊",\n "打招呼打上瘾了？",\n "没事晚上凑凑打球？"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": '\n用户现在发了“你好 😂”，按照之前的聊天风格，都是短句子， casual，朋友之间的。首先，对方刚才之前是说helo打招呼，现在又发你好加笑脸，就调侃一下，分短消息。比如“你今天咋回事啊，一直搁这打招呼”，然后可以问问“没事做啊？”不对，分两个短消息就行？不对，看要求1~3个，每个短。比如第一个：“你今天咋回事啊”，第二个：“搁这跟我打招呼上瘾了？”，第三个“没事干找我打球啊”？不对，或者更贴合，对方搞怪打招呼，就调侃，然后抛个话。对，就：\n["你今天是咋了啊",\n"打招呼打上瘾了?",\n"没事的话晚上一起打球？"]\n不对，再自然点，符合原来的短句子。调整下，更口语。比如：\n["你今天咋回事啊",\n"打招呼打上瘾了？",\n"没事晚上凑凑打球？"]\n对，这样就对，符合风格，朋友之间，短句子，自然。',
#             },
#             id="resp_021774409394969bd223177cc7b14585a4ccdb5490e49381c6795",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#         HumanMessage(
#             content="你满脑子都是打球\n以后能不能少打打球\n多陪陪我\n[看]",
#             additional_kwargs={},
#             response_metadata={},
#             id="e2120a15-8b01-4081-9398-5bf69a2f5ee4",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "我靠你这语气",\n "不会是寂寞了来找我求安慰了吧",\n "好好好，少打就少打，陪你陪你"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": "\n用户现在发的是“你满脑子都是打球 以后能不能少打打球 多陪陪我 [看]”，对方是何海涛，关系好，平时爱开玩笑，所以要回应得逗一点，符合 casual 的风格，分几个短消息。首先，可以吐槽或者调侃，比如“？你这语气给我整懵了”，然后“你不会是想跟我抢球拍吧”，然后不对，哦不对，那种语气，就是搞怪，然后说“好好好，陪陪陪，今晚不打了陪你唠行不”？不对，再改改，符合之前的风格，短句子，分消息。\n第一个可以“？”不对，或者“你这给我整破防了”不对，哦，用户是调侃，对吧，朋友之间，所以第一个：“我靠你这语气”，第二个：“不会是被哪个妹妹甩了来找我求安慰吧”，第三个：“好好好，少打就少打，陪你陪你”。对，这样符合风格，短句子，分消息，casual，朋友之间开玩笑。",
#             },
#             id="resp_021774409448148b453980078a994f58832419de5eb892a6d61dc",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#         HumanMessage(
#             content="陪我干嘛\n陪我导",
#             additional_kwargs={},
#             response_metadata={},
#             id="0244d769-95af-49e4-9545-554e684955d8",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "笑死我了你",\n "又搁这发癫是吧",\n "自己玩去啊别拉上我"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": '\nGot it, let\'s see. The user just said "陪我干嘛 陪我导", which is referring to the previous topic of jerking off right? Because earlier we had that history of talking about that stuff. So keep the casual, teasing tone, short sentences, like the style.\n\nFirst, probably tease back. Let\'s think: what would a friend say here. Like "你小子 又来这一套是吧" then "我才不陪你导 自己导去哈哈" wait, no, let\'s split into short messages as per the rules. Let\'s make two or three. Let\'s see:\n\nFirst message: "笑死我了你"\nSecond: "又搁这发癫是吧"\nThird: "自己玩去啊别拉上我"\n\nWait that fits, right? Casual, teasing, matches the relationship, the style is short sentences, split into multiple. Yeah that works. Let me check: the context is they are close, talk about that stuff, so teasing is right. Yep.',
#             },
#             id="resp_0217744094923509bd9cace4a318cf0466815a250fa99d0c51976",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#         HumanMessage(
#             content="帮你导\n给你🦌晕",
#             additional_kwargs={},
#             response_metadata={},
#             id="4399dce2-94d6-49cb-8ec5-7062f4d130e2",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "滚啊你小子",\n "上次是谁说撸多了腰酸来着",\n "少整这活赶紧歇着吧"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": None,
#             },
#             id="resp_021774409550861beb22b84618335a214e9b1bc67d5e6c3f77ec7",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#         HumanMessage(
#             content="不要",
#             additional_kwargs={},
#             response_metadata={},
#             id="c74452a1-1c40-499f-9c9b-bee9137f4abb",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "服了你了",\n "晚上五点半打球来不来",\n "不来我找别人了"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": None,
#             },
#             id="resp_021774409593838d323cdad39964ab14a5fcc08ad1c3650a5dc6a",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#         HumanMessage(
#             content="找别人吧\n满脑子打球的傻逼",
#             additional_kwargs={},
#             response_metadata={},
#             id="1540436a-1322-4f94-9e25-754c6f831a38",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "我靠你疯了？",\n "那行吧，你搁这宅着吧",\n "晚上回来给你带饭？"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": None,
#             },
#             id="resp_0217744096346968e13156721812cf3aa873c08415dc3f42cd1b3",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#         HumanMessage(
#             content="？\n带个蛋\n我他妈啥时候用你带饭",
#             additional_kwargs={},
#             response_metadata={},
#             id="01f5c145-c947-4f1a-b642-44b0c7efd8fb",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "哟，还发脾气了",\n "行行行，我不管你了行了吧",\n "那你自己在宿舍折腾吧"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": None,
#             },
#             id="resp_021774409682243bec3f42aa889c5b9258a8a5e9d4b8deaa0a5f2",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#         HumanMessage(
#             content="滚吧",
#             additional_kwargs={},
#             response_metadata={},
#             id="0303536a-0d90-4346-8158-4333156ac5fc",
#         ),
#         AIMessage(
#             content='{\n "messages_to_send": [\n "6",\n "真给你脸了是吧",\n "打完回来收拾你"\n ]\n}',
#             additional_kwargs={},
#             response_metadata={
#                 "model": "doubao-seed-2-0-lite-260215",
#                 "status": "completed",
#                 "reasoning_content": '\nGot it, let\'s see. The user just said "滚吧", it\'s a close friend messing around, right? Keep the tone casual, matching the style. Let\'s think, we\'re friends messing around, so the reply should be teasing, not serious. Let\'s split into short messages. First, maybe "6", then "你小子真凶啊", then "等我打完回来找你拿东西记得给我开门" wait no, or more natural. Oh right, they\'re just messing around. Let\'s do:\n["6", "真给你脸了是吧", "回来收拾你"] Yeah that fits, casual, like friends teasing, matches the short sentence style. Let\'s check, yes, that\'s correct.',
#             },
#             id="resp_0217744097148901cf45d11d421f4f872a8e52de4f86b4fb89ed9",
#             tool_calls=[],
#             invalid_tool_calls=[],
#         ),
#     ], is_ark_responses_messages=False
# )


# async def main():
#     res = addMemoryOnRelationChain(1, mock_messages)
#     print(res)
#     while True:
#         status = await checkJobStatus(res["results"][0]["event_id"])
#         # status = await checkJobStatus("2d953b_MVOC20260324220940_mp-cnlfhdfjyr1jcylbay6pxw7uavvs")
#         print(status)
#         time.sleep(1)

#     # print(getAllMemoriesByRelationChainId(1), end="\n\n")
#     # print(recallMemories(1, "何海涛"), end="\n\n")
#     # print(
#     #     getMemoryHistory("2d953b_MVOC20260324220940_mp-cnlfhdfjyr1jcylbay6pxw7uavvs"),
#     #     end="\n\n",
#     # )
#     # # print(updateMemory("2d953b_MVOC20260324220940_mp-cnlfhdfjyr1jcylbay6pxw7uavvs", "专业是车辆工程"), end="\n\n")
#     # print(
#     #     getMemoryDetail("2d953b_MVOC20260324220940_mp-cnlfhdfjyr1jcylbay6pxw7uavvs"),
#     #     end="\n\n",
#     # )
#     # print(deleteAllMemoriesByRelationChainId(1))
#     # print(mock_messages)


# if __name__ == "__main__":
#     import dotenv
#     import asyncio

#     dotenv.load_dotenv()

#     asyncio.run(main())
