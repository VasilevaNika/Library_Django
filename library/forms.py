from django import forms
from django.contrib.auth.models import User
from .models import Profile


class BookReviewForm(forms.Form):
    """Отзыв для отправки в микросервис reviews (POST /reviews)."""

    title = forms.CharField(
        label="Заголовок отзыва",
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Краткий заголовок"}),
    )
    content = forms.CharField(
        label="Текст отзыва",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Ваши впечатления о книге (необязательно)",
            }
        ),
    )
    is_published = forms.BooleanField(
        label="Опубликовать отзыв",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш email'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Имя пользователя'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Имя'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Фамилия'
            }),
        }
        labels = {
            'username': 'Имя пользователя',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
        }

class ProfileUpdateForm(forms.ModelForm):
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 123-45-67'
        }),
        label='Номер телефона',
        max_length=17
    )
    
    birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Дата рождения'
    )
    
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Расскажите немного о себе...'
        }),
        label='О себе',
        max_length=500
    )
    
    class Meta:
        model = Profile
        fields = ['phone_number', 'birth_date', 'bio']
        labels = {
            'birth_date': 'Дата рождения',
            'bio': 'О себе',
        }