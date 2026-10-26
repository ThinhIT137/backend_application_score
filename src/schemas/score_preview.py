"""Public score calculation contract; catalog comparison belongs to Next.js."""
from typing import Annotated, Literal
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScorePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    method: Literal["THPT", "HOC_BA", "CHUNG_CHI", "DGNL"]
    year: int = Field(ge=2000, le=2100)
    combination: str = Field(min_length=1, max_length=20)
    scores: list[Annotated[float, Field(ge=0, le=10, strict=True)]] = Field(default_factory=list, max_length=3)
    annual_scores: list[list[Annotated[float, Field(ge=0, le=10, strict=True)]]] | None = None
    thpt_math_score: float | None = Field(default=None, ge=0, le=10)
    thpt_english_score: float | None = Field(default=None, ge=0, le=10)
    region: Literal["KV3", "KV2", "KV2-NT", "KV1"] = "KV3"
    priority: Literal["NONE", "UT1", "UT2"] = "NONE"
    exam: Literal["HSA", "TSA"] = "HSA"
    exam_score: float | None = Field(default=None, ge=0, le=150)
    certificate: Literal["IELTS"] = "IELTS"
    certificate_score: float | None = Field(default=None, ge=0, le=9)
    certificate_date: date | None = None

    @model_validator(mode="after")
    def validate_mode(self):
        if self.year != 2026:
            raise ValueError("This calculator is configured for UTC GHA 2026 only")
        if self.method == "DGNL":
            if self.exam_score is None or self.exam_score > (150 if self.exam == "HSA" else 100):
                raise ValueError("Exam score is required and must fit its scale")
        elif self.method == "HOC_BA":
            if self.annual_scores is None or len(self.annual_scores) != 3 or any(len(row) != 3 for row in self.annual_scores):
                raise ValueError("Provide all three annual scores for each of three subjects")
        elif len(self.scores) != 3:
            raise ValueError("Three subject scores are required")
        if self.certificate_score is not None:
            if self.certificate_score * 2 != int(self.certificate_score * 2):
                raise ValueError("IELTS score must use half bands")
            if self.certificate_date is None or self.certificate_date <= date(2024, 6, 30) or self.certificate_date > date.today():
                raise ValueError("IELTS issue date must be after 2024-06-30 and not in the future")
        elif self.method == "CHUNG_CHI" or self.certificate_date is not None:
            raise ValueError("IELTS band and valid issue date are required")
        return self



class CalculationResult(BaseModel):
    contractVersion: str
    variants: dict[str, dict]
    actualMethod: str
    certificateBonus: float
    method: str
    rawScore: float
    convertedScore: float | None
    finalScore: float | None
    priorityBonus: float
    maxPriority: float
    subDetails: list[dict[str, str]]
    passPreliminary: bool
    eligibilityStatus: Literal["pending", "met", "not_met"]
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

