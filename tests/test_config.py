from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from flex_agent.config import (
    load_open_coding_concurrency,
    load_seed_pool_size,
    load_update_batch_size,
)


class ConfigLoaderTests(unittest.TestCase):
    def test_load_seed_pool_size_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(load_seed_pool_size(), 20)

    def test_load_seed_pool_size_from_env(self) -> None:
        with patch.dict(os.environ, {"FLEX_AGENT_SEED_POOL_SIZE": "50"}, clear=True):
            self.assertEqual(load_seed_pool_size(), 50)

    def test_load_update_batch_size_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(load_update_batch_size(), 20)

    def test_load_update_batch_size_from_env(self) -> None:
        with patch.dict(os.environ, {"FLEX_AGENT_UPDATE_BATCH_SIZE": "30"}, clear=True):
            self.assertEqual(load_update_batch_size(), 30)

    def test_load_open_coding_concurrency_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(load_open_coding_concurrency(), 40)


if __name__ == "__main__":
    unittest.main()
