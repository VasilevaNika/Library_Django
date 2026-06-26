from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.http import JsonResponse
from django.contrib.auth import login, logout
from django.contrib import messages
from .models import Book, Author, Genre, Favorite, Profile, BookCopy, Reservation
from .forms import BookReviewForm, ProfileUpdateForm, UserUpdateForm, BookCopyForm, ReturnConfirmForm, StaffBookForm
from .microservices_reviews_notifications import (
    build_review_saved_notification_message,
    create_review_saved_notification_via_service,
    create_review_via_service,
    fetch_book_reviews,
    format_service_error,
)
from .recommendations_client import fetch_new_books_from_recommendations_service

def health(request):
    return JsonResponse({"status": "ok"})


def home(request):
    genres = Genre.objects.all()
    total_books = Book.objects.count()

    api_new = fetch_new_books_from_recommendations_service(limit=6)
    orm_fallback = list(Book.objects.order_by("-id")[:6])
    latest_books = orm_fallback
    last_three_books = orm_fallback[:3]

    if api_new:
        api_ids = [b.pk for b in api_new if b.pk is not None]
        if api_ids:
            local_matched = list(Book.objects.filter(pk__in=api_ids))
            if local_matched:
                latest_books = local_matched
                last_three_books = local_matched[:3]
    
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
    
    favorite_book_ids = set()
    if request.user.is_authenticated:
        favorite_book_ids = set(
            Favorite.objects.filter(user=request.user).values_list('book_id', flat=True)
        )

    context = {
        'genres': genres,
        'latest_books': latest_books,
        'total_books': total_books,
        'last_three_books': last_three_books,
        'recommended_books': recommended_books,
        'user_favorite_genres': user_favorite_genres,
        'favorite_book_ids': favorite_book_ids,
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

    review_form = BookReviewForm() if request.user.is_authenticated else None
    reviews = fetch_book_reviews(book.id)

    # Physical availability
    copies = book.copies.all()
    available_count = copies.filter(status=BookCopy.STATUS_AVAILABLE).count()
    total_copies = copies.count()
    reading_room_only = total_copies > 0 and not copies.exclude(
        status=BookCopy.STATUS_READING_ROOM
    ).exists()

    user_reservation = None
    queue_length = Reservation.objects.filter(
        book=book,
        status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_ACTIVE],
        queue_position__isnull=False,
    ).count()
    if request.user.is_authenticated:
        user_reservation = Reservation.objects.filter(
            user=request.user,
            book=book,
            status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_ACTIVE],
        ).first()

    # Подтягиваем имена пользователей по user_id из отзывов
    from django.contrib.auth.models import User as AuthUser
    user_ids = {r["user_id"] for r in reviews if r.get("user_id")}
    users_map = {
        u.id: u.get_full_name() or u.username
        for u in AuthUser.objects.filter(id__in=user_ids)
    }
    for r in reviews:
        r["author_name"] = users_map.get(r.get("user_id"), "Читатель")

    return render(
        request,
        "library/book_detail.html",
        {
            "book": book,
            "is_favorite": is_favorite,
            "review_form": review_form,
            "reviews": reviews,
            "available_count": available_count,
            "total_copies": total_copies,
            "reading_room_only": reading_room_only,
            "user_reservation": user_reservation,
            "queue_length": queue_length,
        },
    )


@login_required
@require_POST
def submit_book_review(request, pk):
    book = get_object_or_404(Book, pk=pk)
    form = BookReviewForm(request.POST)
    if not form.is_valid():
        for errs in form.errors.values():
            for e in errs:
                messages.error(request, e)
        return redirect("book_detail", pk=pk)

    cd = form.cleaned_data
    code, body = create_review_via_service(
        user_id=request.user.id,
        book_id=book.id,
        title=cd["title"],
        content=cd.get("content") or "",
        is_published=bool(cd.get("is_published")),
    )
    if code != 201:
        messages.error(
            request,
            format_service_error(body) if body else "Не удалось создать отзыв (сервис отзывов).",
        )
        return redirect("book_detail", pk=pk)

    n_code, n_body = create_review_saved_notification_via_service(
        user_id=request.user.id,
        book_id=book.id,
        book_title=book.title,
        review_title=cd["title"],
    )
    fallback_text = build_review_saved_notification_message(book.title, cd["title"])
    if n_code == 201 and isinstance(n_body, dict):
        messages.success(
            request,
            n_body.get("message") or fallback_text,
        )
    else:
        messages.warning(
            request,
            "Отзыв создан, но микросервис уведомлений недоступен или вернул ошибку: "
            + (format_service_error(n_body) if n_body else "нет ответа"),
        )
    return redirect("book_detail", pk=pk)

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

    active_reservations = (
        Reservation.objects.filter(
            user=request.user,
            status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_ACTIVE],
        )
        .select_related("book", "book_copy")
        .order_by("-reserved_at")
    )

    context = {
        'favorite_books': favorite_books,
        'favorites_count': len(favorite_books),
        'profile': profile,
        'profile_age_days': days_on_site,
        'active_reservations': active_reservations,
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
@require_POST
def reserve_book(request, pk):
    from django.utils import timezone
    from datetime import timedelta
    from django.db import transaction

    book = get_object_or_404(Book, pk=pk)

    # Prevent duplicate active reservations for the same book
    existing = Reservation.objects.filter(
        user=request.user,
        book=book,
        status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_ACTIVE],
    ).first()
    if existing:
        messages.warning(request, "У вас уже есть активное бронирование этой книги.")
        return redirect("book_detail", pk=pk)

    with transaction.atomic():
        available_copy = (
            BookCopy.objects.filter(book=book, status=BookCopy.STATUS_AVAILABLE)
            .select_for_update()
            .first()
        )

        if available_copy:
            available_copy.status = BookCopy.STATUS_RESERVED
            available_copy.save()
            reservation = Reservation(
                user=request.user,
                book=book,
                book_copy=available_copy,
                status=Reservation.STATUS_PENDING,
                expires_at=timezone.now() + timedelta(days=Reservation.PICKUP_DAYS),
            )
            reservation._expires_set = True
            reservation.save()
            messages.success(
                request,
                f'Книга «{book.title}» забронирована. Заберите в библиотеке в течение {Reservation.PICKUP_DAYS} дней.',
            )
        else:
            queue_pos = (
                Reservation.objects.filter(
                    book=book,
                    status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_ACTIVE],
                    queue_position__isnull=False,
                ).count()
                + 1
            )
            reservation = Reservation(
                user=request.user,
                book=book,
                book_copy=None,
                status=Reservation.STATUS_PENDING,
                queue_position=queue_pos,
                expires_at=timezone.now() + timedelta(days=365),
            )
            reservation._expires_set = True
            reservation.save()
            messages.info(
                request,
                f'Все экземпляры «{book.title}» заняты. Вы добавлены в очередь (позиция {queue_pos}).',
            )

    return redirect("book_detail", pk=pk)


@login_required
@require_POST
def cancel_reservation(request, reservation_id):
    reservation = get_object_or_404(
        Reservation, id=reservation_id, user=request.user
    )

    if reservation.status not in [Reservation.STATUS_PENDING, Reservation.STATUS_ACTIVE]:
        messages.error(request, "Это бронирование нельзя отменить.")
        return redirect("my_reservations")

    # Free the copy if one was assigned and not yet issued
    if reservation.book_copy and reservation.status == Reservation.STATUS_PENDING:
        copy = reservation.book_copy
        copy.status = BookCopy.STATUS_AVAILABLE
        copy.save()

        # Promote the next person in queue, if any
        next_in_queue = (
            Reservation.objects.filter(
                book=reservation.book,
                status=Reservation.STATUS_PENDING,
                queue_position__isnull=False,
            )
            .order_by("queue_position")
            .first()
        )
        if next_in_queue:
            from django.utils import timezone
            from datetime import timedelta

            next_in_queue.book_copy = copy
            next_in_queue.queue_position = None
            next_in_queue.expires_at = timezone.now() + timedelta(days=Reservation.PICKUP_DAYS)
            next_in_queue.save()
            copy.status = BookCopy.STATUS_RESERVED
            copy.save()

    reservation.status = Reservation.STATUS_CANCELLED
    reservation.save()
    messages.success(request, "Бронирование отменено.")
    return redirect("my_reservations")


@login_required
def my_reservations(request):
    reservations = (
        Reservation.objects.filter(user=request.user)
        .select_related("book", "book_copy")
        .order_by("-reserved_at")
    )
    return render(request, "library/my_reservations.html", {"reservations": reservations})


@login_required
@require_POST
def pickup_book(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    if reservation.status != Reservation.STATUS_PENDING or reservation.queue_position is not None:
        messages.error(request, "Невозможно подтвердить получение этой книги.")
        return redirect("my_reservations")
    from django.utils import timezone
    from datetime import timedelta
    reservation.status = Reservation.STATUS_ACTIVE
    reservation.due_date = timezone.now() + timedelta(days=Reservation.LOAN_DAYS)
    reservation.save()
    messages.success(request, f'Отлично! Отметили, что вы забрали «{reservation.book.title}». Верните до {reservation.due_date.strftime("%d.%m.%Y")}.')
    return redirect("my_reservations")


@login_required
@require_POST
def return_book_request(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    if reservation.status != Reservation.STATUS_ACTIVE:
        messages.error(request, "Эту книгу нельзя отметить как возвращённую.")
        return redirect("my_reservations")
    reservation.status = Reservation.STATUS_RETURN_PENDING
    reservation.return_rejected_reason = ""
    reservation.save()
    messages.success(request, f'Спасибо! Возврат «{reservation.book.title}» отправлен на проверку сотруднику.')
    return redirect("my_reservations")


def staff_required(view_func):
    """Декоратор: только is_staff пользователи."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")
        if not request.user.is_staff:
            messages.error(request, "Доступ только для сотрудников библиотеки.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return wrapper


@staff_required
def staff_dashboard(request):
    pending = (
        Reservation.objects.filter(status=Reservation.STATUS_PENDING, queue_position__isnull=True)
        .select_related("user", "book", "book_copy")
        .order_by("reserved_at")
    )
    active = (
        Reservation.objects.filter(status=Reservation.STATUS_ACTIVE)
        .select_related("user", "book", "book_copy")
        .order_by("due_date")
    )
    return_pending = (
        Reservation.objects.filter(status=Reservation.STATUS_RETURN_PENDING)
        .select_related("user", "book", "book_copy")
        .order_by("reserved_at")
    )
    completed_recent = (
        Reservation.objects.filter(status=Reservation.STATUS_COMPLETED)
        .select_related("user", "book", "book_copy")
        .order_by("-returned_at")[:20]
    )
    queue = (
        Reservation.objects.filter(status=Reservation.STATUS_PENDING, queue_position__isnull=False)
        .select_related("user", "book")
        .order_by("book", "queue_position")
    )
    return render(request, "library/staff/dashboard.html", {
        "pending": pending,
        "active": active,
        "return_pending": return_pending,
        "completed_recent": completed_recent,
        "queue": queue,
    })


@staff_required
def staff_confirm_return(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if request.method == "POST":
        form = ReturnConfirmForm(request.POST)
        if form.is_valid():
            from django.utils import timezone
            from datetime import timedelta
            cd = form.cleaned_data
            action = request.POST.get("action", "confirm")

            if action == "reject":
                reason = cd.get("reject_reason") or "Причина не указана"
                reservation.status = Reservation.STATUS_ACTIVE
                reservation.return_rejected_reason = reason
                reservation.warning = ""
                reservation.save()
                messages.warning(request, f'Возврат «{reservation.book.title}» отклонён. Читатель уведомлён.')
                return redirect("staff_dashboard")

            # confirm or confirm_with_warning — free the copy
            if reservation.book_copy:
                reservation.book_copy.condition = cd["condition"]
                if cd["notes"]:
                    reservation.book_copy.notes = cd["notes"]
                reservation.book_copy.status = BookCopy.STATUS_AVAILABLE
                reservation.book_copy.save()
                next_in_queue = (
                    Reservation.objects.filter(
                        book=reservation.book,
                        status=Reservation.STATUS_PENDING,
                        queue_position__isnull=False,
                    ).order_by("queue_position").first()
                )
                if next_in_queue:
                    next_in_queue.book_copy = reservation.book_copy
                    next_in_queue.queue_position = None
                    next_in_queue.expires_at = timezone.now() + timedelta(days=Reservation.PICKUP_DAYS)
                    next_in_queue.save()
                    reservation.book_copy.status = BookCopy.STATUS_RESERVED
                    reservation.book_copy.save()

            reservation.status = Reservation.STATUS_COMPLETED
            reservation.returned_at = timezone.now()
            reservation.return_rejected_reason = ""
            if cd["notes"]:
                reservation.notes = (reservation.notes + "\n" + cd["notes"]).strip()
            if action == "confirm_with_warning":
                reservation.warning = cd.get("warning") or "Обратите внимание на состояние книги."
                messages.success(request, f'Возврат принят, читателю выставлено предупреждение.')
            else:
                reservation.warning = ""
                messages.success(request, f'Возврат «{reservation.book.title}» подтверждён.')
            reservation.save()
            return redirect("staff_dashboard")
    else:
        initial_condition = reservation.book_copy.condition if reservation.book_copy else "good"
        form = ReturnConfirmForm(initial={"condition": initial_condition})
    return render(request, "library/staff/confirm_return.html", {
        "reservation": reservation,
        "form": form,
    })


@staff_required
def staff_add_copy(request):
    if request.method == "POST":
        form = BookCopyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Экземпляр «{form.cleaned_data["inventory_number"]}» добавлен.')
            return redirect("staff_add_copy")
    else:
        initial = {}
        book_pk = request.GET.get("book")
        if book_pk:
            try:
                initial["book"] = Book.objects.get(pk=book_pk)
            except Book.DoesNotExist:
                pass
        form = BookCopyForm(initial=initial)
    recent_copies = BookCopy.objects.select_related("book").order_by("-id")[:15]
    return render(request, "library/staff/add_copy.html", {
        "form": form,
        "recent_copies": recent_copies,
    })


@staff_required
def staff_add_book(request):
    if request.method == "POST":
        form = StaffBookForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data

            # Resolve or create author
            author = cd.get("author")
            if not author:
                author, _ = Author.objects.get_or_create(
                    name=cd["new_author"].strip()
                )

            # Create the book
            book = Book(
                title=cd["title"],
                author=author,
                description=cd.get("description") or "",
            )
            if cd.get("cover"):
                book.cover = cd["cover"]
            if cd.get("book_file"):
                book.book_file = cd["book_file"]
            book.save()

            # Collect genres: existing + newly created
            selected_genres = list(cd.get("genres") or [])
            new_genres_raw = cd.get("new_genres", "")
            if new_genres_raw:
                for name in new_genres_raw.split(","):
                    name = name.strip()
                    if name:
                        genre, _ = Genre.objects.get_or_create(name=name)
                        selected_genres.append(genre)
            if selected_genres:
                book.genres.set(selected_genres)

            # Optionally create first copy
            copy = None
            if cd.get("add_copy") and cd.get("inventory_number"):
                copy = BookCopy.objects.create(
                    book=book,
                    inventory_number=cd["inventory_number"].strip(),
                    condition=cd.get("condition") or "good",
                    location=cd.get("location") or "",
                    status=BookCopy.STATUS_AVAILABLE,
                )

            msg = f'Книга «{book.title}» добавлена.'
            if copy:
                msg += f' Экземпляр {copy.inventory_number} создан.'
            messages.success(request, msg)
            return redirect("staff_add_book")
    else:
        form = StaffBookForm()

    recent_books = Book.objects.select_related("author").prefetch_related("copies").order_by("-id")[:10]
    return render(request, "library/staff/add_book.html", {
        "form": form,
        "recent_books": recent_books,
    })


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