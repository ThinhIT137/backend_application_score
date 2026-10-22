from pydantic import BaseModel

from src.models.giai_thuong import CapGiaiThuong, HangGiaiThuong, MonHoc


class GiaiThuongItem(BaseModel):
    ma_giai_thuong: str
    cccd: str
    giai_thuong: HangGiaiThuong
    loai_giai_thuong: CapGiaiThuong
    mon_hoc: MonHoc

    model_config = {"from_attributes": True}


class TaoGiaiThuongRequest(BaseModel):
    ma_giai_thuong: str
    giai_thuong: HangGiaiThuong
    loai_giai_thuong: CapGiaiThuong
    mon_hoc: MonHoc
