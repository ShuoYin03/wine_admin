from __future__ import annotations
from app.models.fx_rate import FxRate
from shared.database.models.fx_rate_db import FxRatesModel


def map_fx_rate(orm_rate: FxRatesModel) -> FxRate:
    return FxRate.model_validate(orm_rate)
