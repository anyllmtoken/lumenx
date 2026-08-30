import os

import pytest

from src.apps.comic_gen.llm_adapter import LLMAdapter
from src.models.comfyui_llm import ComfyUILanguageModel


class FakeComfyUI:
    def __init__(self, base_url=None, protocol=None):
        self.protocol = protocol or "standard"
        self.base_url = base_url or "http://comfyui.test"
        self.submitted = []

    def load_workflow_template(self, workflow_id):
        return {
            "1": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3.5_4b_bf16.safetensors"}},
            "2": {"class_type": "LoadImage", "inputs": {"image": "sample.png"}},
            "3": {
                "class_type": "TextGenerate",
                "inputs": {
                    "clip": ["1", 0],
                    "image": ["2", 0],
                    "prompt": "old",
                    "max_length": 2048,
                    "sampling_mode": "on",
                },
            },
        }

    def submit_workflow_task(self, workflow_id=None, parameters=None, upload_files=None, workflow=None):
        self.submitted.append({"workflow_id": workflow_id, "workflow": workflow})
        return "llm-task-1"

    def wait_for_task_completion(self, task_id, timeout=600, poll_interval=5):
        return {
            "status": "completed",
            "results": [{"type": "text", "raw": {"text": '{"ok": true}'}}],
        }


@pytest.fixture
def fake_client(monkeypatch):
    fake = FakeComfyUI()
    monkeypatch.setattr("src.models.comfyui_llm.ComfyUIClient", lambda **kw: fake)
    return fake


class TestComfyUILanguageModel:
    def test_chat_sets_prompt_and_returns_text(self, fake_client):
        model = ComfyUILanguageModel({})
        reply = model.chat(
            [
                {"role": "system", "content": "You are a script analyst."},
                {"role": "user", "content": "Analyze this script."},
            ]
        )

        assert reply == '{"ok": true}'
        workflow = fake_client.submitted[0]["workflow"]
        assert workflow["3"]["inputs"]["prompt"] == (
            "System: You are a script analyst.\n\nUser: Analyze this script."
        )
        # image-only node dropped and image input removed for text-only mode
        assert "2" not in workflow
        assert "image" not in workflow["3"]["inputs"]
        assert workflow["1"]["class_type"] == "CLIPLoader"

    def test_chat_json_object_appends_instruction(self, fake_client):
        model = ComfyUILanguageModel({})
        model.chat([{"role": "user", "content": "hi"}], response_format={"type": "json_object"})
        prompt = fake_client.submitted[0]["workflow"]["3"]["inputs"]["prompt"]
        assert "valid JSON only" in prompt


class TestLLMAdapterComfyUI:
    def test_provider_comfyui_delegates_to_comfyui_model(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "comfyui")
        calls = {}

        class FakeLLM:
            def __init__(self, **kwargs):
                pass

            def chat(self, **kwargs):
                calls.update(kwargs)
                return "comfyui-reply"

        monkeypatch.setattr("src.models.comfyui_llm.ComfyUILanguageModel", FakeLLM)
        adapter = LLMAdapter()

        reply = adapter.chat([{"role": "user", "content": "hello"}], model=None)

        assert reply == "comfyui-reply"
        assert calls["messages"] == [{"role": "user", "content": "hello"}]
        assert adapter.is_configured is True
