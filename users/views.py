from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, TopUpForm
from .models import Profile, Transaction

#View for registering
def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your account has been created! You can now log in.")
            return redirect('users:login')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

#View for user profile
@login_required(login_url='users:login')
def user(request):
    profile = request.user.profile
    transactions = Transaction.objects.all().filter(user=request.user).order_by('-created_at')
    return render(request, 'users/user.html', {
        'user': request.user,
        'balance': profile.balance,
        'transactions' : transactions,
    })

#View for the login page. Asks for username and password and checks them against profile
def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', reverse("users:user"))
            return HttpResponseRedirect(next_url)
        else:
            messages.error(request, "Invalid Credentials.")
    return render(request, "users/login.html")

#Lets Users Logout
def logout_view(request):
    logout(request)
    messages.success(request, "Successfully logged out.")
    return redirect('users:login')
import requests
from django.conf import settings

#View for the login page. Asks for username and password and checks them against profile. Verifies users with recaptcha
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        recaptcha_response = request.POST.get("recaptcha-token")  # Updated
        # Verify reCAPTCHA
        data = {
            'secret': settings.RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response,
            'remoteip': request.META.get('REMOTE_ADDR'),
        }
        recaptcha_verification = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data=data
        )
        result = recaptcha_verification.json()
        # Check reCAPTCHA response
        if not result.get("success"):
            messages.error(request, "reCAPTCHA validation failed. Please try again.")
            return redirect("users:login")  # Redirect back to the login page
        # Authenticate user if reCAPTCHA is valid
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect to the next URL if provided, else default to user profile
            next_url = request.GET.get('next', reverse("users:user"))  # Simplified fallback
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, "users/login.html")

#Stores the logged in users profile and allows it to be returned with a balance
def user_view(request):
    profile = request.user.profile  # Get the logged-in user's profile
    return render(request, 'users/user.html', {'balance': profile.balance})

#View for topping up the balance of a user profile and creates a transaction for that top_up
@login_required
def top_up_balance(request):
    Profile = request.user.profile
    form = TopUpForm(request.POST)
    if form.is_valid():
        amount = form.cleaned_data['amount']
        Profile.balance += amount
        Profile.save()
        Transaction.objects.create(user=request.user, amount=amount)
        messages.success(request, f"Your balance has been topped up by ${amount}.")
        return redirect('users:user')
    else:
        form = TopUpForm()
    return render(request, 'users/top_up.html', {'form': form, 'balance': Profile.balance})