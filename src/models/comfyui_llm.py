"""ComfyUI native LLM adapter.

Routes LumenX text-generation calls (script analysis, prompt polishing) to a
local ComfyUI LLM workflow (e.g. ``qwen3_llm.json`` using the core
``TextGenerate`` node).  Enabled via ``LLM_PROVIDER=comfyui``.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from ..utils import get_logger
from .comfyui_client import ComfyUIClient, load_workflow_mapping

logger = get_logger(__name__)


class ComfyUILanguageModel:
    """Submit a text prompt to a ComfyUI LLM workflow and return the reply."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.comfyui_client = ComfyUIClient(
            base_url=self.config.get("base_url"),
            protocol=self.config.get("protocol"),
        )
        self.workflow_mapping = self.config.get("workflow_mapping") or load_workflow_mapping()
        self.workflow_id = (
            self.config.get("workflow_id")
            or os.getenv("COMFYUI_LLM_WORKFLOW")
            or self.workflow_mapping.get("llm_generation", {}).get("text_gen")
            or "qwen3_llm"
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate text from OpenAI-style messages via the ComfyUI workflow."""
        workflow = self.comfyui_client.load_workflow_template(self.workflow_id)
        if not workflow:
            raise RuntimeError(
                f"ComfyUI LLM workflow template not found: {self.workflow_id} "
                "(expected under config/comfyui_workflows/)"
            )

        prompt_text = self._messages_to_prompt(messages)
        if response_format and response_format.get("type") == "json_object":
            prompt_text = (
                f"{prompt_text}\n\nRespond with valid JSON only, no markdown fences."
            )

        workflow = self._prepare_workflow(workflow, prompt_text)
        task_id = self.comfyui_client.submit_workflow_task(
            workflow_id=self.workflow_id,
            workflow=workflow,
        )
        if not task_id:
            raise RuntimeError("Failed to submit LLM generation task to ComfyUI")

        result = self.comfyui_client.wait_for_task_completion(
            task_id=task_id,
            timeout=int(self.config.get("timeout", 600)),
        )
        if not result or result.get("status") != "completed":
            raise RuntimeError(
                "ComfyUI LLM generation failed: %s"
                % (result.get("error") if result else "task failed or timed out")
            )

        reply = self._extract_text(result)
        if not reply:
            raise RuntimeError("ComfyUI LLM returned no text output")
        logger.info("ComfyUI LLM replied (%d chars)", len(reply))
        return reply

    @staticmethod
    def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
        parts: List[str] = []
        for message in messages or []:
            role = (message.get("role") or "user").capitalize()
            content = message.get("content") or ""
            parts.append(f"{role}: {content}")
        return "\n\n".join(parts).strip()

    @staticmethod
    def _prepare_workflow(
        workflow: Dict[str, Any],
        prompt_text: str,
    ) -> Dict[str, Any]:
        """Set the prompt on the LLM node and drop image-only nodes."""
        prompt = json.loads(json.dumps(workflow))
        llm_node_ids = [
            node_id
            for node_id, node in prompt.items()
            if isinstance(node, dict) and "TextGenerate" in str(node.get("class_type", ""))
        ]
        if not llm_node_ids:
            raise RuntimeError("ComfyUI LLM workflow has no TextGenerate node")
        llm_node = prompt[llm_node_ids[0]]
        llm_node.setdefault("inputs", {})["prompt"] = prompt_text
        # Text-only: never send an image reference.
        llm_node["inputs"].pop("image", None)

        # Drop image-loading nodes that are no longer referenced.
        referenced = {
            value[0]
            for node in prompt.values()
            for value in (node.get("inputs") or {}).values()
            if isinstance(value, list) and len(value) == 2
        }
        for node_id in list(prompt.keys()):
            node = prompt[node_id]
            if node.get("class_type") == "LoadImage" and node_id not in referenced:
                del prompt[node_id]
        return prompt

    @staticmethod
    def _extract_text(result: Dict[str, Any]) -> str:
        chunks: List[str] = []
        for item in result.get("results", result.get("files", [])):
            if not isinstance(item, dict):
                continue
            if item.get("type") != "text":
                continue
            raw = item.get("raw") or {}
            text = raw.get("text") or ""
            if text:
                chunks.append(str(text))
        return "\n".join(chunks).strip()
