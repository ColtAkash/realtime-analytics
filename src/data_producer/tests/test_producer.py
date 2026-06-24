import json
from unittest.mock import MagicMock, patch

import pytest

from schemas import generate_event


class TestProducerMessageFormat:
    def test_event_serializes_to_valid_json(self):
        for _ in range(50):
            event, key = generate_event()
            payload = json.dumps(event).encode()
            decoded = json.loads(payload)
            assert decoded == event

    def test_key_is_utf8_encodable(self):
        for _ in range(50):
            _, key = generate_event()
            encoded = key.encode("utf-8")
            assert len(encoded) > 0

    def test_payload_size_reasonable(self):
        for _ in range(100):
            event, _ = generate_event()
            payload = json.dumps(event).encode()
            assert len(payload) < 2048
