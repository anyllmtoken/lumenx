# config/comfyui_workflows

本目录存放 LumenX 提交给 ComfyUI 的工作流（standard/原生协议，API 格式）。

## 两类文件

- **API 格式（已就绪，LumenX 直接提交）**：`h3_i2v.json`、`h3_r2v.json`、
  `flux_schnell_t2i.json`、`qwen_image_t2i.json`、`wan_vace_r2v.json`、
  `wan2_2_flf2v.json`、`qwen3_llm.json`。
- **原始 UI 格式（官方模板库）**：`image_krea2_turbo_*`、`video_wan2_2_14B_*`、
  `video_minimax_h3_*`、`audio-chatterbox_tts.json`、`llm_qwen3_5_text_gen.json` 等。
  这些是给 ComfyUI 界面用的模板，请在 ComfyUI 中打开后 **Save (API Format)**
  导出，覆盖同名文件或另存新名。

## 使用约定

- LumenX 按文件名从本目录读取工作流（`config/workflow_mapping.json` 里的值 = 文件名）。
- UI 格式文件不能直接用于提交，必须先导出为 API 格式。
- 导出后如使用新文件名，请同步更新 `config/workflow_mapping.json` 的映射
  （`video_generation.*` / `asset_generation.*` / `templates.*` / `model_overrides.*`）。
