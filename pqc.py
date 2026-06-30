"""后量子密码学（PQC）模拟模块 — Kyber512 / Kyber768。"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum


class KyberVariant(str, Enum):
    KYBER512 = "Kyber512"
    KYBER768 = "Kyber768"


@dataclass
class PQCState:
    algorithm: KyberVariant = KyberVariant.KYBER512
    session_key: str = field(default_factory=lambda: _generate_session_key("Kyber512"))
    renegotiation_count: int = 0


def _generate_session_key(algorithm: str) -> str:
    seed = f"{algorithm}-{time.time_ns()}"
    return hashlib.sha256(seed.encode()).hexdigest()[:16]


@dataclass
class PQCDecision:
    sample_id: int
    status: str
    pqc_action: str
    algorithm: str
    renegotiated: bool
    switched: bool = False


class PQCSimulator:
    def __init__(self, default_mode: str = "Kyber512") -> None:
        self.state = PQCState(
            algorithm=KyberVariant(default_mode)
            if default_mode in KyberVariant._value2member_map_
            else KyberVariant.KYBER512
        )

    @property
    def current_algorithm(self) -> str:
        return self.state.algorithm.value

    def switch_to_kyber512(self) -> tuple[str, bool]:
        if self.state.algorithm == KyberVariant.KYBER512:
            return self.state.session_key, False
        self.state.algorithm = KyberVariant.KYBER512
        self.state.session_key = _generate_session_key("Kyber512")
        return self.state.session_key, True

    def switch_to_kyber768(self) -> tuple[str, bool]:
        switched = self.state.algorithm != KyberVariant.KYBER768
        self.state.algorithm = KyberVariant.KYBER768
        self.state.session_key = _generate_session_key("Kyber768")
        return self.state.session_key, switched

    def renegotiate_key(self) -> str:
        self.state.renegotiation_count += 1
        self.state.session_key = _generate_session_key(self.state.algorithm.value)
        return self.state.session_key

    def process_sample(self, sample_id: int, is_anomaly: bool) -> PQCDecision:
        if is_anomaly:
            _, switched = self.switch_to_kyber768()
            self.renegotiate_key()
            return PQCDecision(
                sample_id=sample_id,
                status="ANOMALY",
                pqc_action="Kyber768",
                algorithm=self.state.algorithm.value,
                renegotiated=True,
                switched=switched or True,
            )
        self.switch_to_kyber512()
        return PQCDecision(
            sample_id=sample_id,
            status="NORMAL",
            pqc_action="Kyber512",
            algorithm=self.state.algorithm.value,
            renegotiated=False,
            switched=False,
        )
