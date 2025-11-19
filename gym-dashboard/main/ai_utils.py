# main/ai_utils.py
from django.conf import settings
import json

def _fallback_plan(profile):
    # Keep your existing fallback text (short)
    goal = profile.goal or "General Fitness"
    experience = profile.experience_level or "Beginner"
    age = profile.age or "N/A"
    height = f"{profile.height_cm} cm" if profile.height_cm else "N/A"
    weight = f"{profile.weight_kg} kg" if profile.weight_kg else "N/A"

    return {
        "type": "fallback",
        "text": (
            f"AI Unavailable — fallback plan generated.\n\n"
            f"Profile — Goal: {goal}, Experience: {experience}, Age: {age}, Height: {height}, Weight: {weight}\n\n"
            "7-day sample workout overview:\n"
            "Day 1: Full-body (squats, push-ups, bent-over rows, planks) — 3 sets each.\n"
            "Day 2: Cardio (30 min brisk walk or bike).\n"
            "Day 3: Upper body (dumbbell press, rows, shoulder press) — 3 sets.\n"
            "Day 4: Rest or light stretching.\n"
            "Day 5: Lower body (lunges, deadlifts, calf raises) — 3 sets.\n"
            "Day 6: HIIT 20 minutes (work/rest intervals).\n"
            "Day 7: Mobility and active recovery.\n\n"
            "Sample diet tips:\n"
            "- Breakfast: Oats / eggs / fruits.\n"
            "- Lunch: Protein + veg + complex carbs.\n"
            "- Dinner: Lighter protein + veg.\n"
            "- Snacks: Nuts, yogurt, fruit.\n\n"
            "Note: This is a generic fallback — integrate OpenAI later for richer plans."
        )
    }

def generate_plans(profile):
    """
    Attempt to get a structured JSON plan from OpenAI.
    Returns a dict:
      - if successful: {"type":"json","data": parsed_json}
      - if fallback: {"type":"fallback","text": "..."}
    """
    key = getattr(settings, 'OPENAI_API_KEY', '') or None
    if not key:
        return _fallback_plan(profile)

    try:
        import openai
        openai.api_key = key

        # JSON schema we expect — keep it simple and forgiving.
        system_instructions = (
            "You are a fitness coach. Output ONLY valid JSON (no explanatory text) "
            "matching the schema described. If you cannot provide the full fields, "
            "include them where possible but keep valid JSON.\n\n"
            "Schema:\n"
            "{\n"
            '  "member": {"age": int, "height_cm": int|null, "weight_kg": number|null, "goal": string},\n'
            '  "plan": [\n'
            '    { "day": 1, "workout": [{"name":"Squat","sets":3,"reps":"8-12","notes":"..."}], "diet": {"breakfast":"...","lunch":"...","dinner":"...","snacks":"..."} },\n'
            '    ... up to 7 items\n'
            '  ]\n'
            "}\n\n"
            "Important: ALWAYS return a JSON object with top-level keys 'member' and 'plan'. "
            "Do not return markdown or any surrounding text. Use simple strings and numbers."
        )

        prompt = (
            f"Generate a 7-day structured workout+diet plan for a user with the following profile:\n"
            f"Age: {profile.age}\nHeight_cm: {profile.height_cm}\nWeight_kg: {profile.weight_kg}\n"
            f"Goal: {profile.goal}\nExperience: {profile.experience_level}\n\n"
            "Follow the schema exactly and output valid JSON only."
        )

        # Use ChatCompletion (works for both gpt-3.5/gpt-4 style). Modify model name if needed.
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # change if unavailable
            messages=[
                {"role":"system","content": system_instructions},
                {"role":"user","content": prompt}
            ],
            max_tokens=1200,
            temperature=0.2,
        )

        raw = resp['choices'][0]['message']['content'].strip()

        # Attempt to parse JSON from the response. Sometimes model returns extra whitespace/newlines.
        try:
            parsed = json.loads(raw)
            return {"type":"json", "data": parsed}
        except json.JSONDecodeError:
            # Try to extract JSON substring (simple heuristic)
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    snippet = raw[start:end+1]
                    parsed = json.loads(snippet)
                    return {"type":"json", "data": parsed}
                except Exception:
                    pass
            # If parsing fails, return fallback with the text for debugging
            return {"type":"fallback", "text": f"OpenAI returned non-JSON. Raw output:\n{raw}"}
    except Exception as e:
        # network/model error => fallback
        return {"type":"fallback", "text": f"OpenAI error: {str(e)}\n\n" + _fallback_plan(profile)['text']}
