"""Protocol definitions for Pramana eval format."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AssertionType(str, Enum):
    """Supported assertion types."""

    EXACT_MATCH = "exact_match"
    CONTAINS = "contains"
    CONTAINS_ANY = "contains_any"
    IS_JSON = "is_json"
    LLM_JUDGE = "llm_judge"
    SEMANTIC_SIMILARITY = "semantic_similarity"


class Category(str, Enum):
    """Test case categories."""

    REASONING = "reasoning"
    FACTUAL = "factual"
    INSTRUCTION_FOLLOWING = "instruction_following"
    CODING = "coding"
    SAFETY = "safety"
    CREATIVE = "creative"


class Assertion(BaseModel):
    """Assertion configuration for test evaluation."""

    type: AssertionType
    case_sensitive: bool = True
    threshold: float | None = None  # For semantic_similarity
    judge_prompt: str | None = None  # For llm_judge


class TestMetadata(BaseModel):
    """Metadata for a test case."""

    difficulty: Literal["easy", "medium", "hard"]
    tokens_est: int
    tags: list[str] = Field(default_factory=list)


class TestCase(BaseModel):
    """A single test case in an eval suite."""

    id: str
    category: Category
    input: str | list[dict[str, str]]  # String or chat messages
    ideal: str | list[str] | None = None
    assertion: Assertion
    metadata: TestMetadata


class AssertionResult(BaseModel):
    """Result of evaluating an assertion."""

    passed: bool
    details: dict[str, Any] = Field(default_factory=dict)


class TestResult(BaseModel):
    """Result of running a single test."""

    test_id: str
    output: str
    assertion_result: AssertionResult
    latency_ms: int
    result_hash: str


class RunMetadata(BaseModel):
    """Metadata about an eval run."""

    timestamp: datetime
    model_id: str
    temperature: float
    seed: int | None
    runner_version: str

    # User tracking fields (for personalized feedback)
    user_id: str | None = None  # UUID of authenticated user
    is_authenticated: bool = False  # True if submitted with valid token


class RunSummary(BaseModel):
    """Summary statistics for a run."""

    total: int
    passed: int
    pass_rate: float


class EvalResults(BaseModel):
    """Complete results from an eval run."""

    suite_version: str
    suite_hash: str
    run_metadata: RunMetadata
    results: list[TestResult]
    summary: RunSummary
