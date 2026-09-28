import enum

from sqlalchemy import Enum as SAEnum


class TrangThaiDuyet(str, enum.Enum):
    cho = "cho"
    hop_le = "hop_le"
    tu_choi = "tu_choi"


class NguonDuLieu(str, enum.Enum):
    tu_nop = "tu_nop"
    dong_bo_bo = "dong_bo_bo"


class LoaiBangDiem(str, enum.Enum):
    lop_10 = "lop_10"
    lop_11 = "lop_11"
    lop_12 = "lop_12"
    tnTHPT = "tnTHPT"


def pg_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=True,
        create_constraint=False,
        values_callable=lambda cls: [item.value for item in cls],
    )
