"""Reusable search signal templates.

These are topic-agnostic signal vocabularies. Specific benchmark topics belong
in app/eval/topic_profiles.yaml, not here.
"""

from __future__ import annotations


PRODUCTION_SIGNALS = [
    "production",
    "deploy",
    "deployment",
    "self-host",
    "self hosted",
    "kubernetes",
    "docker",
    "cloud",
    "scale",
    "latency",
    "performance",
]

INTEGRATION_SIGNALS = [
    "integration",
    "api",
    "webhook",
    "plugin",
    "sdk",
    "connector",
    "workflow",
]

ENTERPRISE_SIGNALS = [
    "enterprise",
    "sso",
    "oidc",
    "auth",
    "permission",
    "security",
    "audit",
    "team",
    "rbac",
]

OBSERVABILITY_SIGNALS = [
    "observability",
    "trace",
    "tracing",
    "monitoring",
    "debug",
    "debugging",
    "evaluation",
    "eval",
    "metrics",
]

COMMERCIAL_GAP_SIGNALS = [
    "hosted",
    "managed",
    "dashboard",
    "ui",
    "no-code",
    "template",
    "boilerplate",
    "admin",
]

NEGATIVE_SIGNAL_TERMS = [
    "typo",
    "beginner",
    "homework",
    "simple install error",
    "duplicate",
    "local environment",
    "one-off bug",
    "pip install",
    "npm install",
    "my laptop",
]

POSITIVE_SIGNAL_TERMS = (
    PRODUCTION_SIGNALS
    + INTEGRATION_SIGNALS
    + ENTERPRISE_SIGNALS
    + OBSERVABILITY_SIGNALS
    + COMMERCIAL_GAP_SIGNALS
)

# Backwards-compatible aliases used by older nodes/tests.
COMMERCIAL_SIGNAL_TERMS = POSITIVE_SIGNAL_TERMS

REPO_SEARCH_PATTERNS = [
    "{term} in:name,description,readme",
    "{term} production in:name,description,readme",
    "{term} framework tool in:name,description,readme",
]

GLOBAL_ISSUE_PATTERNS = [
    "{term} type:issue",
    "{term} production type:issue",
    "{term} workflow blocker type:issue",
    "{term} repeated feature request type:issue",
    "{term} workaround type:issue",
    '"{term}" production deployment type:issue',
    '"{term}" integration workflow type:issue',
    '"{term}" enterprise security permission type:issue',
    '"{term}" observability debugging evaluation type:issue',
    '"{term}" hosted managed dashboard type:issue',
]

REPO_ISSUE_PATTERNS = [
    "production deployment workflow",
    "integration api sdk workflow",
    "enterprise sso auth permission security",
    "observability tracing debugging evaluation metrics",
    "hosted managed dashboard ui",
]

EXPANSION_PATTERNS = [
    '"{term}" missing feature type:issue',
    '"{term}" workaround type:issue',
    '"{term}" production support type:issue',
    '"{term}" self hosted type:issue',
    '"{term}" production deployment blocker type:issue',
    '"{term}" integration workflow friction type:issue',
    '"{term}" enterprise auth permission audit type:issue',
    '"{term}" observability debugging tracing type:issue',
    '"{term}" hosted managed dashboard type:issue',
    '"{term}" manual workaround repeated feature request type:issue',
]
