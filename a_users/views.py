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
from .models import CreditClaim, Policy, Region
from django.http import JsonResponse
from management.models import SubscriptionBonus




from .models import Profile

@login_required
def load_regions(request):
    country_id = request.GET.get('country')
    regions = Region.objects.filter(country_id=country_id).order_by('name')
    data = [{'id': p.id, 'name': p.name} for p in regions]
    return JsonResponse({'regions': data})


def profile_view(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return redirect('account_login')

    onboarding = not profile.profile_is_filled
    print('onboarding', str(onboarding))
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            bonus = None
            code = form.cleaned_data.get('coupon_code', '').strip()
            # Validation du coupon si onboarding
            if onboarding and code:
                try:
                    bonus = SubscriptionBonus.objects.get(code__iexact=code)
                    if not bonus.is_valid():
                        form.add_error('coupon_code', 'Code coupon invalide ou expiré.')
                except SubscriptionBonus.DoesNotExist:
                    form.add_error('coupon_code', 'Code coupon invalide ou expiré.')

            if not form.errors:
                # Sauvegarde du profil
                profile = form.save()
                if onboarding:
                    profile.profile_is_filled = True
                    profile.save()
                    # Attribution des crédits bonus
                    if bonus:
                        profile.available_credits += bonus.credits
                        profile.save()
                        CreditClaim.objects.create(
                            profile=profile,
                            credits=bonus.credits,
                            subscription_bonus=bonus
                        )
                return redirect('home')
    else:
        form = ProfileForm(instance=profile)

    data_policy = Policy.objects.filter(name='Data Usage Policy').first().content
    context = {
        'form': form,
        'onboarding': onboarding,
        'profile': profile,
        'data_policy': data_policy
    }
    return render(request, 'a_users/profile_edit.html', context)


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
            daily_amount = 5
            if profile.current_plan and profile.current_plan.daily_credits:
                daily_amount = profile.current_plan.daily_credits
            profile.available_credits += daily_amount
            profile.has_claimed_credits = True
            profile.daily_credit_claim_date = local_today
            profile.save()
            # Enregistrer la traçabilité du claim
            CreditClaim.objects.create(profile=profile, credits=20)

        return redirect(request.META.get('HTTP_REFERER', '/'))
    return HttpResponseForbidden()