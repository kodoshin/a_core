from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from allauth.account.utils import send_email_confirmation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .forms import EmailForm, GithubKeyForm, ProfileForm
from a_projects.models import Project
from django.http import HttpResponseForbidden
import pytz
from django.utils import timezone
from .models import CreditClaim




from .models import Profile


def profile_view(request, username=None):
    if username:
        profile = get_object_or_404(User, username=username).profile
    else:
        try:
            profile = request.user.profile
        except:
            return redirect('account_login')
    return render(request, 'a_users/profile.html', {'profile':profile})


@login_required
def profile_settings_view(request):
    return render(request, 'a_users/profile_settings.html')


@login_required
def profile_githubkeychange(request):
    if request.htmx:
        print("HTMX Request Detected")
        form = GithubKeyForm(instance=request.user.profile)
        return render(request, 'partials/github_key_change.html', {'form': form})

    if request.method == 'POST':
        print(request.user.profile)
        form = GithubKeyForm(request.POST, instance=request.user.profile)

        if form.is_valid():
            form.save()

            # Then Signal updates emailaddress and set verified to False

            # Then send confirmation email
            send_email_confirmation(request, request.user)

            return redirect('profile-settings')
        else:
            messages.warning(request, 'Form not valid')
            return redirect('profile-settings')

    return redirect('home')


@login_required
def profile_emailchange(request):
    if request.htmx:
        form = EmailForm(instance=request.user)
        return render(request, 'partials/email_form.html', {'form': form})

    if request.method == 'POST':
        form = EmailForm(request.POST, instance=request.user)

        if form.is_valid():

            # Check if the email already exists
            email = form.cleaned_data['email']
            if User.objects.filter(email=email).exclude(id=request.user.id).exists():
                messages.warning(request, f'{email} is already in use.')
                return redirect('profile-settings')

            form.save()

            # Then Signal updates emailaddress and set verified to False

            # Then send confirmation email
            send_email_confirmation(request, request.user)

            return redirect('profile-settings')
        else:
            messages.warning(request, 'Form not valid')
            return redirect('profile-settings')

    return redirect('home')


@login_required
def profile_emailverify(request):
    send_email_confirmation(request, request.user)
    return redirect('profile-settings')


@login_required
def profile_delete_view(request):
    user = request.user
    if request.method == "POST":
        logout(request)
        user.delete()
        messages.success(request, 'Account deleted, what a pity')
        return redirect('home')

    return render(request, 'a_users/profile_delete.html')


@login_required
def user_projects_view(request):
    user = request.user
    projects = Project.objects.filter(user_id=user.id)
    return render(request, 'a_users/user_projects.html', {'projects': projects})


@login_required
def profile_view(request):
    profile = request.user.profile
    # Check if the profile is not completed (assuming 0 means not filled)
    onboarding = (profile.profile_is_filled == 0)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            # If this was the onboarding process, mark profile as complete
            if onboarding:
                profile.profile_is_filled = 1
                profile.save()
            return redirect('home')
    else:
        form = ProfileForm(instance=profile)

    try:
        profile = request.user.profile
    except:
        return redirect('account_login')

    context = {
        'form': form,
        'onboarding': onboarding,
        'profile': profile
    }

    return render(request, 'a_users/profile_edit.html', context)


def claim_credits_view(request):
    if request.method == 'POST':
        profile = request.user.profile

        # Determine user's timezone (fallback if not provided)
        try:
            user_tz = pytz.timezone(profile.timezone) if profile.timezone else timezone.get_current_timezone()
        except Exception:
            user_tz = timezone.get_current_timezone()

        # Get the current local date for the user
        local_today = timezone.now().astimezone(user_tz).date()

        # Reset the claimed flag if the stored claim date is not today
        if profile.daily_credit_claim_date != local_today:
            profile.has_claimed_credits = False

        if not profile.has_claimed_credits:
            profile.available_credits += 20
            profile.has_claimed_credits = True
            profile.daily_credit_claim_date = local_today
            profile.save()
            # Enregistrer la traçabilité du claim
            CreditClaim.objects.create(profile=profile, credits=20)

        return redirect(request.META.get('HTTP_REFERER', '/'))
    return HttpResponseForbidden()