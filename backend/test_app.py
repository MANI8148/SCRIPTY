from backend.app import app


def test_health_endpoint():
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] in {"healthy", "degraded"}


def test_generate_validation():
    client = app.test_client()
    response = client.post("/api/generate", json={"location": "", "year": 1920})
    assert response.status_code == 400


def test_generate_accepts_user_directed_story_payload():
    client = app.test_client()
    response = client.post("/api/generate", json={
        "location": "Orbital Mumbai",
        "year": 2250,
        "story_mode": "short",
        "genre": "science fiction",
        "theme": "memory and rebellion",
        "setting_period": "far future",
        "storyline": "A courier discovers that the city's memories are being edited.",
        "characters": "Asha Varma | protagonist | skeptical, loyal | protect the memory key\nDirector Sen | antagonist | calm, controlling | erase the uprising",
        "timeline_beats": "The memory key wakes during a power failure.\nAsha enters the orbital archive.",
        "character_instructions": "Asha should solve problems practically.",
        "style_instructions": "Cinematic, tense, non-historical.",
    })
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["story_mode"] == "short"
    assert "Asha Varma" in payload["story_text"]
    assert "memory key wakes" in payload["story_text"]


def test_metrics_endpoint():
    client = app.test_client()
    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert "generation" in response.get_json()


def test_research_dataset_stats_endpoint():
    client = app.test_client()
    response = client.get("/api/research/dataset/stats")
    assert response.status_code == 200
    payload = response.get_json()
    assert "source_count" in payload
    assert "passage_count" in payload


def test_research_respond_endpoint():
    client = app.test_client()
    response = client.post("/api/research/respond", json={"prompt": "cities revolution pressure", "top_k": 2})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["mode"] == "local_rag"
    assert "answer" in payload
