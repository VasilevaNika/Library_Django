from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib import messages
from .models import Book, Author, Genre, Favorite, Profile
from .forms import ProfileUpdateForm, UserUpdateForm
from django.conf import settings

def home(request):
    genres = Genre.objects.all()
    latest_books = Book.objects.order_by('-id')[:6]
    total_books = Book.objects.count()
    last_three_books = Book.objects.order_by('-id')[:3]
    
    recommended_books = None
    user_favorite_genres = []
    
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            recommended_books = profile.get_recommended_books()
            
            favorite_books = request.user.favorite_books.all()
            for book in favorite_books:
                user_favorite_genres.extend(book.genres.all())
            user_favorite_genres = list(set(user_favorite_genres))
            
        except Profile.DoesNotExist:
            Profile.objects.create(user=request.user)
            recommended_books = Book.objects.order_by('-favorite_count')[:4]
    
    context = {
        'genres': genres,
        'latest_books': latest_books,
        'total_books': total_books,
        'last_three_books': last_three_books,
        'recommended_books': recommended_books,
        'user_favorite_genres': user_favorite_genres,
    }
    
    return render(request, 'library/home.html', context)

def book_list(request):
    books = Book.objects.all()
    
    query = request.GET.get('q')
    if query:
        books = books.filter(
            Q(title__icontains=query) | Q(author__name__icontains=query)
        )
    
    genre_id = request.GET.get('genre')
    if genre_id:
        books = books.filter(genres__id=genre_id)
    
    author_id = request.GET.get('author')
    if author_id:
        books = books.filter(author__id=author_id)
    
    authors = Author.objects.all()
    genres = Genre.objects.all()
    
    favorite_books = []
    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user)
        favorite_books = [fav.book.id for fav in favorites]
    
    return render(request, 'library/book_list.html', {
        'books': books,
        'genres': genres,
        'authors': authors,
        'favorite_books': favorite_books,
    })

def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, book=book).exists()
    
    return render(request, 'library/book_detail.html', {
        'book': book,
        'is_favorite': is_favorite
    })

def read_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    
    if book.book_file:
        file_extension = book.book_file.name.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            return render(request, 'library/read_book.html', {
                'book': book,
                'is_pdf': True
            })
        elif file_extension == 'txt':
            try:
                with open(book.book_file.path, 'r', encoding='utf-8') as file:
                    content = file.read()
                return render(request, 'library/read_book.html', {
                    'book': book,
                    'content': content
                })
            except:
                return render(request, 'library/read_book.html', {
                    'book': book,
                    'error': 'Ошибка чтения файла'
                })
        else:
            return render(request, 'library/read_book.html', {
                'book': book,
                'error': 'Формат файла не поддерживается для чтения онлайн'
            })
    else:
        return render(request, 'library/read_book.html', {
            'book': book,
            'error': 'Файл книги недоступен'
        })

@login_required
def profile(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('book')
    favorite_books = [favorite.book for favorite in favorites]
    
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    from django.utils import timezone
    from datetime import timedelta
    
    days_on_site = (timezone.now().date() - request.user.date_joined.date()).days

    context = {
        'favorite_books': favorite_books,
        'favorites_count': len(favorite_books),
        'profile': profile,
        'profile_age_days': days_on_site,
    }
    return render(request, 'library/profile.html', context)

@login_required
def edit_profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST, 
            request.FILES, 
            instance=profile
        )
        
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile_form.save()
            
            print(f"DEBUG: Email сохранен: {user.email}")
            
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile')
        else:
            print(f"DEBUG: Ошибки user_form: {user_form.errors}")
            print(f"DEBUG: Ошибки profile_form: {profile_form.errors}")
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    }
    return render(request, 'library/edit_profile.html', context)

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('home')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = UserCreationForm()
    return render(request, 'library/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('home')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')
    else:
        form = AuthenticationForm()
    return render(request, 'library/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('home')

@login_required
def toggle_favorite(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    favorite_exists = Favorite.objects.filter(user=request.user, book=book).exists()
    
    if favorite_exists:
        Favorite.objects.filter(user=request.user, book=book).delete()
        messages.success(request, f'Книга "{book.title}" удалена из избранного')
    else:
        Favorite.objects.create(user=request.user, book=book)
        messages.success(request, f'Книга "{book.title}" добавлена в избранное')
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))