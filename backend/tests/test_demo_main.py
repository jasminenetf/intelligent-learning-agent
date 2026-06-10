from fastapi.testclient import TestClient

from app.demo_main import STATE, app


client = TestClient(app)
STATE["llm_provider"] = "mock"


def test_demo_backend_open_bootstrap_and_settings_status():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

    bootstrap = client.get("/api/app/bootstrap")
    assert bootstrap.status_code == 200
    data = bootstrap.json()
    assert data["ok"] is True
    assert data["data"]["user"]["authenticated"] is True

    settings = client.get("/api/settings/status")
    assert settings.status_code == 200
    assert "llm_provider" in settings.json()


def test_generate_mindmap_returns_chinese_mermaid_for_topic():
    response = client.post(
        "/api/app/generate",
        json={"course_id": 1, "resource_type": "mindmap", "topic": "函数极限的定义"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["type"] == "mindmap"
    assert "函数极限" in data["title"]
    assert data["mermaid"].startswith(("mindmap", "flowchart"))
    assert "核心定义" in data["mermaid"]


def test_generate_quiz_returns_valid_items_for_topic():
    response = client.post(
        "/api/app/generate",
        json={"course_id": 1, "resource_type": "quiz", "topic": "函数极限的定义"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["type"] == "quiz"
    assert "函数极限" in data["title"]
    assert len(data["items"]) >= 3
    for item in data["items"]:
        assert item["question"]
        assert len(item["options"]) >= 2
        assert 0 <= int(item["answer"]) < len(item["options"])


def test_resource_center_generation_and_download():
    response = client.post(
        "/api/resources/generate",
        json={"course_id": 1, "topic": "函数极限", "resource_types": ["mindmap", "quiz", "ppt"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert len(data["resources"]) == 3
    assert {r["label"] for r in data["resources"]} == {"思维导图", "练习题", "PPT课件"}

    listing = client.get("/api/resources/generated")
    assert listing.status_code == 200
    assert listing.json()["ok"] is True

    resource_id = data["resources"][0]["resource_id"]
    download = client.get(f"/api/resources/download/{resource_id}")
    assert download.status_code == 200
    assert "函数极限" in download.text
