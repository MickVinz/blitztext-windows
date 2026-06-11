from unittest.mock import MagicMock, patch


def _mock_client(text):
    c = MagicMock()
    c.messages.create.return_value.content = [MagicMock(text=text)]
    return c


def test_improve_strips_whitespace():
    with patch("services.llm.anthropic.Anthropic", return_value=_mock_client("  Result.  ")):
        import importlib, services.llm as m; importlib.reload(m)
        assert m.LLMService("sk-x").improve_text("raw") == "Result."


def test_uses_haiku_model():
    mock_c = _mock_client("OK")
    with patch("services.llm.anthropic.Anthropic", return_value=mock_c):
        import importlib, services.llm as m; importlib.reload(m)
        m.LLMService("sk-x").improve_text("test")
    kw = mock_c.messages.create.call_args.kwargs
    assert kw["model"] == "claude-haiku-4-5"
    assert kw["max_tokens"] == 1024


def test_raw_text_in_prompt():
    mock_c = _mock_client("OK")
    with patch("services.llm.anthropic.Anthropic", return_value=mock_c):
        import importlib, services.llm as m; importlib.reload(m)
        m.LLMService("sk-x").improve_text("mein rohtext")
    content = mock_c.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "mein rohtext" in content
