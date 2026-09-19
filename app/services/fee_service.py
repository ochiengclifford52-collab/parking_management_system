"""
Fee calculation — no hard-coded KES values.

The algorithm reads tariff bands from the DB on every call.
Boundary rule: the tariff band whose max_duration_minutes >= the
session's minutes wins. Partial minutes round UP to the next minute.
"""
import math
from ..models.tariff import Tariff


class FeeCalculationService:

    @staticmethod
    def calculate_duration(entry_time, exit_time):
        delta = exit_time - entry_time
        seconds = max(0, int(delta.total_seconds()))
        minutes = max(0, math.ceil(seconds / 60))
        h, m = divmod(minutes, 60)
        if h and m:
            human = f"{h}h {m}m"
        elif h:
            human = f"{h}h"
        else:
            human = f"{m}m"
        return {"seconds": seconds, "minutes": minutes, "hours": h, "human": human}

    @classmethod
    def calculate_fee(cls, entry_time, exit_time, tariff_rules=None):
        duration = cls.calculate_duration(entry_time, exit_time)
        minutes = duration["minutes"]

        if tariff_rules is None:
            tariff_rules = (Tariff.query
                            .filter_by(is_active=True)
                            .order_by(Tariff.max_duration_minutes.asc()).all())
        if not tariff_rules:
            raise RuntimeError("No active tariff rules configured.")

        tariff_rules = sorted(tariff_rules, key=lambda t: t.max_duration_minutes)
        chosen = next((r for r in tariff_rules if minutes <= r.max_duration_minutes),
                      tariff_rules[-1])
        return {
            "duration": duration,
            "applicable_tariff": chosen.name,
            "band_name": chosen.name,
            "tariff_id": chosen.id,
            "amount": float(chosen.amount),
        }