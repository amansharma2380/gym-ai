from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.urls import reverse
from .forms import (
    UserRegistrationForm,
    MemberProfileForm,
    ProgressEnteryForm,
    PaymentForm,
    ProgressPhotoForm,
)

from .models import MemberProfile, Payment, WorkoutPlan, DietPlan, Progress
from .ai_utils import generate_plans
from .ai_parser import save_parsed_plans
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import ProgressSerializer
from .ai_utils import generate_plans
from .ai_json_parser import save_json_plan
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import WorkoutPlan, Progress, ProgressPhoto
from .forms import ProgressPhotoForm

@require_POST
@login_required
def generate_plan_ajax(request):
    """
    AJAX endpoint to generate plan for the logged-in user.
    Returns JSON: {ok: true, message: "...", created_count: N}
    """
    profile = request.user.memberprofile
    if not profile.is_payment_approved:
        return JsonResponse({'ok': False, 'message': 'Payment not approved.'}, status=403)

    # call existing generate helper (which returns structured JSON or fallback)
    from .ai_utils import generate_plans
    from .ai_json_parser import save_json_plan

    resp = generate_plans(profile)
    try:
        if resp.get('type') == 'json':
            parsed = resp.get('data')
            created = save_json_plan(profile, parsed)
            return JsonResponse({'ok': True, 'message': 'AI JSON plan generated.', 'created_count': len(created)})
        else:
            # fallback: parse raw text (use existing parser to create at least one plan)
            # save_parsed_plans is robust; use it
            from .ai_parser import save_parsed_plans
            text = resp.get('text') if isinstance(resp, dict) else str(resp)
            created = save_parsed_plans(profile, text)
            return JsonResponse({'ok': True, 'message': 'Fallback plan generated.', 'created_count': len(created)})
    except Exception as e:
        # on error return helpful message
        return JsonResponse({'ok': False, 'message': f'Failed to generate/save plan: {str(e)}'}, status=500)


@require_POST
@login_required
def delete_plan_ajax(request, plan_id):
    """
    AJAX endpoint to delete a WorkoutPlan (only owner or admin allowed)
    """
    plan = get_object_or_404(WorkoutPlan, id=plan_id)
    if not (request.user.is_superuser or plan.member.user == request.user):
        return HttpResponseForbidden("Not allowed")

    plan.delete()
    return JsonResponse({'ok': True, 'message': 'Plan deleted'})



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_progress_list(request):
    profile = request.user.memberprofile
    entries = profile.progress.order_by('date')
    serializer = ProgressSerializer(entries, many=True)
    return Response(serializer.data)

def home(request):
    return render(request, 'main/home.html')

def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        profile_form = MemberProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            # create user first
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()

            # use get_or_create to avoid duplicate MemberProfile (signals may have created one)
            profile_data = profile_form.cleaned_data
            profile, created = MemberProfile.objects.get_or_create(user=user)

            # update fields from the form into profile
            profile.phone = profile_data.get('phone') or profile.phone
            profile.age = profile_data.get('age') or profile.age
            profile.height_cm = profile_data.get('height_cm') or profile.height_cm
            profile.weight_kg = profile_data.get('weight_kg') or profile.weight_kg
            profile.gender = profile_data.get('gender') or profile.gender
            profile.goal = profile_data.get('goal') or profile.goal
            profile.experience_level = profile_data.get('experience_level') or profile.experience_level
            profile.save()

            messages.success(request, "Registration successful. Please login.")
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserRegistrationForm()
        profile_form = MemberProfileForm()
    return render(request, 'main/register.html', {'user_form': user_form, 'profile_form': profile_form})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, "Invalid credentials.")
    return render(request, 'main/login.html')

def user_logout(request):
    logout(request)
    return redirect('home')
from .forms import MemberProfileForm, ProgressEnteryForm
from django.contrib.auth.decorators import login_required

@login_required
def edit_profile(request):
    profile = request.user.memberprofile
    if request.method == 'POST':
        form = MemberProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('dashboard')
    else:
        form = MemberProfileForm(instance=profile)
    return render(request, 'main/edit_profile.html', {'form': form})

@login_required
def delete_plan(request, id):
    plan = get_object_or_404(WorkoutPlan, id=id)

    # Only the owner or admin can delete
    if request.user.is_superuser or plan.member.user == request.user:
        plan.delete()
        messages.success(request, "Plan deleted successfully.")
    else:
        messages.error(request, "You are not allowed to delete this plan.")

    return redirect('dashboard')

@login_required
def add_progress(request):
    profile = request.user.memberprofile
    if request.method == 'POST':
        form = ProgressEnteryForm(request.POST)   # ← correct name here
        if form.is_valid():
            pe = form.save(commit=False)
            pe.member = profile
            pe.save()
            messages.success(request, "Progress entry added.")
            return redirect('dashboard')
    else:
        form = ProgressEnteryForm()
    return render(request, 'main/add_progress.html', {'form': form})


@login_required
def dashboard(request):
    profile = request.user.memberprofile

    workouts = profile.workouts.order_by('-created_at')[:10]
    diets = profile.diets.order_by('-created_at')[:5]
    progress_qs = profile.progress.order_by('date')  # oldest → newest
    progress_recent = profile.progress.order_by('-date')[:20]
    photos = profile.photos.order_by('-created_at')[:6]

    # --- ANALYTICS: BMI, weight change, goal progress ---
    bmi = None
    bmi_status = None
    start_weight = None
    current_weight = None
    weight_change = None
    progress_count = progress_qs.count()

    if progress_count > 0:
        start_weight = progress_qs.first().weight_kg
        current_weight = progress_qs.last().weight_kg
        if start_weight and current_weight:
            weight_change = current_weight - start_weight  # positive = gain, negative = loss

    if profile.height_cm and (profile.weight_kg or current_weight):
        h_m = profile.height_cm / 100.0
        w = current_weight or profile.weight_kg
        if h_m > 0 and w:
            bmi = round(w / (h_m * h_m), 1)
            if bmi < 18.5:
                bmi_status = "Underweight"
            elif bmi < 25:
                bmi_status = "Normal"
            elif bmi < 30:
                bmi_status = "Overweight"
            else:
                bmi_status = "Obese"

    # simple goal progress estimate based on weight change
    goal_progress_percent = 0
    if weight_change is not None and profile.goal:
        g = profile.goal.lower()
        if "loss" in g or "fat" in g:
            target = 8.0  # assume 8 kg target loss
            loss = max(0, start_weight - current_weight)
            goal_progress_percent = min(100, int((loss / target) * 100))
        elif "gain" in g or "muscle" in g:
            target = 5.0
            gain = max(0, current_weight - start_weight)
            goal_progress_percent = min(100, int((gain / target) * 100))

    # --- WEEKLY ACTIVITY (last 7 days progress calendar) ---
    today = timezone.now().date()
    last7 = []
    progress_dates = set(p.date for p in progress_qs if p.date)
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        label = d.strftime('%a')  # Mon, Tue...
        last7.append({
            "label": label,
            "date": d,
            "active": d in progress_dates
        })

    # --- DIET MACROS (simple percentages based on goal) ---
    goal = (profile.goal or "").lower()
    if "loss" in goal or "fat" in goal:
        macros = {"protein": 40, "carbs": 30, "fat": 30}
    elif "gain" in goal or "muscle" in goal:
        macros = {"protein": 35, "carbs": 45, "fat": 20}
    else:
        macros = {"protein": 30, "carbs": 45, "fat": 25}

    # --- ACHIEVEMENTS / BADGES ---
    achievements = []
    if progress_count >= 1:
        achievements.append("First Step: Logged your progress")
    if progress_count >= 7:
        achievements.append("Consistency: 7+ progress updates")
    if progress_count >= 30:
        achievements.append("Committed: 30+ progress logs")
    if workouts.exists():
        achievements.append("AI Explorer: Generated workout plan")
    if bmi and 18.5 <= bmi <= 24.9:
        achievements.append("Healthy BMI Range")

    photo_form = ProgressPhotoForm()

    context = {
        "profile": profile,
        "workouts": workouts,
        "diets": diets,
        "progress": progress_recent,
        "bmi": bmi,
        "bmi_status": bmi_status,
        "start_weight": start_weight,
        "current_weight": current_weight,
        "weight_change": weight_change,
        "goal_progress_percent": goal_progress_percent,
        "weekly_activity": last7,
        "macros": macros,
        "achievements": achievements,
        "photos": photos,
        "photo_form": photo_form,
    }
    return render(request, "main/dashboard.html", context)
@require_POST
@login_required
def ai_coach_ajax(request):
    question = request.POST.get("question", "").strip()
    if not question:
        return JsonResponse({"ok": False, "answer": "Please type a question first."})

    q = question.lower()
    # Simple rule-based responses; you can swap with OpenAI later if quota allows
    if "weight loss" in q or "fat" in q:
        answer = (
            "For effective weight loss: focus on a small calorie deficit, "
            "3–5 days of cardio, and 2–3 days of strength training weekly. "
            "Keep protein high and track your progress consistently."
        )
    elif "muscle" in q or "bulk" in q:
        answer = (
            "For muscle gain: train each muscle group 2x per week with progressive overload, "
            "sleep 7–8 hours, and aim for a slight calorie surplus with high protein."
        )
    elif "cardio" in q:
        answer = (
            "Cardio suggestion: 20–30 minutes, 3–4 times per week. "
            "Mix steady-state with one HIIT session if you are comfortable."
        )
    elif "diet" in q or "food" in q or "meal" in q:
        answer = (
            "Basic diet guideline: include a lean protein, complex carb, and vegetables in each meal. "
            "Limit sugary drinks and processed foods. Drink plenty of water."
        )
    else:
        answer = (
            "Great question! For best results, combine regular strength training, some cardio, "
            "good sleep, and a balanced diet. Start simple and stay consistent."
        )

    return JsonResponse({"ok": True, "answer": answer})



@user_passes_test(lambda u: u.is_superuser)
def admin_payments(request):
    payments = Payment.objects.order_by('-created_at').all()
    if request.method == 'POST':
        pid = request.POST.get('payment_id')
        action = request.POST.get('action')
        try:
            p = Payment.objects.get(id=pid)
            if action == 'approve':
                p.status = 'Approved'
                p.save()
                # mark profile approved
                p.member.is_payment_approved = True
                p.member.save()
            elif action == 'reject':
                p.status = 'Rejected'
                p.save()
            messages.success(request, "Action completed.")
        except Payment.DoesNotExist:
            messages.error(request, "Payment not found.")
        return redirect('admin_payments')
    return render(request, 'main/admin_payments.html', {'payments': payments})

@login_required
def make_payment(request):
    # simple demo: create a Payment record (no real gateway)
    profile = request.user.memberprofile
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            p = form.save(commit=False)
            p.member = profile
            p.status = 'Pending'
            p.save()
            messages.success(request, "Payment created and is pending admin approval.")
            return redirect('dashboard')
    else:
        form = PaymentForm()
    return render(request, 'main/make_payment.html', {'form': form})

@login_required
def generate_plan(request, member_id=None):
    # allow members to generate for themselves; admins can generate for a member by id
    if member_id:
        if not request.user.is_superuser:
            messages.error(request, "Only admin can generate plan for other members.")
            return redirect('dashboard')
        profile = get_object_or_404(MemberProfile, id=member_id)
    else:
        profile = request.user.memberprofile

    if not profile.is_payment_approved:
        messages.error(request, "Payment not approved. Please make payment and wait for admin approval.")
        return redirect('dashboard')

    resp = generate_plans(profile)  # new generate_plans returns dict with type

    try:
        if resp.get('type') == 'json':
            parsed = resp.get('data')
            # Save parsed JSON to DB using the parser
            created = save_json_plan(profile, parsed)
            messages.success(request, f"AI JSON plan generated and saved ({len(created)} workout entries).")
        elif resp.get('type') == 'fallback':
            # If fallback contains a plain text 'text', save a raw blob
            text = resp.get('text') or resp.get('data') or "No plan returned"
            WorkoutPlan.objects.create(member=profile, title='AI Plan (fallback)', content=text)
            DietPlan.objects.create(member=profile, title='AI Diet (fallback)', content='Refer to AI Plan')
            messages.warning(request, "AI JSON unavailable — saved fallback plan text.")
        else:
            # Unknown response shape
            WorkoutPlan.objects.create(member=profile, title='AI Plan (unknown)', content=str(resp))
            messages.warning(request, "AI returned unexpected format — saved raw response.")
    except Exception as e:
        # If saving/parsing failed, store raw text so user still gets something
        try:
            raw_text = resp.get('text') if isinstance(resp, dict) else str(resp)
            WorkoutPlan.objects.create(member=profile, title='AI Plan (error)', content=raw_text)
            DietPlan.objects.create(member=profile, title='AI Diet (error)', content='Refer to AI Plan (error)')
        except Exception:
            pass
        messages.error(request, f"Failed to parse/save AI plan: {str(e)}")

    return redirect('dashboard')

@require_POST
@login_required
def upload_progress_photo(request):
    profile = request.user.memberprofile
    form = ProgressPhotoForm(request.POST, request.FILES)

    if form.is_valid():
        photo = form.save(commit=False)
        photo.member = profile
        photo.save()
        messages.success(request, "Progress photo uploaded successfully.")

        # If using AJAX, return JSON
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "ok": True,
                "message": "Photo uploaded.",
                "photo_id": photo.id,
                "created_at": photo.created_at.isoformat(),
            })

        # Normal form submission fallback
        return redirect("dashboard")

    # Form invalid
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": False,
            "errors": form.errors,
        }, status=400)

    messages.error(request, "Failed to upload photo. Please check the form.")
    return redirect("dashboard")


@login_required
def progress_data(request):
    profile = request.user.memberprofile
    data = list(profile.progress.order_by('date').values('date','weight_kg'))
    return JsonResponse(data, safe=False)
