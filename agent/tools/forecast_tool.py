from strands import tool

from agent.forecast import get_hourly_temps
from agent.tools._common import out


@tool
def get_forecast(lat: float | None = None, lon: float | None = None) -> str:
    """Hourly temperature forecast (°C, local time) for a location.

    Args:
        lat: Latitude. Leave empty if unknown.
        lon: Longitude. Leave empty if unknown.
    """
    temps, source = get_hourly_temps(lat, lon)
    if temps is None:
        return out(
            {
                "available": False,
                "source": source,
                "note": "No forecast: rules will assume a hot day (> 32 °C).",
            }
        )
    return out(
        {
            "available": True,
            "source": source,
            "max_c": max(t for _, t in temps),
            "hourly": [[ts.strftime("%Y-%m-%dT%H:%M"), t] for ts, t in temps[:24]],
        }
    )
