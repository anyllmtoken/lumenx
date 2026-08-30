# config/comfyui_workflows

本目录存放 LumenX 提交给 ComfyUI 的工作流（standard/原生协议，API 格式）。

## 文件说明

本目录全部是 Comfy-Org 官方模板库的**原始 UI 格式**模板。它们同时承担两个角色：

- 在 ComfyUI 界面中打开（可看模板、下载模型、预览）；
- 在 ComfyUI 中 **Save (API Format)** 导出后**覆盖同名文件**，
  即变成 LumenX 可提交的 API 格式。

`config/workflow_mapping.json` 已经指向这些文件名，因此只要导出后覆盖同名文件，
映射无需再改。若导出时另存新名，请同步更新映射。

## 使用约定

- LumenX 按文件名从本目录读取工作流（`config/workflow_mapping.json` 里的值 = 文件名）。
- UI 格式文件不能直接用于提交，必须先导出为 API 格式并覆盖同名文件。
