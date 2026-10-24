"""Public score calculation contract; catalog comparison belongs to Next.js."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class ScorePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    method: Literal["THPT", "HOC_BA", "CHUNG_CHI", "DGNL"]
    year: int = Field(ge=2000, le=2100)
    combination: str = Field(min_length=1, max_length=20)
    # Certificate mode: scores[0] is the explicitly labelled Math input,
    # scores[1] is the second subject; no replacement subject is inferred.
    scores: list[Annotated[float, Field(ge=0, le=10, strict=True)]] = Field(min_length=3, max_length=3)
    region: Literal["KV3", "KV2", "KV2-NT", "KV1"] = "KV3"
    priority: Literal["NONE", "UT1", "UT2"] = "NONE"
    exam: Literal["HSA", "TSA"] = "HSA"
    exam_score: float = Field(default=0, ge=0, le=150)
    certificate: Literal["IELTS", "TOEFL", "SAT"] = "IELTS"
    certificate_score: float = Field(default=0, ge=0, le=1600)


class CalculationResult(BaseModel):
    method: str
    rawScore: float
    convertedScore: float | None
    finalScore: float | None
    priorityBonus: float
    maxPriority: float
    subDetails: list[dict[str, str]]
    passPreliminary: bool
    preliminaryNotes: list[str]
    combinationCode: str


class ComparisonRow(BaseModel):
    ma_chuong_trinh: str
    ten_chuong_trinh: str | None
    ma_nganh: str | None
    ten_nganh: str | None
    faculty: str
    benchmarkYear: int
    benchmarkScore: float | None
    predictionScore: float | None
    previousScore: float | None
    matchedMethodName: str
    chance: Literal['high', 'medium', 'low', 'unknown', 'ineligible']
    pointBand: Literal['high', 'medium', 'low'] | None = None
    diff: float | None
    reason: str


class ScorePreviewResponse(BaseModel):
    calculation: CalculationResult
    # Kept for compatibility with older clients; no catalog work is performed.
    programs: list[ComparisonRow] = Field(default_factory=list)

