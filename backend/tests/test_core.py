import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("STORAGE_DIR", "/tmp/reframe_test_storage")
os.environ.setdefault("APP_SECRET_KEY", "test-secret")

import numpy as np

from app.ai.muse_spark.provider import plan_locally
from app.ai.orchestration.tools import tool_names, validate_tool_call
from app.video.masks import bounding_box, ellipse_mask_from_box, refine_mask


def test_tool_registry_allowlist():
    names = tool_names()
    assert "remove_object" in names and "export_video" in names
    args = validate_tool_call("segment_object", {"project_id": "p", "frame_number": 3, "x": 10, "y": 20})
    assert args.frame_number == 3
    try:
        validate_tool_call("rm -rf", {})
        raise AssertionError("should have raised")
    except ValueError:
        pass


def test_local_planner_remove_replace_unknown():
    assert plan_locally("Remove the person walking behind me").operation == "remove"
    assert plan_locally("Replace the can with a bottle").operation == "replace"
    unk = plan_locally("hello there")
    assert unk.needs_clarification and unk.question


def test_mask_utils():
    m = np.zeros((100, 100), dtype=np.uint8)
    m[10:20, 30:40] = 1
    box = bounding_box(m)
    assert (box["x1"], box["y1"], box["x2"], box["y2"]) == (30, 10, 39, 19)
    e = ellipse_mask_from_box(100, 100, {"x1": 10, "y1": 10, "x2": 50, "y2": 50})
    assert e.sum() > 0
    r = refine_mask(m)
    assert r.shape == (100, 100)


def test_local_segmentation_synthetic():
    import cv2

    from app.ai.sam.local import segment_box, segment_click

    img = np.full((200, 200, 3), 60, dtype=np.uint8)
    cv2.rectangle(img, (70, 70), (130, 130), (200, 50, 50), -1)
    m = segment_click(img, 100, 100)
    assert m.sum() > 100
    m2 = segment_box(img, 60, 60, 140, 140)
    assert m2.sum() > 100
