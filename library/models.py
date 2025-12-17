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