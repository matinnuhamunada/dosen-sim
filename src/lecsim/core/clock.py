"""Semester clock: tick index <-> calendar labels."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Clock:
    months_per_semester: int

    @property
    def semesters_per_year(self) -> int:
        return 12 // self.months_per_semester

    def years(self, semesters: int) -> int:
        """Whole years contained in ``semesters`` semesters."""
        return semesters // self.semesters_per_year

    def label(self, t: int) -> str:
        """Label for tick ``t`` (0-based), e.g. ``Y1S2``."""
        return f"Y{t // self.semesters_per_year + 1}S{t % self.semesters_per_year + 1}"
