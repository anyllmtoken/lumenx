# config/comfyui_workflows

本目录存放 LumenX 提交给 ComfyUI 的工作流（standard/原生协议，API 格式）。

## 文件说明

本目录只保留**最小必要集**（Flux 2 图像 + MiniMax H3 视频 + Qwen3 LLM）：

| 文件 | 用途 |
|---|---|
| `image_flux2_klein_text_to_image.json` | 文生图 T2I（Flux 2 Klein 4B） |
| `image_flux2_klein_image_edit_4b_distilled.json` | 图生图 I2I（Flux 2 Klein 4B Edit） |
| `video_minimax_h3_i2v.json` | 图生视频 I2V（FL2VA int8） |
| `video_minimax_h3_r2v.json` | 参考生视频 R2V（Ref2VA int8） |
| `video_minimax_h3_t2v.json` | 文生视频 T2V（复用 FL2VA） |
| `llm_qwen3_5_text_gen.json` | LLM 剧本分析/提示词润色 |

这些是 Comfy-Org 官方模板库的**原始 UI 格式**模板：

- 在 ComfyUI 界面中打开（可看模板、下载模型、预览）；
- 在 ComfyUI 中 **Save (API Format)** 导出后**覆盖同名文件**，即变成 LumenX 可提交的 API 格式。

`config/workflow_mapping.json` 已指向这些文件名，导出后覆盖同名即可，映射无需再改。
若导出时另存新名，请同步更新映射。
