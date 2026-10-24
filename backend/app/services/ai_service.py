import json
from openai import OpenAI
from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.config import settings
from app.schemas.ai import ChatMessage, ChatRequest
from app.services import equipment_service, kb_service, lab_service
from data.tools.ai_config import SYSTEM_PROMPT, TOOLS


def run_tool(db: Session, name: str, arguments: str) -> str:
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return json.dumps({"error": "参数不是合法的json"}, ensure_ascii=False)

    if not isinstance(args, dict):
        return json.dumps({"error": "参数必须是JSON对象"}, ensure_ascii=False)

    try:
        if name == "list_open_labs":
            keywords = (args.get("keywords") or "").strip() or None
            page = lab_service.get_lab_page_list(
                db, page=1, page_size=10, keywords=keywords, status=1
            )
            rows = [
                {
                    "id": item.id,
                    "name": item.name,
                    "location": item.location,
                    "capacity": item.capacity,
                    "open_time": item.open_time,
                    "close_time": item.close_time,
                }
                for item in page.list
            ]
            return json.dumps({"total": page.total, "labs": rows}, ensure_ascii=False)

        if name == "list_lab_equipments":
            lab_id = args.get("lab_id")
            if not lab_id:
                return json.dumps(
                    {"error": "参数缺少实验室的 lab_id"}, ensure_ascii=False
                )
            keywords = (args.get("keywords") or "").strip() or None
            page = equipment_service.get_equipment_page_list(
                db, page=1, page_size=10, keywords=keywords, lab_id=int(lab_id)
            )
            rows = [
                {
                    "id": item.id,
                    "lab_id": item.lab_id,
                    "lab_name": item.lab_name,
                    "name": item.name,
                    "spec": item.spec,
                    "quantity": item.quantity,
                    "status": item.status,
                }
                for item in page.list
            ]
            return json.dumps(
                {"total": page.total, "equipments": rows}, ensure_ascii=False
            )

        return json.dumps({"error": f"未找到对应的tool: {name}"}, ensure_ascii=False)

    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def get_client() -> OpenAI:
    """创建OPENAI的客户端"""
    if not settings.LLM_API_KEY:
        raise BusinessException(message="未获取到大模型的APIKey")
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)


def chat(db: Session, data: ChatRequest):
    """大模型对话"""
    if not data.messages:
        raise BusinessException(message="对话内容为空")
    history = []
    for message in data.messages:
        if message.role in ("user", "assistant") and message.content.strip():
            history.append(message.model_dump())
    if not history:
        raise BusinessException(message="请输入您要对话的内容")

    # 取出用户最新的一条提问内容
    question = next(
        (item["content"] for item in reversed(history) if item["role"] == "user"), ""
    )

    system_prompt = SYSTEM_PROMPT
    knowledge = kb_service.search(query=question) if question else ""
    if knowledge:
        system_prompt += "\n\n以下是检索到的实验室的资料: \n" + knowledge

    client = get_client()
    messages = [{"role": "system", "content": system_prompt}, *history]

    try:
        for _ in range(3):
            res = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            msg = res.choices[0].message
            tool_calls = msg.tool_calls or []
            if not tool_calls:  # 若没有tool调用, 则直接返回大模型的输出结果内容
                content = msg.content
                if not content or not content.strip():
                    raise BusinessException(message="大模型没有返回内容")
                return content
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in tool_calls
                    ],
                }
            )
            for call in tool_calls:
                result = run_tool(db, call.function.name, call.function.arguments)
                messages.append(
                    {"role": "tool", "content": result, "tool_call_id": call.id}
                )

        raise BusinessException(message="工具调用次数已达上限，请缩小查询范围后重试")
    except Exception as exc:
        raise BusinessException(message="大模型调用失败, 请稍后重试") from exc
