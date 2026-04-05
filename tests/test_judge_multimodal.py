"""Tests for multimodal judge — image detection and vision prompt building."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from exchange.judge import _is_image_submission, _build_vision_messages


def test_detects_png_base64():
    work = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
    assert _is_image_submission(work) is True


def test_detects_jpeg_base64():
    work = "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
    assert _is_image_submission(work) is True


def test_detects_webp_base64():
    work = "data:image/webp;base64,UklGR..."
    assert _is_image_submission(work) is True


def test_plain_text_not_image():
    work = "This is a regular text submission about cats."
    assert _is_image_submission(work) is False


def test_empty_string_not_image():
    assert _is_image_submission("") is False


def test_vision_messages_contain_image_url():
    task = "Draw a cat"
    image_data = "data:image/png;base64,iVBORw0KGgo"
    criteria = ["Accuracy", "Style"]
    messages = _build_vision_messages(task, image_data, criteria)

    # System message exists
    assert messages[0]["role"] == "system"

    # User message has both text and image_url content blocks
    user_msg = messages[1]
    assert user_msg["role"] == "user"
    assert isinstance(user_msg["content"], list)

    types = [block["type"] for block in user_msg["content"]]
    assert "text" in types
    assert "image_url" in types

    # Image URL block contains our data URI
    img_block = [b for b in user_msg["content"] if b["type"] == "image_url"][0]
    assert img_block["image_url"]["url"] == image_data


def test_vision_messages_include_task_in_text():
    task = "Draw a sunset over mountains"
    image_data = "data:image/png;base64,abc123"
    messages = _build_vision_messages(task, image_data, ["Quality"])

    text_block = [b for b in messages[1]["content"] if b["type"] == "text"][0]
    assert "Draw a sunset over mountains" in text_block["text"]
