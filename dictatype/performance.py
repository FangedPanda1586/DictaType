from __future__ import annotations

import ctypes
import os
import platform
from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceProfile:
    requested_mode: str
    effective_mode: str
    ram_gb: float | None
    logical_cpus: int
    low_memory: bool
    audio_chunk_bytes: int
    classroom_result_limit: int

    @property
    def label(self) -> str:
        if self.requested_mode == "auto":
            return "Automatic · Low-memory/HDD" if self.low_memory else "Automatic · Standard"
        return "Low-memory / HDD" if self.low_memory else "Standard"

    @property
    def hardware_summary(self) -> str:
        ram = f"{self.ram_gb:.1f} GB RAM" if self.ram_gb else "RAM unknown"
        return f"{ram} · {self.logical_cpus} logical CPU(s)"


def _physical_memory_gb() -> float | None:
    """Return installed physical memory without adding a third-party dependency."""
    try:
        if os.name == "nt":
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return status.ullTotalPhys / (1024 ** 3)
        elif hasattr(os, "sysconf"):
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return (pages * page_size) / (1024 ** 3)
    except Exception:
        return None
    return None


def resolve_performance_profile(requested_mode: str = "auto") -> PerformanceProfile:
    requested = str(requested_mode or "auto").strip().casefold()
    if requested not in {"auto", "low", "standard"}:
        requested = "auto"

    ram_gb = _physical_memory_gb()
    cpus = max(1, int(os.cpu_count() or 1))

    # 4 GB classroom machines need the conservative path. 6 GB is used as the
    # automatic threshold to leave enough headroom for Windows, the browser and
    # antivirus software running alongside DictaType.
    detected_low = (ram_gb is not None and ram_gb <= 6.0) or cpus <= 2
    low_memory = detected_low if requested == "auto" else requested == "low"

    return PerformanceProfile(
        requested_mode=requested,
        effective_mode="low" if low_memory else "standard",
        ram_gb=ram_gb,
        logical_cpus=cpus,
        low_memory=low_memory,
        audio_chunk_bytes=32 * 1024 if low_memory else 128 * 1024,
        classroom_result_limit=250 if low_memory else 500,
    )


def apply_runtime_hints(profile: PerformanceProfile) -> None:
    """Apply conservative CPU hints before optional neural libraries are loaded."""
    if profile.low_memory:
        # These environment variables are read by common numerical runtimes.
        # They keep a four-core classroom PC responsive while audio is prepared.
        os.environ.setdefault("OMP_NUM_THREADS", "2")
        os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
        os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
    else:
        # Do not override an administrator's explicit values on faster systems.
        os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")


def platform_hint() -> str:
    return f"{platform.system()} {platform.release()}"
