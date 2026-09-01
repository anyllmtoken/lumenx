import os

import pytest

from src.models.comfyui_image import ComfyUIImageModel
from src.models.comfyui_video import ComfyUIVideoModel


class FakeComfyUI:
    """Fake client replacing ComfyUIClient inside the model adapters."""

    def __init__(self, base_url=None, protocol=None):
        self.protocol = protocol or "zealman"
        self.base_url = base_url or "http://comfyui.test"
        self.submitted = []
        self.uploaded = []

    def submit_workflow_task(self, workflow_id=None, parameters=None, upload_files=None, workflow=None):
        self.submitted.append(
            {
                "workflow_id": workflow_id,
                "parameters": parameters,
                "upload_files": upload_files,
                "workflow": workflow,
            }
        )
        return "task-1"

    def wait_for_task_completion(self, task_id, timeout=600, poll_interval=5):
        return {
            "status": "completed",
            "results": [
                {"type": "image", "raw": {"filename": "gen.png", "subfolder": "", "type": "output"}},
                {"type": "video", "raw": {"filename": "gen.mp4", "subfolder": "", "type": "output"}},
            ],
        }

    def upload_file(self, file_path, file_type="input"):
        self.uploaded.append((file_path, file_type))
        return {"filename": os.path.basename(file_path), "subfolder": "", "type": "input"}

    def download_file(self, filename, output_path, file_type="output", subfolder=""):
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as fh:
            fh.write(b"fake-media")
        return True

    def find_workflow_by_pattern(self, patterns):
        return patterns[0]

    def health_check(self):
        return True


@pytest.fixture
def fake_client(monkeypatch):
    fake = FakeComfyUI()
    monkeypatch.setattr("src.models.comfyui_image.ComfyUIClient", lambda **kw: fake)
    monkeypatch.setattr("src.models.comfyui_video.ComfyUIClient", lambda **kw: fake)
    return fake


class TestComfyUIImageModel:
    def test_generate_t2i(self, fake_client, tmp_path):
        model = ComfyUIImageModel({})
        out = tmp_path / "img.png"

        path, duration = model.generate(
            "a cinematic scene",
            str(out),
            model_name="comfyui-flux2-klein-t2i",
            size="1024*1024",
        )

        assert path == str(out)
        assert os.path.exists(out)
        assert duration >= 0
        submitted = fake_client.submitted[-1]
        assert submitted["workflow_id"] == "image_flux2_klein_text_to_image"
        assert submitted["parameters"]["75:68:value"] == 1024
        assert submitted["parameters"]["75:69:value"] == 1024

    def test_generate_i2i_injects_reference_image(self, fake_client, tmp_path):
        model = ComfyUIImageModel({})
        ref = tmp_path / "ref.png"
        ref.write_bytes(b"ref")
        out = tmp_path / "img2.png"

        model.generate(
            "same character",
            str(out),
            ref_image_path=str(ref),
            model_name="comfyui-flux2-klein-i2i",
        )

        submitted = fake_client.submitted[-1]
        assert submitted["workflow_id"] == "image_flux2_klein_image_edit_4b_distilled"
        assert submitted["parameters"]["76:image"] == "ref.png"
        assert (str(ref), "input") in fake_client.uploaded


class TestComfyUIVideoModel:
    def test_generate_i2v(self, fake_client, tmp_path):
        model = ComfyUIVideoModel({})
        out = tmp_path / "clip.mp4"
        image = tmp_path / "frame.png"
        image.write_bytes(b"frame")

        path, duration = model.generate(
            "camera pans left",
            str(out),
            img_path=str(image),
            model_name="comfyui-h3-i2v",
            duration=5,
            seed=123,
        )

        assert path == str(out)
        assert os.path.exists(out)
        submitted = fake_client.submitted[-1]
        assert submitted["workflow_id"] == "video_minimax_h3_i2v"
        assert submitted["parameters"]["105:104:prompt"] == "camera pans left"
        assert submitted["parameters"]["105:111:value"] == 5
        assert submitted["parameters"]["105:15:noise_seed"] == 123

    def test_generate_r2v_uses_reference_video_workflow(self, fake_client, tmp_path):
        model = ComfyUIVideoModel({})
        out = tmp_path / "r2v.mp4"
        image = tmp_path / "frame.png"
        image.write_bytes(b"frame")
        ref_video = tmp_path / "ref.mp4"
        ref_video.write_bytes(b"ref-video")

        model.generate(
            "mirror the reference motion",
            str(out),
            img_path=str(image),
            model_name="comfyui-h3-r2v",
            generation_mode="r2v",
            ref_video_urls=[str(ref_video)],
        )

        submitted = fake_client.submitted[-1]
        assert submitted["workflow_id"] == "video_minimax_h3_r2v"
        assert submitted["parameters"]["138:value"] == "mirror the reference motion"
        assert submitted["parameters"]["137:image"] == "frame.png"
        assert submitted["parameters"]["139:image"] == "frame.png"
        assert "reference_videos" not in submitted["parameters"]
        assert "image" not in submitted["parameters"]

    def test_h3_template_node_mapping(self, fake_client, tmp_path):
        model = ComfyUIVideoModel({})
        out = tmp_path / "h3.mp4"
        image = tmp_path / "frame.png"
        image.write_bytes(b"frame")

        model.generate(
            "camera pans",
            str(out),
            img_path=str(image),
            model_name="comfyui-h3-i2v",
            seed=11,
            duration=6,
        )

        params = fake_client.submitted[-1]["parameters"]
        assert params["114:image"] == "frame.png"
        assert params["105:15:noise_seed"] == 11
        assert params["105:111:value"] == 6
