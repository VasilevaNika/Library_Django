from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import date
from django.db.models import Count, Q

class Author(models.Model):
    name = models.CharField(max_length=100, verbose_name="Имя автора")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Автор"
        verbose_name_plural = "Авторы"

class Genre(models.Model):
    name = models.CharField(max_length=50, verbose_name="Название жанра")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey('Author', on_delete=models.CASCADE)
    genres = models.ManyToManyField('Genre')
    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to='covers/', blank=True, null=True)
    book_file = models.FileField(upload_to='books/', blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    favorited_by = models.ManyToManyField(
        User, 
        related_name='favorite_books',
        blank=True,
        verbose_name="В избранном у"
    )
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "Книга"
        verbose_name_plural = "Книги"

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="Книга")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        verbose_name = "Избранная книга"
        verbose_name_plural = "Избранные книги"
        unique_together = ('user', 'book')

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Номер телефона должен быть в формате: '+999999999'. До 15 цифр."
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        verbose_name="Номер телефона", null=True,
    )
    
    email = models.EmailField(
        max_length=100,
        blank=True,
        verbose_name="Email", null=True,
    )
    
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата рождения"
    )
    
    bio = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="О себе", null=True,
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def age(self):
        """Вычисляет возраст пользователя"""
        if self.birth_date:
            today = date.today()
            age = today.year - self.birth_date.year
            if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
                age -= 1
            return age
        return None
    
    def __str__(self):
        return f'Профиль {self.user.username}'
    
    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"
    
    def get_recommended_books(self, limit=4):
        """Получить рекомендации на основе избранных книг пользователя"""
        favorite_books = self.user.favorite_books.all()
        
        if not favorite_books.exists():
            return Book.objects.annotate(
                favorite_count=Count('favorited_by')
            ).order_by('-favorite_count')[:limit]
        
        favorite_genres = set()
        for book in favorite_books:
            favorite_genres.update(book.genres.all())
        favorite_authors = set(book.author for book in favorite_books)
        
        recommended = Book.objects.filter(
            Q(genres__in=favorite_genres) | Q(author__in=favorite_authors)
        ).exclude(
            id__in=[book.id for book in favorite_books]
        ).distinct().annotate(
            match_score=Count('genres', filter=Q(genres__in=favorite_genres)) +
                       Count('author', filter=Q(author__in=favorite_authors))
        ).order_by('-match_score', '-id')[:limit]
        
        return recommended

class BookCopy(models.Model):
    STATUS_AVAILABLE    = 'available'
    STATUS_RESERVED     = 'reserved'
    STATUS_CHECKED_OUT  = 'checked_out'
    STATUS_READING_ROOM = 'reading_room'
    STATUS_LOST         = 'lost'

    STATUS_CHOICES = [
        (STATUS_AVAILABLE,    'Доступен'),
        (STATUS_RESERVED,     'Забронирован'),
        (STATUS_CHECKED_OUT,  'Выдан читателю'),
        (STATUS_READING_ROOM, 'Только читальный зал'),
        (STATUS_LOST,         'Утерян'),
    ]

    CONDITION_CHOICES = [
        ('good', 'Хорошее'),
        ('fair', 'Удовлетворительное'),
        ('poor', 'Плохое'),
    ]

    book             = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='copies', verbose_name='Книга')
    inventory_number = models.CharField(max_length=50, unique=True, verbose_name='Инвентарный номер')
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE, verbose_name='Статус')
    condition        = models.CharField(max_length=10, choices=CONDITION_CHOICES, default='good', verbose_name='Состояние')
    location         = models.CharField(max_length=100, blank=True, verbose_name='Расположение (полка/зал)')
    notes            = models.TextField(blank=True, verbose_name='Примечания')

    class Meta:
        verbose_name        = 'Экземпляр книги'
        verbose_name_plural = 'Экземпляры книг'
        ordering            = ['book', 'inventory_number']

    def __str__(self):
        return f'{self.book.title} [{self.inventory_number}]'


class Reservation(models.Model):
    STATUS_PENDING        = 'pending'
    STATUS_ACTIVE         = 'active'
    STATUS_RETURN_PENDING = 'return_pending'
    STATUS_COMPLETED      = 'completed'
    STATUS_CANCELLED      = 'cancelled'
    STATUS_EXPIRED        = 'expired'

    STATUS_CHOICES = [
        (STATUS_PENDING,        'Ожидает выдачи'),
        (STATUS_ACTIVE,         'На руках'),
        (STATUS_RETURN_PENDING, 'Ожидает подтверждения возврата'),
        (STATUS_COMPLETED,      'Возвращена'),
        (STATUS_CANCELLED,      'Отменена'),
        (STATUS_EXPIRED,        'Истекла'),
    ]

    LOAN_DAYS   = 14
    PICKUP_DAYS = 3

    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations', verbose_name='Пользователь')
    book           = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reservations', verbose_name='Книга')
    book_copy      = models.ForeignKey(BookCopy, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations', verbose_name='Экземпляр')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name='Статус')
    queue_position = models.PositiveIntegerField(null=True, blank=True, verbose_name='Позиция в очереди')

    reserved_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата бронирования')
    expires_at  = models.DateTimeField(verbose_name='Бронь действует до')
    due_date    = models.DateTimeField(null=True, blank=True, verbose_name='Вернуть до')
    returned_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата возврата')
    notes                  = models.TextField(blank=True, verbose_name='Примечания библиотекаря')
    warning                = models.TextField(blank=True, verbose_name='Предупреждение читателю')
    return_rejected_reason = models.TextField(blank=True, verbose_name='Причина отклонения возврата')

    class Meta:
        verbose_name        = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering            = ['-reserved_at']

    def __str__(self):
        return f'{self.user.username} — {self.book.title} [{self.get_status_display()}]'

    @property
    def is_queue(self):
        return self.queue_position is not None

    def save(self, *args, **kwargs):
        if not self.pk and not hasattr(self, '_expires_set'):
            from django.utils import timezone
            from datetime import timedelta
            if not self.expires_at:
                self.expires_at = timezone.now() + timedelta(days=self.PICKUP_DAYS)
        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        Profile.objects.create(user=instance)