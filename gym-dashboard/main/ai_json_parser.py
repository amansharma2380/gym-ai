# main/ai_json_parser.py
from .models import WorkoutPlan, DietPlan
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def validate_plan_json(parsed):
    """
    Basic validation: ensure top-level keys and plan is iterable.
    Returns (ok, message)
    """
    if not isinstance(parsed, dict):
        return False, "Top-level JSON must be an object"
    if 'plan' not in parsed or 'member' not in parsed:
        return False, "Missing 'plan' or 'member' keys"
    if not isinstance(parsed['plan'], list):
        return False, "'plan' must be a list"
    return True, "ok"

def save_json_plan(profile, parsed):
    """
    parsed is a dict matching the schema returned by the LLM.
    Save WorkoutPlan entries (one per day) and one DietPlan summary.
    Returns list of created WorkoutPlan objects.
    """
    ok, msg = validate_plan_json(parsed)
    if not ok:
        raise ValueError(f"Invalid plan JSON: {msg}")

    created = []
    diet_summary_lines = []

    for item in parsed.get('plan', []):
        # Accept either 'day' or numeric key index fallback
        day = item.get('day') or item.get('Day') or None
        if day is None:
            # generate from sequence if day missing
            day = len(created) + 1

        workout = item.get('workout') or []
        # Create a readable text for the workout
        workout_text_lines = []
        for ex in workout:
            name = ex.get('name') or ex.get('exercise') or 'Exercise'
            sets = ex.get('sets')
            reps = ex.get('reps') or ex.get('repetition') or ''
            notes = ex.get('notes') or ''
            parts = [name]
            if sets is not None:
                parts.append(f"sets: {sets}")
            if reps:
                parts.append(f"reps: {reps}")
            if notes:
                parts.append(f"({notes})")
            workout_text_lines.append(" — ".join(parts))
        workout_text = "\n".join(workout_text_lines) if workout_text_lines else (item.get('workout','') or '')

        # diet may be dict with breakfast/lunch/dinner/snacks
        diet = item.get('diet') or {}
        diet_text = ""
        if isinstance(diet, dict):
            lines = []
            for k in ('breakfast','lunch','dinner','snacks'):
                if k in diet and diet[k]:
                    lines.append(f"{k.capitalize()}: {diet[k]}")
            diet_text = "\n".join(lines)
        else:
            diet_text = str(diet)

        # Save workout for this day
        title = f"Day {day} - AI Workout"
        wp = WorkoutPlan.objects.create(member=profile, title=title, content=workout_text)
        created.append(wp)

        # Append diet lines to summary
        if diet_text:
            diet_summary_lines.append(f"Day {day}:\n{diet_text}")

    # Create a diet plan summary
    diet_content = "\n\n".join(diet_summary_lines) if diet_summary_lines else "Refer to workouts for diet."
    DietPlan.objects.create(member=profile, title='AI Diet (parsed JSON)', content=diet_content)

    return created
