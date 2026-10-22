"""Configured provider contracts; URLs/tokens are server configuration, never request input."""
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from src.schemas.diem_schema import ThiSinhDiemThpt
from src.services.adapters.score_provider import ExternalScoreProvider, ExternalDgnlProvider


def fetch(url, token, params):
    if not url or not url.startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
        raise ValueError("Nguồn điểm chưa có URL HTTPS hợp lệ")
    request = Request(url + ("&" if "?" in url else "?") + urlencode(params), headers={"Authorization": f"Bearer {token}"} if token else {})
    with urlopen(request, timeout=15) as response:
        raw = response.read(5000001)
        if len(raw) > 5000000:
            raise ValueError("Nguồn điểm trả dữ liệu vượt giới hạn")
        return json.loads(raw)


class HttpThptProvider(ExternalScoreProvider):
    def __init__(self, url, token): self.url, self.token = url, token
    def fetch_thpt_scores(self, nam_hoc):
        body = fetch(self.url, self.token, {"nam_hoc": nam_hoc})
        rows = body.get("data", body) if isinstance(body, dict) else body
        if not isinstance(rows, list): raise ValueError("Nguồn điểm phải trả danh sách thí sinh/điểm môn")
        return [ThiSinhDiemThpt.model_validate(row) for row in rows]


class HttpDgnlProvider(ExternalDgnlProvider):
    def __init__(self, url, token): self.url, self.token = url, token
    def diem_khop(self, cccd, diem, nam=None):
        body = fetch(self.url, self.token, {"cccd": cccd, "nam": nam})
        data = body.get("data", body) if isinstance(body, dict) else {}
        return data.get("cccd") == cccd and int(data.get("nam", 0)) == nam and abs(float(data.get("diem", -1)) - float(diem)) < 0.0001


class DisabledProvider(ExternalScoreProvider, ExternalDgnlProvider):
    def fetch_thpt_scores(self, nam_hoc): raise ValueError("Chưa cấu hình nguồn THPT; dùng import có nguồn hoặc cấu hình API")
    def diem_khop(self, cccd, diem, nam=None): raise ValueError("Chưa cấu hình nguồn đối soát ĐGNL")
