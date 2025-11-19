from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.urls import reverse
from .forms import UserRegistrationForm, MemberProfileForm, ProgressEntryForm, PaymentForm
from .models import MemberProfile, Payment, WorkoutPlan, DietPlan, ProgressEntry
from .ai_utils import generate_plans
from .ai_parser import save_parsed_plans
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import ProgressEntrySerializer
from .ai_utils import generate_plans
from .ai_json_parser import save_json_plan
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
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
    serializer = ProgressEntrySerializer(entries, many=True)
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
from .forms import MemberProfileForm, ProgressEntryForm
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
        form = ProgressEntryForm(request.POST)
        if form.is_valid():
            pe = form.save(commit=False)
            pe.member = profile
            pe.save()
            messages.success(request, "Progress entry added.")
            return redirect('dashboard')
    else:
        form = ProgressEntryForm()
    return render(request, 'main/add_progress.html', {'form': form})


@login_required
def dashboard(request):
    profile = request.user.memberprofile
    workouts = profile.workouts.order_by('-created_at')[:20]  # show more recent items
    diets = profile.diets.order_by('-created_at')[:5]
    progress = profile.progress.order_by('-date')[:20]
    # compute payment pending flag here (safe in view)
    payment_pending = profile.payments.filter(status='Pending').exists()
    return render(request, 'main/dashboard.html', {
        'profile': profile,
        'workouts': workouts,
        'diets': diets,
        'progress': progress,
        'payment_pending': payment_pending,
    })


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



@login_required
def progress_data(request):
    profile = request.user.memberprofile
    data = list(profile.progress.order_by('date').values('date','weight_kg'))
    return JsonResponse(data, safe=False)
