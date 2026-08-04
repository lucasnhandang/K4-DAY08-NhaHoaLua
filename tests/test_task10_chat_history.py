from unittest.mock import MagicMock, patch

from src.task10_generation import MAX_HISTORY_TURNS, generate_with_citation


def test_generate_includes_only_recent_valid_chat_history(monkeypatch):
    chunks = [{
        "content": "Shopee hỗ trợ thanh toán bằng thẻ.",
        "score": 0.9,
        "metadata": {"source": "payment.md", "type": "legal"},
        "source": "hybrid",
    }]
    history = []
    for index in range(5):
        history.extend([
            {"role": "user", "content": f"Câu hỏi {index}"},
            {"role": "assistant", "content": f"Câu trả lời {index}"},
        ])
    history.append({"role": "tool", "content": "không được gửi"})

    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content="Câu trả lời [payment.md]"))]
    client = MagicMock()
    client.chat.completions.create.return_value = completion
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    with patch("src.task10_generation.retrieve", return_value=chunks), patch(
        "openai.OpenAI", return_value=client
    ):
        result = generate_with_citation(
            "Trong số đó phương thức nào được hỗ trợ?",
            top_k=1,
            chat_history=history,
        )

    messages = client.chat.completions.create.call_args.kwargs["messages"]
    sent_history = messages[1:-1]

    assert len(sent_history) == MAX_HISTORY_TURNS * 2
    assert sent_history[0] == {"role": "user", "content": "Câu hỏi 2"}
    assert all(message["role"] in {"user", "assistant"} for message in sent_history)
    assert messages[-1]["role"] == "user"
    assert "Trong số đó phương thức nào được hỗ trợ?" in messages[-1]["content"]
    assert result["answer"] == "Câu trả lời [payment.md]"
