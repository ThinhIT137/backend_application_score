from abc import ABC, abstractmethod


class NotificationPublisher(ABC):
    @abstractmethod
    def trigger_cong_bo_ket_qua(self, nam_tuyen_sinh: int) -> None:
        raise NotImplementedError


class NoOpNotificationPublisher(NotificationPublisher):
    def trigger_cong_bo_ket_qua(self, nam_tuyen_sinh: int) -> None:
        _ = nam_tuyen_sinh
