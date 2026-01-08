from django import forms
from django.contrib.auth.models import User

class UserRegistrationForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'John Doe'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'name@techodrill.com'})
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        required=True
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        required=True
    )
    terms = forms.BooleanField(required=True)

    class Meta:
        model = User
        fields = ("email", "full_name")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        # Split full_name into first and last name if possible, or just use first_name
        name_parts = self.cleaned_data["full_name"].split(' ', 1)
        user.first_name = name_parts[0]
        if len(name_parts) > 1:
            user.last_name = name_parts[1]
        
        user.set_password(self.cleaned_data["password1"])
        
        if commit:
            user.save()
        return user
