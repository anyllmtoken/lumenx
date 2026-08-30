#!/usr/bin/env python3
"""Convert a ComfyUI UI-format workflow JSON to API format.

The API format is what LumenX submits via ``POST /prompt`` (standard/native
ComfyUI protocol).  The conversion replicates the ComfyUI frontend's
``graphToPrompt`` logic, using the node schemas from ``/object_info`` to map
``widgets_values`` back to input names.

Usage:
    python scripts/comfyui_convert_template.py \\
        --template path/to/workflow.json \\
        --output config/comfyui_workflows/workflow.json

``--object-info`` accepts a saved ``/object_info`` dump; when omitted the
script tries ``http://localhost:8188/object_info``.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


WIDGET_PRIMITIVES = {
    "STRING",
    "INT",
    "FLOAT",
    "BOOLEAN",
    "COMBO",
    "COMFY_DYNAMICCOMBO_V3",
}

SKIP_TYPES = {
    "Note",
    "MarkdownNote",
    "PrimitiveNode",
    "PrimitiveFloat",
    "PrimitiveInt",
    "PrimitiveBoolean",
    "PrimitiveString",
    "PrimitiveStringMultiline",
    "Primitive",
    "Reroute",
}


def load_object_info(path: Optional[str] = None) -> Dict[str, Any]:
    if path and Path(path).is_file():
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    with urllib.request.urlopen("http://localhost:8188/object_info", timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_widget_input(defn: Any) -> bool:
    typ = defn[0]
    if isinstance(typ, list):
        return True
    return isinstance(typ, str) and typ in WIDGET_PRIMITIVES


def unwrap(value: Any) -> Any:
    """Undo the ``{__value__: ...}`` wrappers used for array widget values."""
    if isinstance(value, dict) and "__value__" in value:
        return value["__value__"]
    return value


def convert(
    workflow: Dict[str, Any],
    object_info: Dict[str, Any],
) -> Dict[str, Any]:
    nodes = workflow.get("nodes", [])
    raw_links = workflow.get("links", [])
    nodes_by_id = {str(n.get("id")): n for n in nodes if isinstance(n, dict)}
    links_by_id = {str(l[0]): l for l in raw_links}

    output: Dict[str, Any] = {}
    warnings: List[str] = []

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id"))
        node_type = node.get("type", "")
        mode = node.get("mode", 0)
        if mode in (2, 4):  # NEVER / BYPASS
            continue
        if node_type in SKIP_TYPES:
            continue

        node_info = object_info.get(node_type)
        if not node_info:
            warnings.append(f"node {node_id} type {node_type!r} not in object_info; skipping")
            continue

        inputs: Dict[str, Any] = {}

        # 1) Connectable inputs (with links). Widget inputs connected to a
        #    primitive resolve to the primitive's value.
        for slot in node.get("inputs") or []:
            link_id = slot.get("link")
            if link_id is None:
                continue
            link = links_by_id.get(str(link_id))
            if not link:
                continue
            src_id = str(link[1])
            src_slot = int(link[2])
            src_node = nodes_by_id.get(src_id)
            if src_node and str(src_node.get("type", "")).startswith("Primitive"):
                values = src_node.get("widgets_values") or []
                if src_slot < len(values):
                    inputs[slot["name"]] = unwrap(values[src_slot])
            else:
                inputs[slot["name"]] = [src_id, src_slot]

        # 2) Widget values, mapped to names via the node schema. Values are
        #    consumed in order even when the widget is already set through a
        #    connection (ComfyUI keeps the value in widgets_values).
        schema = node_info.get("input", {})
        schema_defs: Dict[str, Any] = {}
        for section in ("required", "optional"):
            for name, defn in (schema.get(section) or {}).items():
                schema_defs[name] = defn
        widget_names = [name for name, defn in schema_defs.items() if is_widget_input(defn)]

        widget_values = node.get("widgets_values") or []
        idx = 0
        for name in widget_names:
            if idx >= len(widget_values):
                break
            value = widget_values[idx]
            idx += 1
            if name not in inputs:
                inputs[name] = unwrap(value)
            defn = schema_defs[name]
            opts = defn[1] if len(defn) > 1 and isinstance(defn[1], dict) else {}
            if opts.get("control_after_generate") and idx < len(widget_values):
                inputs["control_after_generate"] = widget_values[idx]
                idx += 1

        output[node_id] = {
            "class_type": node_type,
            "inputs": inputs,
        }

    # Drop inputs pointing at removed/skipped nodes.
    for entry in output.values():
        for key, value in list(entry["inputs"].items()):
            if isinstance(value, list) and len(value) == 2 and str(value[0]) not in output:
                del entry["inputs"][key]

    if warnings:
        print("[warnings]", file=sys.stderr)
        for w in warnings:
            print("  -", w, file=sys.stderr)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, help="UI-format workflow JSON")
    parser.add_argument("--output", required=True, help="API-format output path")
    parser.add_argument("--object-info", default=None, help="saved /object_info dump")
    args = parser.parse_args()

    with open(args.template, "r", encoding="utf-8") as fh:
        workflow = json.load(fh)
    if "prompt" in workflow and isinstance(workflow["prompt"], dict):
        workflow = workflow["prompt"]  # already API-ish; pass through

    object_info = load_object_info(args.object_info)
    result = convert(workflow, object_info)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print(f"converted {len(result)} nodes -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
