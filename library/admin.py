from django.contrib import admin
from .models import Author, Genre, Book, Favorite, BookCopy, Reservation

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_per_page = 20

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_per_page = 20

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'display_genres', 'has_book_file']
    list_filter = ['author', 'genres']
    search_fields = ['title', 'author__name']
    filter_horizontal = ['genres']
    list_per_page = 20
    
    fieldsets = [
        ('Основная информация', {
            'fields': ['title', 'author', 'description', 'cover']
        }),
        ('Файл книги', {
            'fields': ['book_file'],
            'description': 'Загрузите PDF файл с текстом книги'
        }),
        ('Жанры', {
            'fields': ['genres']
        }),
    ]
    
    def display_genres(self, obj):
        """Отображает жанры в списке книг"""
        return ", ".join([genre.name for genre in obj.genres.all()])
    display_genres.short_description = 'Жанры'
    
    def has_book_file(self, obj):
        """Показывает есть ли файл у книги"""
        return bool(obj.book_file)
    has_book_file.short_description = 'Есть файл'
    has_book_file.boolean = True

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'added_at']
    list_filter = ['added_at', 'user']
    search_fields = ['user__username', 'book__title']
    list_per_page = 20
    date_hierarchy = 'added_at'


class BookCopyInline(admin.TabularInline):
    model = BookCopy
    extra = 1
    fields = ['inventory_number', 'status', 'condition', 'location', 'notes']


@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display  = ['inventory_number', 'book', 'status', 'condition', 'location']
    list_filter   = ['status', 'condition']
    search_fields = ['inventory_number', 'book__title']
    list_per_page = 30
    list_editable = ['status', 'condition']
    autocomplete_fields = ['book']


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'book', 'book_copy', 'status', 'queue_position', 'reserved_at', 'expires_at', 'due_date']
    list_filter   = ['status', 'reserved_at']
    search_fields = ['user__username', 'book__title', 'book_copy__inventory_number']
    list_per_page = 30
    readonly_fields = ['reserved_at']
    list_editable = ['status']
    date_hierarchy = 'reserved_at'
    fieldsets = [
        ('Основное', {
            'fields': ['user', 'book', 'book_copy', 'status', 'queue_position']
        }),
        ('Даты', {
            'fields': ['reserved_at', 'expires_at', 'due_date', 'returned_at']
        }),
        ('Примечания', {
            'fields': ['notes']
        }),
    ]