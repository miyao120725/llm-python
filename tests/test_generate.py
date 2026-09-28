from app.providers.image.mock import _MINIMAL_PNG


def test_generate_image_without_file_is_text_to_image(client):
    response = client.post(
        "/v1/generate/image",
        data={"prompt": "一只在雨中的猫", "enhance_prompt": "true", "async_mode": "false"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["kind"] == "text_to_image"
    assert body["media"]["url"].startswith("/v1/media/")

    media = client.get(body["media"]["url"])
    assert media.status_code == 200
    assert media.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_video_four_modes_mock(client):
    text_resp = client.post(
        "/v1/generate/video",
        data={"prompt": "小猫在屋顶奔跑", "async_mode": "false"},
    )
    assert text_resp.status_code == 200
    assert text_resp.json()["status"] == "succeeded"
    assert text_resp.json()["kind"] == "text_to_video"
    assert text_resp.json()["media"]["url"].startswith("/v1/media/")

    image_resp = client.post(
        "/v1/generate/video",
        data={"prompt": "镜头缓缓推进", "async_mode": "false"},
        files={"image": ("cat.png", _MINIMAL_PNG, "image/png")},
    )
    assert image_resp.status_code == 200
    assert image_resp.json()["kind"] == "image_to_video"

    video_resp = client.post(
        "/v1/generate/video",
        data={"prompt": "改成赛博朋克风格", "async_mode": "false"},
        files={"video": ("clip.mp4", b"fake-mp4", "video/mp4")},
    )
    assert video_resp.status_code == 200
    assert video_resp.json()["kind"] == "video_to_video"

    both_resp = client.post(
        "/v1/generate/video",
        data={"prompt": "图中的猫沿视频运镜跑起来", "async_mode": "false"},
        files={
            "image": ("cat.png", _MINIMAL_PNG, "image/png"),
            "video": ("clip.mp4", b"fake-mp4", "video/mp4"),
        },
    )
    assert both_resp.status_code == 200
    assert both_resp.json()["kind"] == "image_and_video_to_video"


def test_llm_chat_and_enhance_prompt_mock(client):
    chat = client.post(
        "/v1/llm/chat",
        json={"messages": [{"role": "user", "content": "你好"}], "model": "string"},
    )
    assert chat.status_code == 200
    assert "mock-llm" in chat.json()["content"]
    assert chat.json()["conversation_id"] is None
    assert chat.json()["thinking"] is False
    assert chat.json()["search"] == "off"
    assert chat.json()["reasoning"] is None

    enhance = client.post(
        "/v1/llm/enhance-prompt",
        json={"prompt": "海边日落", "mode": "image"},
    )
    assert enhance.status_code == 200
    assert enhance.json()["original"] == "海边日落"

    enhance_video = client.post(
        "/v1/llm/enhance-prompt",
        json={"prompt": "小猫在屋顶奔跑", "mode": "video"},
    )
    assert enhance_video.status_code == 200
    assert enhance_video.json()["original"] == "小猫在屋顶奔跑"


def test_generate_image_with_file_is_image_to_image(client):
    response = client.post(
        "/v1/generate/image",
        data={"prompt": "改成赛博朋克", "async_mode": "false"},
        files={"image": ("cat.png", _MINIMAL_PNG, "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["kind"] == "image_to_image"
    assert body["media"]["url"].startswith("/v1/media/")

    media = client.get(body["media"]["url"])
    assert media.status_code == 200
    assert media.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_reject_invalid_image_upload(client):
    video_resp = client.post(
        "/v1/generate/video",
        data={"prompt": "推进", "async_mode": "false"},
        files={"image": ("notes.txt", b"not-an-image", "text/plain")},
    )
    assert video_resp.status_code == 400
    assert video_resp.json()["code"] == "invalid_upload"

    edit_resp = client.post(
        "/v1/generate/image",
        data={"prompt": "改风格", "async_mode": "false"},
        files={"image": ("notes.txt", b"not-an-image", "text/plain")},
    )
    assert edit_resp.status_code == 400
    assert edit_resp.json()["code"] == "invalid_upload"


def test_old_generate_paths_removed(client):
    json_resp = client.post("/v1/generate/text-to-image", json={"prompt": "猫"})
    assert json_resp.status_code == 404
    form_resp = client.post(
        "/v1/generate/image-to-image",
        data={"prompt": "改风格"},
        files={"image": ("cat.png", _MINIMAL_PNG, "image/png")},
    )
    assert form_resp.status_code == 404
    old_i2v = client.post(
        "/v1/generate/image-to-video",
        data={"prompt": "推进", "async_mode": "false"},
        files={"image": ("cat.png", _MINIMAL_PNG, "image/png")},
    )
    assert old_i2v.status_code == 404
    old_v2v = client.post(
        "/v1/generate/video-to-video",
        data={"prompt": "改风格", "async_mode": "false"},
        files={"video": ("clip.mp4", b"fake-mp4", "video/mp4")},
    )
    assert old_v2v.status_code == 404


def test_video_duration_out_of_range(client):
    response = client.post(
        "/v1/generate/video",
        data={"prompt": "小猫", "duration_seconds": "15", "async_mode": "false"},
    )
    assert response.status_code == 422


def test_generate_empty_prompt_rejected(client):
    image_resp = client.post("/v1/generate/image", data={"prompt": "", "async_mode": "false"})
    assert image_resp.status_code == 422
    video_resp = client.post("/v1/generate/video", data={"prompt": "", "async_mode": "false"})
    assert video_resp.status_code == 422
