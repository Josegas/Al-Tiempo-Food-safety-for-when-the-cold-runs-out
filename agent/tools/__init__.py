from agent.tools.clock_tool import get_current_time
from agent.tools.danger_signs_tool import check_danger_signs
from agent.tools.forecast_tool import get_forecast
from agent.tools.meals_tool import plan_meals
from agent.tools.outage_tool import track_outage
from agent.tools.reminder_tool import schedule_reminder
from agent.tools.safe_window_tool import compute_safe_window
from agent.tools.shelter_tool import plan_shelter_batches

ALL_TOOLS = [
    get_forecast,
    compute_safe_window,
    plan_meals,
    track_outage,
    plan_shelter_batches,
    schedule_reminder,
    check_danger_signs,
    get_current_time,
]
