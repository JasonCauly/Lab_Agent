import re
from typing import Any
from urllib.parse import urlparse
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.config import settings
from app.models.user import User
from app.schemas.ai import ChatRequest
from data.config_global.agent_config import build_tools, SYSTEM_PROMPT, TOOL_LABELS


def _build_history(data: ChatRequest) -> list:
    """将前端的消息转成 LangChain 的消息对象"""
    history = []
    for message in data.messages:
        if message.role == "user" and message.content.strip():
            history.append(HumanMessage(content=message.content.strip()))
        elif message.role == "assistant" and message.content.strip():
            history.append(AIMessage(content=message.content.strip()))
    if not history:
        raise BusinessException(message="请输入您的对话内容")
    return history


def _tool_output_preview(output: Any, limit: int = 200):
    """把工具输出的结果收成短文本预览, 避免整段的JSON污染了输出的区域"""
    if isinstance(output, ToolMessage):
        output = output.content

    text = (
        output if isinstance(output, str) else str(output)
    )  # output 有可能是 dict -> str

    return text if len(text) <= limit else text[:limit] + "..."


def _chunk_text(chunk: Any):
    """
    从模型的流式输出里面 拿到纯文本
    chunk.content 可能是 str [{type, text}, ....] 等类型 这个需要统一处理成字符串
    """
    if chunk is None:
        return ""

    # chunk 如果是 AiMessage 类型的 则可以取出 content
    content = getattr(chunk, "content", None)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get("text") or "")
        return "".join(parts)

    return str(content) if content is not None else ""


def build_agent(db: Session, current_user: User):
    tools = build_tools(db=db, current_user=current_user)
    model = ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        temperature=0,
        # 当前对话只保存正文；DeepSeek 的思考模式要求额外回传 reasoning_content。
        extra_body=(
            {"thinking": {"type": "disabled"}}
            if urlparse(settings.LLM_BASE_URL).hostname == "api.deepseek.com"
            else None
        ),
        streaming=True,  # 使用流式输出, stream_event 用于接收逐字返回的token
    ).bind_tools(tools)

    async def agent_node(state: MessagesState):
        """LangGragh 执行的工作流的节点"""
        # response = model.invoke(state["messages"])
        response = await model.ainvoke(state["messages"])
        # response = await model.astream(state["messages"])
        return {"messages": [response]}

    gragh = StateGraph(MessagesState)
    gragh.add_node("agent", agent_node)  # 调用大模型的节点
    gragh.add_node("tools", ToolNode(tools))  # tool call的节点
    gragh.add_edge(START, "agent")  # 流程的起点, call LLM
    gragh.add_conditional_edges(
        "agent", tools_condition
    )  # 判断是否有 tool_call, 有就继续call, 没有就END 输出
    gragh.add_edge("tools", "agent")  # agent查看tool调用的结果
    return gragh.compile()


# def run_agent(db: Session, current_user: User, data: ChatRequest):
#     """大模型对话"""
#     try:
#         if not data.messages:
#             raise BusinessException(message="对话内容为空")

#         history = _build_history(data)

#         agent = build_agent(db, current_user)
#         try:
#             result = agent.invoke(
#                 {"messages": [SystemMessage(content=SYSTEM_PROMPT), *history]},
#                 # Tools share this request's SQLAlchemy session; execute them sequentially.
#                 config={"recursion_limit": 10, "max_concurrency": 1},
#             )  # 设置对话循环的上限是10轮
#         except BusinessException:
#             raise
#         except Exception:
#             raise BusinessException(message="大模型调用失败，请稍后重试")

#         messages = result.get("messages") or []
#         if not messages:
#             raise BusinessException(message="大模型没有任何返回内容")

#         message = messages[-1]
#         if not isinstance(message, AIMessage) or message.tool_calls:
#             raise BusinessException(message="大模型没有返回有效的回复内容")

#         if message.invalid_tool_calls:
#             raise BusinessException(message="助手未能正确调用工具，请重试", code=502)

#         content = message.content

#         # 处理字符串类型的回复
#         if isinstance(content, str):
#             content = content.strip()

#         # 处理列表类型的回复
#         elif isinstance(content, list):
#             content = "".join(
#                 (
#                     part
#                     if isinstance(part, str)
#                     else part.get("text", "") if isinstance(part, dict) else ""
#                 )
#                 for part in content
#             ).strip()

#         else:
#             content = ""

#         if re.search(r"<\s*/?\s*(?:tool_call|function)\b", content, re.IGNORECASE):
#             raise BusinessException(message="助手未能正确调用工具，请重试", code=502)

#         if content:
#             return content

#         raise BusinessException(message="大模型没有返回有效的回复内容")

#     except BusinessException as e:
#         yield {"type": "error", "message": e.message}
#     except Exception:
#         yield {"type": "error", "message": "大模型调用失败，请稍后重试"}


async def stream_agent(db: Session, current_user: User, data: ChatRequest):
    """
    生成器：边跑 agent 边 yield 事件，提供 SSE 输出给前端
    事件的类型: status | tool_start | tool_end | token | done | error
    """
    try:
        if not data.messages:
            raise BusinessException(message="对话内容为空")

        history = _build_history(data)

        agent = build_agent(db, current_user)
        inputs = {"messages": [SystemMessage(content=SYSTEM_PROMPT), *history]}

        yield {"type": "status", "message": "正在思考..."}

        async for event in agent.astream_events(
            inputs, version="v2", config={"recursion_limit": 10}
        ):
            kind = event.get("event")
            if kind == "on_tool_start":
                name = event.get("name") or ""  # tool的名称
                yield {
                    "type": "tool_start",
                    "name": name,
                    "label": TOOL_LABELS.get(name, name),
                }
            elif kind == "on_tool_end":
                name = event.get("name") or ""  # tool的名称
                yield {
                    "type": "tool_end",
                    "name": name,
                    "label": TOOL_LABELS.get(name, name),
                    "preview": _tool_output_preview(
                        (event.get("data") or {}).get("output")
                    ),
                }
            elif kind == "on_chat_model_stream":
                metadata = event.get("metadata") or {}
                if metadata.get("langgraph_node") not in (None, "agent"):
                    continue
                text = _chunk_text((event.get("data") or {}).get("chunk"))
                yield {"type": "token", "content": text}
        yield {"type": "done"}

    except BusinessException as e:
        yield {"type": "error", "message": e.message}
    except Exception:
        yield {"type": "error", "message": "大模型调用失败，请稍后重试"}
