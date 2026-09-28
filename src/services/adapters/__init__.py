from abc import ABC, abstractmethod

from src.schemas.diem_schema import ThiSinhDiemThpt
from src.services.adapters.score_provider import ExternalDgnlProvider, ExternalScoreProvider

__all__ = ["ExternalDgnlProvider", "ExternalScoreProvider", "ThiSinhDiemThpt", "ABC", "abstractmethod"]
