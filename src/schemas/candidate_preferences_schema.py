from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExpectedPreference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    ma_ho_so: str = Field(min_length=1, max_length=100)
    nguyen_vong_cu: int = Field(strict=True, ge=1)


class ChangeProgram(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    ma_chuong_trinh: str = Field(min_length=1, max_length=100)
    ma_chuong_trinh_cu: str = Field(min_length=1, max_length=100)


class ReorderPreferences(BaseModel):
    """Array order is the requested order; each entry carries its observed rank."""
    model_config = ConfigDict(extra="forbid")
    nam_tuyen_sinh: int = Field(strict=True, ge=1900, le=2100)
    thu_tu: list[ExpectedPreference] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_entries(self):
        ids = [item.ma_ho_so for item in self.thu_tu]
        ranks = [item.nguyen_vong_cu for item in self.thu_tu]
        if len(ids) != len(set(ids)) or len(ranks) != len(set(ranks)):
            raise ValueError("Duplicate dossier or expected rank")
        return self
