# main/ai_parser.py
import re
from .models import WorkoutPlan, DietPlan

DAY_MARKER_REGEX = re.compile(r'(?:Day|DAY)\s*(\d{1,2})\s*[:\-–]\s*', re.IGNORECASE)

def split_into_days(text):
    """
    Splits the AI text into ordered dict of day -> content.
    Returns list of tuples: [(1, 'text for day1'), (2, 'text day2'), ...]
    If no day markers found, returns [(0, full_text)]
    """
    parts = []
    # find all markers with positions
    matches = list(DAY_MARKER_REGEX.finditer(text))
    if not matches:
        return [(0, text.strip())]
    for idx, match in enumerate(matches):
        start = match.end()
        day_num = int(match.group(1))
        end = matches[idx+1].start() if idx+1 < len(matches) else len(text)
        content = text[start:end].strip()
        parts.append((day_num, content))
    return parts

def save_parsed_plans(profile, text):
    """
    Parses text and creates WorkoutPlan entries for each day (or one entry if not parsed).
    Also tries to create a DietPlan summarizing diet parts (very basic).
    """
    days = split_into_days(text)
    created_workouts = []
    if len(days) == 1 and days[0][0] == 0:
        wp = WorkoutPlan.objects.create(member=profile, title='AI Plan', content=text)
        created_workouts.append(wp)
        # no reliable diet parse -> create a DietPlan placeholder
        DietPlan.objects.create(member=profile, title='AI Diet', content='See AI Plan')
    else:
        # create one WorkoutPlan per day
        for day, content in days:
            title = f"Day {day} - AI Plan"
            wp = WorkoutPlan.objects.create(member=profile, title=title, content=content)
            created_workouts.append(wp)
        # Create a simple DietPlan: find lines with breakfast/lunch/dinner keywords
        diet_lines = []
        for line in text.splitlines():
            l = line.strip()
            if not l:
                continue
            if any(k in l.lower() for k in ('breakfast','lunch','dinner','snack','snacks')):
                diet_lines.append(l)
        diet_text = '\n'.join(diet_lines) or 'Refer to day-wise plans for diet.'
        DietPlan.objects.create(member=profile, title='AI Diet (parsed)', content=diet_text)
    return created_workouts
