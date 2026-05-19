from django import forms
from django.contrib.auth.models import User
from .models import Profile, BookCopy, Book, Author, Genre


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


class StaffBookForm(forms.Form):
    title = forms.CharField(
        label='Название книги',
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название'}),
    )
    author = forms.ModelChoiceField(
        label='Автор',
        queryset=Author.objects.all().order_by('name'),
        required=False,
        empty_label='— Выбрать из списка —',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    new_author = forms.CharField(
        label='Или добавьте нового автора',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя автора (если нет в списке)'}),
    )
    genres = forms.ModelMultipleChoiceField(
        label='Жанры',
        queryset=Genre.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )
    description = forms.CharField(
        label='Описание',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Краткое описание книги...'}),
    )
    cover = forms.ImageField(
        label='Обложка',
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
    )
    book_file = forms.FileField(
        label='Файл книги (PDF, необязательно)',
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
    )
    # Первый экземпляр — необязательно
    add_copy = forms.BooleanField(
        label='Сразу добавить физический экземпляр',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'addCopyCheck'}),
    )
    new_genres = forms.CharField(
        label='Новые жанры',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Фантастика, Детектив (через запятую)',
        }),
    )
    inventory_number = forms.CharField(
        label='Инвентарный номер экземпляра',
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: 123'}),
    )
    condition = forms.ChoiceField(
        label='Состояние экземпляра',
        choices=BookCopy.CONDITION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    location = forms.CharField(
        label='Расположение',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Полка, зал...'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        author = cleaned_data.get('author')
        new_author = cleaned_data.get('new_author', '').strip()
        if not author and not new_author:
            self.add_error('new_author', 'Укажите автора: выберите из списка или введите имя нового.')
        if cleaned_data.get('add_copy') and not cleaned_data.get('inventory_number', '').strip():
            self.add_error('inventory_number', 'Укажите инвентарный номер для экземпляра.')
        return cleaned_data


class BookCopyForm(forms.ModelForm):
    book = forms.ModelChoiceField(
        queryset=Book.objects.all().order_by('title'),
        label='Книга',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    inventory_number = forms.CharField(
        label='Инвентарный номер',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: 123'}),
    )
    condition = forms.ChoiceField(
        label='Состояние',
        choices=BookCopy.CONDITION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    location = forms.CharField(
        label='Расположение (полка/зал)',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Полка A3, зал 1'}),
    )
    notes = forms.CharField(
        label='Примечания',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )

    class Meta:
        model = BookCopy
        fields = ['book', 'inventory_number', 'condition', 'location', 'notes']


class ReturnConfirmForm(forms.Form):
    condition = forms.ChoiceField(
        label='Состояние при возврате',
        choices=BookCopy.CONDITION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    notes = forms.CharField(
        label='Внутренние примечания',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                     'placeholder': 'Только для сотрудников...'}),
    )
    warning = forms.CharField(
        label='Предупреждение читателю',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                     'placeholder': 'Например: книга возвращена с повреждениями...'}),
    )
    reject_reason = forms.CharField(
        label='Причина отклонения',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                     'placeholder': 'Книга не была найдена на стойке возврата...'}),
    )