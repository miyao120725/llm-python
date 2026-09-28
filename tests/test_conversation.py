import json

from app.providers.llm.mock import MockLLMProvider
from app.providers.llm.openai_compat import resolve_search_strategy
from app.schemas.llm import ChatRequest, coerce_search


def test_qwen38_search_strategy_falls_back_to_max():
    assert resolve_search_strategy("qwen3.8-max", "agent_max") == "max"
    assert resolve_search_strategy("qwen3.8-max", "agent") == "max"
    assert resolve_search_strategy("qwen3.8-max", "max") == "max"
    assert resolve_search_strategy("qwen3.8-max", "off") is None
    assert resolve_search_strategy("qwen3-max", "agent_max") == "agent_max"


def test_search_true_from_client_enables_deep_search():
    assert coerce_search(True) == "agent_max"
    assert coerce_search("true") == "agent_max"
    assert coerce_search("max") == "max"
    assert coerce_search("深度搜索") == "agent_max"
    payload = ChatRequest(messages=[{"role": "user", "content": "hi"}], search=True)
    assert payload.search == "agent_max"
    aliased = ChatRequest.model_validate(
        {"messages": [{"role": "user", "content": "hi"}], "deepSearch": True}
    )
    assert aliased.search == "agent_max"


def test_stateless_chat_still_works(client):
    response = client.post(
        "/v1/llm/chat",
        json={"messages": [{"role": "user", "content": "你好"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mocked"] is True
    assert body["conversation_id"] is None
    assert "你好" in body["content"]


def test_conversation_memory_two_turns(client):
    created = client.post("/v1/llm/conversations")
    assert created.status_code == 200
    conversation_id = created.json()["conversation_id"]

    first = client.post(
        "/v1/llm/chat",
        json={
            "conversation_id": conversation_id,
            "messages": [{"role": "user", "content": "我叫小明"}],
        },
    )
    assert first.status_code == 200
    assert first.json()["conversation_id"] == conversation_id

    second = client.post(
        "/v1/llm/chat",
        json={
            "conversation_id": conversation_id,
            "messages": [{"role": "user", "content": "我叫什么"}],
        },
    )
    assert second.status_code == 200
    llm = client.app.state.container.providers.llm
    assert isinstance(llm, MockLLMProvider)
    contents = [item.content for item in llm.last_messages]
    assert "我叫小明" in contents
    assert "我叫什么" in contents

    history = client.get(f"/v1/llm/conversations/{conversation_id}")
    assert history.status_code == 200
    roles = [item["role"] for item in history.json()["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_conversation_not_found(client):
    response = client.get("/v1/llm/conversations/missing")
    assert response.status_code == 404
    assert response.json()["code"] == "conversation_not_found"


def test_invalid_conversation_turn(client):
    conversation_id = client.post("/v1/llm/conversations").json()["conversation_id"]
    response = client.post(
        "/v1/llm/chat",
        json={
            "conversation_id": conversation_id,
            "messages": [
                {"role": "user", "content": "a"},
                {"role": "user", "content": "b"},
            ],
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_conversation_turn"


def test_chat_stream_sse(client):
    response = client.post(
        "/v1/llm/chat",
        json={"messages": [{"role": "user", "content": "流式"}], "stream": True},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    pieces: list[str] = []
    done = False
    types: list[str] = []
    for line in response.text.splitlines():
        if not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            done = True
            continue
        event = json.loads(data)
        types.append(event.get("type", ""))
        if event.get("type") == "delta":
            pieces.append(event["content"])
    assert done
    assert "reasoning" not in types
    assert "流式" in "".join(pieces)


def test_thinking_stream_not_persisted_in_history(client):
    conversation_id = client.post("/v1/llm/conversations").json()["conversation_id"]
    response = client.post(
        "/v1/llm/chat",
        json={
            "conversation_id": conversation_id,
            "stream": True,
            "thinking": True,
            "messages": [{"role": "user", "content": "思考题"}],
        },
    )
    assert response.status_code == 200
    reasoning: list[str] = []
    deltas: list[str] = []
    for line in response.text.splitlines():
        if not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            continue
        event = json.loads(data)
        if event.get("type") == "reasoning":
            reasoning.append(event["content"])
        if event.get("type") == "delta":
            deltas.append(event["content"])
    assert "先分析问题" in "".join(reasoning)
    assert "思考题" in "".join(deltas)

    history = client.get(f"/v1/llm/conversations/{conversation_id}").json()["messages"]
    assert [item["role"] for item in history] == ["user", "assistant"]
    assert "先分析问题" not in history[1]["content"]
    assert "思考题" in history[1]["content"]


def test_thinking_and_search_reach_provider(client):
    response = client.post(
        "/v1/llm/chat",
        json={
            "messages": [{"role": "user", "content": "调研"}],
            "thinking": True,
            "search": "agent_max",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["thinking"] is True
    assert body["search"] == "agent_max"
    assert body["reasoning"]
    assert "[mock-search:agent_max]" in body["content"]
    llm = client.app.state.container.providers.llm
    assert isinstance(llm, MockLLMProvider)
    assert llm.last_thinking is True
    assert llm.last_search == "agent_max"


def test_recent_conversations_order_and_empty_filtered(client):
    empty_id = client.post("/v1/llm/conversations").json()["conversation_id"]
    first_id = client.post("/v1/llm/conversations").json()["conversation_id"]
    second_id = client.post("/v1/llm/conversations").json()["conversation_id"]

    client.post(
        "/v1/llm/chat",
        json={"conversation_id": first_id, "messages": [{"role": "user", "content": "我叫小明"}]},
    )
    client.post(
        "/v1/llm/chat",
        json={"conversation_id": second_id, "messages": [{"role": "user", "content": "今天天气"}]},
    )

    listed = client.get("/v1/llm/conversations")
    assert listed.status_code == 200
    items = listed.json()["items"]
    ids = [item["conversation_id"] for item in items]
    assert empty_id not in ids
    assert ids[:2] == [second_id, first_id]
    assert items[0]["title"] == "今天天气"
    assert items[1]["title"] == "我叫小明"
    assert items[0]["last_role"] == "assistant"
    assert items[0]["message_count"] == 2


def test_recent_conversation_can_continue(client):
    conversation_id = client.post("/v1/llm/conversations").json()["conversation_id"]
    client.post(
        "/v1/llm/chat",
        json={"conversation_id": conversation_id, "messages": [{"role": "user", "content": "我叫小明"}]},
    )

    listed = client.get("/v1/llm/conversations").json()["items"]
    assert listed[0]["conversation_id"] == conversation_id

    client.post(
        "/v1/llm/chat",
        json={
            "conversation_id": listed[0]["conversation_id"],
            "messages": [{"role": "user", "content": "我叫什么"}],
        },
    )
    llm = client.app.state.container.providers.llm
    assert isinstance(llm, MockLLMProvider)
    contents = [item.content for item in llm.last_messages]
    assert "我叫小明" in contents
    assert "我叫什么" in contents


def test_chat_stream_persists_assistant(client):
    conversation_id = client.post("/v1/llm/conversations").json()["conversation_id"]
    response = client.post(
        "/v1/llm/chat",
        json={
            "conversation_id": conversation_id,
            "stream": True,
            "messages": [{"role": "user", "content": "流式记忆"}],
        },
    )
    assert response.status_code == 200
    assert "流式记忆" in response.text

    history = client.get(f"/v1/llm/conversations/{conversation_id}")
    assert history.status_code == 200
    messages = history.json()["messages"]
    assert [item["role"] for item in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "流式记忆"
    assert "流式记忆" in messages[1]["content"]
