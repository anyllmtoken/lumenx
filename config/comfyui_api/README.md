# config/comfyui_api

本目录存放**已从 ComfyUI 导出（Save API Format）的 API 格式工作流**，是运行时实际提交给
ComfyUI `/prompt` 的文件（`comfyui_client.py` 优先从本目录加载，其次才是
`config/comfyui_workflows/` 里的原始 UI 格式模板）。

| 文件 | 用途 | 所需模型（ComfyUI/models/ 下） |
|---|---|---|
| `image_flux2_klein_text_to_image.json` | 文生图 T2I（角色/场景/道具/分镜） | `flux-2-klein-4b`、`flux-2-klein-base-4b`、`qwen_3_4b`（text_encoders）、`flux2-vae` |
| `image_flux2_klein_image_edit_4b_distilled.json` | 图生图 I2I | `flux-2-klein-4b-fp8`、`qwen_3_4b`、`flux2-vae` |
| `video_minimax_h3_i2v.json` | 图生视频 I2V（FL2VA） | `minimax_h3_fl2va_pruned_int8_convrot`、`qwen3vl_32b_minimax_h3_nvfp4_awq`、H3 双 VAE |
| `video_minimax_h3_r2v.json` | 参考图生视频 R2V（Ref2VA） | `minimax_h3_ref2va_pruned_int8_convrot`、`qwen3vl_32b_minimax_h3_nvfp4_awq`、H3 双 VAE、`minimax_h3_ref2v_turbo_4step` LoRA |
| `video_minimax_h3_t2v.json` | 文生视频 T2V（复用 FL2VA） | 同 I2V |
| `llm_qwen3vl_text_gen.json` | LLM 剧本分析/提示词润色 | `qwen3vl_4b_fp8_scaled`（text_encoders） |

> 注意：这些文件由用户在 ComfyUI 中手动导出（Workflow → Save API Format）后放入本目录。
> 若重新导出覆盖，请同步检查 `config/workflow_mapping.json` 里 `templates.*.node_mapping`
> 的节点号（子图模板导出后节点号形如 `75:73`、`105:104`）。
