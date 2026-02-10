"""Pytest 配置与公共 fixture。"""

import os
import pytest


@pytest.fixture(autouse=True)
def env_clean():
    """测试时避免读真实 .env（可选）。"""
    yield
    # 可在此清理测试注入的 env
