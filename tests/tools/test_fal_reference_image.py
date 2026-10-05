"""fal_reference_image: payload per model, reference limits, error mapping,
cost per image, reference shrinking, and how image_selector routes to it
(reference requests only, never text-only ones). Runs fully offline."""

import base64
import io

import pytest
import requests
from PIL import Image

from lib.paths import REPO_ROOT
from tools.base_tool import ToolResult, ToolStatus
from tools.graphics.fal_reference_image import MAX_REF_SIDE, FalReferenceImage, _image_to_data_uri
from tools.graphics.image_selector import ImageSelector

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 64


class _Response:
    def __init__(self, status=200, payload=None, content=b"", headers=None, text=""):
        self.status_code = status
        self._payload = payload or {}
        self.content = content
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def _png(path, size=(64, 96), color=(200, 120, 80)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


@pytest.fixture
def fal(monkeypatch):
    """Fake fal.run: records each POST and serves one JPEG per requested image."""
    posts = []

    def post(url, **kwargs):
        posts.append({"url": url, **kwargs})
        count = kwargs["json"].get("num_images", 1)
        return _Response(payload={"images": [{"url": f"https://cdn.test/{i}.jpg"} for i in range(count)]})

    def get(url, **kwargs):
        return _Response(content=JPEG_BYTES, headers={"content-type": "image/jpeg"})

    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setenv("FAL_KEY", "test-key")
    return posts


def _decode(data_uri):
    header, encoded = data_uri.split(",", 1)
    return header, base64.b64decode(encoded)


class TestContract:
    def test_registered_with_its_layer3_skill(self):
        from tools.tool_registry import registry

        registry.discover()
        tool = registry.get("fal_reference_image")
        assert tool is not None and tool.provider == "fal" and tool.capability == "image_generation"
        assert tool.supports["requires_reference_image"] is True
        for skill in tool.agent_skills:
            assert (REPO_ROOT / ".agents" / "skills" / skill / "SKILL.md").exists(), skill

    def test_status_follows_the_key(self, monkeypatch):
        monkeypatch.delenv("FAL_KEY", raising=False)
        monkeypatch.delenv("FAL_AI_API_KEY", raising=False)
        assert FalReferenceImage().get_status() == ToolStatus.UNAVAILABLE
        monkeypatch.setenv("FAL_AI_API_KEY", "k")
        assert FalReferenceImage().get_status() == ToolStatus.AVAILABLE

    def test_cost_per_model_and_image(self):
        tool = FalReferenceImage()
        assert tool.estimate_cost({"prompt": "p"}) == 0.01
        assert tool.estimate_cost({"prompt": "p", "num_images": 3}) == 0.03
        assert tool.estimate_cost({"prompt": "p", "model": "fal-ai/flux-pro/kontext"}) == 0.04


class TestExecute:
    def test_muse_sends_ordered_data_uris_and_no_seed(self, fal, tmp_path):
        first = _png(tmp_path / "a.png", color=(255, 0, 0))
        second = _png(tmp_path / "b.png", color=(0, 0, 255))
        result = FalReferenceImage().execute({
            "prompt": "Image 1 is Meera. Image 2 is Raj.",
            "image_paths": [str(first), str(second)],
            "aspect_ratio": "9:16",
            "seed": 7,
            "output_path": str(tmp_path / "out" / "shot.png"),
        })
        assert result.success, result.error
        call = fal[0]
        assert call["url"] == "https://fal.run/meta/muse-image/edit"
        assert call["headers"]["Authorization"] == "Key test-key"
        payload = call["json"]
        assert "seed" not in payload
        assert payload["aspect_ratio"] == "9:16" and payload["output_format"] == "jpeg"
        assert [_decode(u)[1] for u in payload["image_urls"]] == [first.read_bytes(), second.read_bytes()]
        assert all(u.startswith("data:image/png;base64,") for u in payload["image_urls"])
        assert result.cost_usd == 0.01
        assert result.data["output"].endswith("shot.jpg")  # extension follows the real bytes
        assert result.data["references"] == [str(first), str(second)]

    def test_hosted_urls_follow_local_paths(self, fal, tmp_path):
        local = _png(tmp_path / "a.png")
        FalReferenceImage().execute({
            "prompt": "p",
            "image_paths": [str(local)],
            "image_urls": ["https://example.test/ref.png"],
            "output_path": str(tmp_path / "o.jpg"),
        })
        urls = fal[0]["json"]["image_urls"]
        assert urls[0].startswith("data:") and urls[1] == "https://example.test/ref.png"

    def test_kontext_takes_exactly_one_reference(self, fal, tmp_path):
        refs = [str(_png(tmp_path / f"{i}.png")) for i in range(2)]
        tool = FalReferenceImage()
        too_many = tool.execute({
            "prompt": "p", "model": "fal-ai/flux-pro/kontext", "image_paths": refs, "output_path": str(tmp_path / "o.jpg"),
        })
        assert not too_many.success and "1-1 reference" in too_many.error
        assert fal == []

        ok = tool.execute({
            "prompt": "p", "model": "fal-ai/flux-pro/kontext", "image_paths": refs[:1], "seed": 11,
            "output_path": str(tmp_path / "o.jpg"),
        })
        payload = fal[0]["json"]
        assert ok.success and ok.cost_usd == 0.04
        assert payload["image_url"].startswith("data:") and "image_urls" not in payload
        assert payload["seed"] == 11 and payload["guidance_scale"] == 3.5

    @pytest.mark.parametrize("count", [0, 11])
    def test_reference_count_is_checked_before_any_call(self, fal, tmp_path, count):
        refs = [str(_png(tmp_path / f"{i}.png")) for i in range(count)]
        result = FalReferenceImage().execute({"prompt": "p", "image_paths": refs, "output_path": str(tmp_path / "o.jpg")})
        assert not result.success and "1-10 reference" in result.error
        assert fal == []

    def test_content_policy_is_reported_as_not_billed(self, monkeypatch, tmp_path):
        monkeypatch.setenv("FAL_KEY", "k")
        monkeypatch.setattr(
            requests, "post",
            lambda url, **kw: _Response(status=422, text='{"detail":[{"type":"content_policy_violation"}]}'),
        )
        result = FalReferenceImage().execute({
            "prompt": "p", "image_paths": [str(_png(tmp_path / "a.png"))], "output_path": str(tmp_path / "o.jpg"),
        })
        assert not result.success and "not billed" in result.error

    def test_dropped_upload_that_hides_a_403_is_reported_as_a_key_problem(self, monkeypatch, tmp_path):
        # fal closes the socket after rejecting the key, so the big upload dies with an
        # SSL error; the empty-body probe then gets the real 403.
        monkeypatch.setenv("FAL_KEY", "k")
        probes = []

        def post(url, **kwargs):
            if kwargs["json"]:
                raise requests.exceptions.SSLError("EOF occurred in violation of protocol")
            probes.append(kwargs["json"])
            return _Response(status=403, text="forbidden")

        monkeypatch.setattr(requests, "post", post)
        result = FalReferenceImage().execute({
            "prompt": "p", "image_paths": [str(_png(tmp_path / "a.png"))], "output_path": str(tmp_path / "o.jpg"),
        })
        assert probes == [{}]  # the probe carried no prompt, so it can't run or bill
        assert not result.success
        assert "rejected this API key for meta/muse-image/edit (HTTP 403" in result.error
        assert "not billed" in result.error

    def test_plain_403_and_real_network_failures_are_told_apart(self, monkeypatch, tmp_path):
        monkeypatch.setenv("FAL_KEY", "k")
        ref = str(_png(tmp_path / "a.png"))
        inputs = {"prompt": "p", "image_paths": [ref], "output_path": str(tmp_path / "o.jpg")}

        monkeypatch.setattr(requests, "post", lambda url, **kw: _Response(status=403, text="forbidden"))
        assert "rejected this API key" in FalReferenceImage().execute(inputs).error

        def offline(url, **kw):
            raise requests.exceptions.ConnectionError("no route to host")

        monkeypatch.setattr(requests, "post", offline)
        assert "(network)" in FalReferenceImage().execute(inputs).error

    def test_every_requested_image_is_written_and_billed(self, fal, tmp_path):
        result = FalReferenceImage().execute({
            "prompt": "p", "image_paths": [str(_png(tmp_path / "a.png"))], "num_images": 3,
            "output_path": str(tmp_path / "out" / "v.jpg"),
        })
        assert result.success and len(result.artifacts) == 3 and result.cost_usd == 0.03
        assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["v_1.jpg", "v_2.jpg", "v_3.jpg"]

    def test_requires_output_path_and_a_known_model(self, fal, tmp_path):
        ref = str(_png(tmp_path / "a.png"))
        tool = FalReferenceImage()
        assert "output_path" in tool.execute({"prompt": "p", "image_paths": [ref]}).error
        assert "unknown model" in tool.execute(
            {"prompt": "p", "image_paths": [ref], "model": "fal-ai/other", "output_path": str(tmp_path / "o.jpg")}
        ).error

    def test_large_references_are_shrunk_to_jpeg(self, tmp_path):
        big = _png(tmp_path / "big.png", size=(3000, 2000))
        header, raw = _decode(_image_to_data_uri(str(big)))
        assert header == "data:image/jpeg;base64"
        with Image.open(io.BytesIO(raw)) as image:
            assert max(image.size) == MAX_REF_SIDE


class _TextOnlyStub:
    name = "stub_text"
    provider = "stubflux"
    capability = "image_generation"
    supports = {"seed": True}
    input_schema = {"properties": {"prompt": {}}}
    best_for = ["text to image"]
    quality_score = None

    def get_status(self):
        return ToolStatus.AVAILABLE


class _Score:
    def __init__(self, provider):
        self.provider = provider

    def explain(self):
        return f"stub {self.provider}"

    def to_dict(self):
        return {"provider": self.provider}


class TestSelectorRouting:
    def test_text_only_requests_never_reach_a_reference_only_tool(self):
        ref_tool, text_tool = FalReferenceImage(), _TextOnlyStub()
        selector = ImageSelector()
        assert selector._filter_candidates({"prompt": "a village at dusk"}, [ref_tool, text_tool]) == [text_tool]
        assert selector._filter_candidates({"prompt": "x", "image_paths": ["r.png"]}, [ref_tool, text_tool]) == [ref_tool]

    def test_reference_request_reaches_the_tool_with_its_model(self, monkeypatch, tmp_path):
        monkeypatch.setenv("FAL_KEY", "k")
        ref_tool = FalReferenceImage()
        captured = {}

        def fake_execute(inputs):
            captured.update(inputs)
            return ToolResult(success=True, data={})

        ref_tool.execute = fake_execute
        selector = ImageSelector()
        monkeypatch.setattr(selector, "_providers", lambda: [_TextOnlyStub(), ref_tool])
        monkeypatch.setattr("lib.scoring.rank_providers", lambda candidates, ctx: [_Score(t.provider) for t in candidates])

        ref = str(_png(tmp_path / "master.jpg"))
        result = selector.execute({
            "prompt": "Image 1 is the character reference for Meera. New scene…",
            "image_paths": [ref],
            "model": "meta/muse-image/edit",
            "aspect_ratio": "16:9",
            "preferred_provider": "fal",
            "output_path": str(tmp_path / "shot.jpg"),
        })
        assert result.success and result.data["selected_provider"] == "fal"
        assert captured["model"] == "meta/muse-image/edit"
        assert captured["image_paths"] == [ref] and captured["aspect_ratio"] == "16:9"
        assert "preferred_provider" not in captured
