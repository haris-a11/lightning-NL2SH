"""Run with `python tests/test_nl2sh.py` (or pytest). No network, no fixtures."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lightning_nl2sh import core  # noqa: E402

ENV_VARS = ("NL2SH_API_KEY", "NL2SH_BASE_URL", "NL2SH_MODEL", "NL2SH_SHELL")


class FakeResponse:
    def __init__(self, status=200, content="ls -la", body=""):
        self.status_code = status
        self.ok = 200 <= status < 300
        self.text = body
        self._content = content

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def call(env, response=None):
    """Run generate_command with a stubbed transport; return (url, payload, result)."""
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"], captured["payload"] = url, json
        return response or FakeResponse()

    saved = {k: os.environ.pop(k, None) for k in ENV_VARS}
    real_post = core.requests.post
    core.requests.post = fake_post
    try:
        os.environ.update({k: v for k, v in env.items() if v is not None})
        result = core.generate_command("list files", shell="bash")
    finally:
        core.requests.post = real_post
        for k in ENV_VARS:
            os.environ.pop(k, None)
            if saved[k] is not None:
                os.environ[k] = saved[k]
    return captured["url"], captured["payload"], result


def test_default_is_openrouter():
    url, payload, result = call({"NL2SH_API_KEY": "k"})
    assert url == "https://openrouter.ai/api/v1/chat/completions", url
    assert payload["reasoning"] == {"effort": "none"}, payload
    assert result == "ls -la", result


def test_other_provider_drops_openrouter_field():
    url, payload, _ = call(
        {
            "NL2SH_API_KEY": "k",
            "NL2SH_BASE_URL": "https://api.openai.com/v1/",  # trailing slash
            "NL2SH_MODEL": "gpt-4o-mini",
        }
    )
    assert url == "https://api.openai.com/v1/chat/completions", url
    assert "reasoning" not in payload, payload


def test_no_think_only_for_qwen():
    _, qwen, _ = call({"NL2SH_API_KEY": "k", "NL2SH_MODEL": "qwen/qwen3-14b"})
    _, other, _ = call({"NL2SH_API_KEY": "k", "NL2SH_MODEL": "gpt-4o-mini"})
    assert qwen["messages"][1]["content"].startswith("/no_think\n")
    assert other["messages"][1]["content"] == "list files", other


def test_missing_key_raises():
    try:
        call({})
    except RuntimeError as exc:
        assert "NL2SH_API_KEY" in str(exc), exc
    else:
        raise AssertionError("expected RuntimeError")


def test_http_error_includes_body():
    bad = FakeResponse(status=400, body="model 'nope' not found")
    try:
        call({"NL2SH_API_KEY": "k"}, response=bad)
    except RuntimeError as exc:
        assert "not found" in str(exc) and "400" in str(exc), exc
    else:
        raise AssertionError("expected RuntimeError")


def test_null_content_is_not_a_crash():
    _, _, result = call({"NL2SH_API_KEY": "k"}, response=FakeResponse(content=None))
    assert result == "", repr(result)


def test_fences_stripped():
    fenced = FakeResponse(content="```bash\nls -la\n```")
    _, _, result = call({"NL2SH_API_KEY": "k"}, response=fenced)
    assert result == "ls -la", repr(result)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok  " + name)
    print("all passed")
