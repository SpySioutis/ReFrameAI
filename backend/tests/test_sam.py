import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("STORAGE_DIR", "/tmp/reframe_test_storage")
os.environ.setdefault("APP_SECRET_KEY", "test-secret")

from app.ai.sam.parser import parse_output_text
from app.ai.sam.prompts import build_object_prompt, validate_concept


def test_parse_image_line():
    text = "<0f>0<|box;x1=181;y1=365;x2=556;y2=486;w=1516;h=1600|><|mask;x=0;y=0;data=122,376,~abc|>"
    recs = parse_output_text(text)
    assert len(recs) == 1
    r = recs[0]
    assert r.frame == 0 and r.object_id == 0
    assert r.box["x1"] == 181 and r.box["h"] == 1600
    assert r.mask.h == 122 and r.mask.w == 376 and r.mask.encoding == "~"


def test_parse_multi_record_and_confidence():
    text = ("<0f>1<|box;x1=1;y1=2;x2=3;y2=4;w=10;h=10;c=0.96|>"
            "<|mask;x=0;y=0;c=0.96;data=2,2,!zz|>,"
            "2<|box;x1=5;y1=5;x2=9;y2=9;w=10;h=10|><|mask;x=0;y=0;data=2,2,~qq|>")
    recs = parse_output_text(text)
    assert len(recs) == 2
    assert recs[0].confidence == 0.96
    assert recs[0].mask.encoding == "!"


def test_parse_empty_is_valid():
    assert parse_output_text("") == []
    assert parse_output_text("   \n  ") == []


def test_build_object_prompt_point():
    p = build_object_prompt(30, 1, 960, 540, points=[(585, 366, True)])
    assert p == "<30f>1<|point;x=585;y=366;w=960;h=540|>"


def test_build_object_prompt_box_and_negative():
    p = build_object_prompt(0, 2, 1800, 1200, points=[(1430, 700, True), (1300, 450, False)],
                            box=(444, 626, 675, 849))
    assert p.startswith("<0f>2<|box;")
    assert "-<|point;x=1300;y=450;w=1800;h=1200|>" in p


def test_validate_concept():
    assert validate_concept("  yellow school bus ") == "yellow school bus"
    try:
        validate_concept("   ")
        raise AssertionError("should have raised")
    except ValueError:
        pass
