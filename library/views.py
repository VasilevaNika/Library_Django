from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib import messages
from .models import Book, Author, Genre, Favorite

def home(request):
    """Главная страница"""
    latest_books = Book.objects.all().order_by('-id')[:6]
    genres = Genre.objects.all()
    return render(request, 'library/home.html', {
        'latest_books': latest_books,
        'genres': genres
    })

def book_list(request):
    """Страница каталога с поиском и фильтрами"""
    books = Book.objects.all()
    
    # Поиск
    query = request.GET.get('q')
    if query:
        books = books.filter(
            Q(title__icontains=query) | Q(author__name__icontains=query)
        )
    
    # Фильтрация по жанру
    genre_id = request.GET.get('genre')
    if genre_id:
        books = books.filter(genres__id=genre_id)
    
    # Фильтрация по автору
    author_id = request.GET.get('author')
    if author_id:
        books = books.filter(author__id=author_id)
    
    authors = Author.objects.all()
    genres = Genre.objects.all()
    
    return render(request, 'library/book_list.html', {
        'books': books,
        'genres': genres,
        'authors': authors,
    })

from django.shortcuts import render, get_object_or_404
from .models import Book

def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    return render(request, 'library/book_detail.html', {'book': book})

def read_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    
    if book.book_file:
        # Определяем тип файла по расширению
        file_extension = book.book_file.name.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            return render(request, 'library/read_book.html', {
                'book': book,
                'is_pdf': True
            })
        elif file_extension == 'txt':
            # Для текстовых файлов
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
    """Личный кабинет пользователя"""
    favorite_books = Book.objects.filter(favorited_by=request.user)
    return render(request, 'library/profile.html', {
        'favorite_books': favorite_books
    })

def register_view(request):
    """Регистрация пользователя"""
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
    """Вход пользователя"""
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
    """Выход пользователя"""
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('home')

@login_required
def toggle_favorite(request, book_id):
    """Добавление/удаление книги из избранного"""
    book = get_object_or_404(Book, id=book_id)
    
    # Проверяем, есть ли уже книга в избранном
    favorite_exists = Favorite.objects.filter(user=request.user, book=book).exists()
    
    if favorite_exists:
        # Удаляем из избранного
        Favorite.objects.filter(user=request.user, book=book).delete()
        messages.success(request, f'Книга "{book.title}" удалена из избранного')
    else:
        # Добавляем в избранное
        Favorite.objects.create(user=request.user, book=book)
        messages.success(request, f'Книга "{book.title}" добавлена в избранное')
    
    # Возвращаемся на предыдущую страницу
    return redirect(request.META.get('HTTP_REFERER', 'home'))






