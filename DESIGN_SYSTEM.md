# Дизайн-система «Между строк»

Онлайн-библиотека. Стиль: тёмный editorial, тёплый янтарный акцент, минимализм.

---

## Цвета

### Основная палитра

| Токен | HEX | Применение |
|---|---|---|
| `--c-primary` | `#E8811B` | Акцент, кнопки, иконки, подчёркивания |
| `--c-primary-dark` | `#C5661A` | Hover-состояние primary |
| `--c-primary-light` | `#F5A84D` | Лёгкие акценты |
| `--c-primary-subtle` | `rgba(232,129,27,0.12)` | Фоновые подсветки |

### Тёмные оттенки (navbar, hero, sidebar, карточки-заглушки)

| Токен | HEX | Применение |
|---|---|---|
| `--c-dark` | `#141414` | Navbar, hero-секция, card-header, тёмные блоки |
| `--c-dark-2` | `#1F1F1F` | Второй уровень тёмного фона |
| `--c-dark-3` | `#2C2C2C` | Разделители, границы на тёмном фоне |

### Светлые оттенки (основной контент)

| Токен | HEX | Применение |
|---|---|---|
| `--c-light` | `#FAFAF7` | Фон страницы |
| `--c-light-2` | `#F2EDE4` | Фон второстепенных секций, card-header-light |
| `--c-light-3` | `#E5DDD0` | Границы карточек, разделители |

### Текст

| Токен | HEX | Применение |
|---|---|---|
| `--c-text` | `#1A1A1A` | Основной текст на светлом фоне |
| `--c-text-inv` | `#F5F5F0` | Текст на тёмном фоне |
| `--c-text-muted` | `#787870` | Второстепенный текст на светлом |
| `--c-text-muted-inv` | `#A8A89E` | Второстепенный текст на тёмном |

### Статусные цвета

| Токен | HEX | Применение |
|---|---|---|
| `--c-success` | `#2D7A4F` | Успех, зелёные badge |
| `--c-danger` | `#C53030` | Ошибка, удаление, избранное (filled) |
| `--c-info` | `#2B6CB0` | Информация |

---

## Типографика

**Шрифт:** Inter (Google Fonts)  
**Подключение:** `https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap`  
**Fallback:** `-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`

### Размеры и веса

| Элемент | Размер | Вес | Примечания |
|---|---|---|---|
| Hero-заголовок | `clamp(2rem, 5vw, 3.2rem)` | 900 | letter-spacing: -0.04em |
| Section title | `1.6rem` | 800 | letter-spacing: -0.03em |
| Card title | `0.92rem` | 700 | line-height: 1.35 |
| Навигация | `0.88rem` | 500 | letter-spacing: 0.01em |
| Основной текст | `0.95rem` | 400 | line-height: 1.65 |
| Мелкий текст | `0.8rem` | 400 | — |
| Badge | `0.72rem` | 600 | text-transform: uppercase, letter-spacing: 0.03em |
| Статистика (число) | `2.8rem` | 900 | letter-spacing: -0.05em |

### Специальные классы

```css
/* Заголовок секции с оранжевой чертой снизу */
.section-title { font-size: 1.6rem; font-weight: 800; letter-spacing: -0.03em; }
.section-divider { display: block; width: 2.5rem; height: 3px; background: #E8811B; margin-top: 0.6rem; }

/* Большое число (статистика) */
.stat-number { font-size: 2.8rem; font-weight: 900; color: #E8811B; letter-spacing: -0.05em; }
.stat-label  { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }
```

---

## Скругления

| Токен | Значение | Применение |
|---|---|---|
| `--radius-sm` | `6px` | Badge, мелкие элементы |
| `--radius-md` | `10px` | Inputs, alerts, мелкие карточки |
| `--radius-lg` | `16px` | Карточки книг, основные блоки |
| `--radius-xl` | `24px` | Hero-секция |
| `--radius-full` | `9999px` | Кнопки, nav-ссылки |

---

## Тени

| Токен | Значение | Применение |
|---|---|---|
| `--shadow-sm` | `0 1px 4px rgba(0,0,0,0.07)` | Карточки в покое |
| `--shadow-md` | `0 4px 16px rgba(0,0,0,0.10)` | Модалки, прилипшие элементы |
| `--shadow-lg` | `0 10px 36px rgba(0,0,0,0.14)` | Карточки при hover |
| `--shadow-primary` | `0 4px 20px rgba(232,129,27,0.28)` | Primary-кнопки |

---

## Компоненты

### Navbar
- Фон: `--c-dark` (`#141414`)
- Граница снизу: `1px solid --c-dark-3`
- Логотип: белый текст + слово «Между» в `--c-primary`
- Ссылки: `--c-text-muted-inv`, при hover — белые + `rgba(255,255,255,0.07)` фон
- CTA-кнопка (Регистрация / Выйти): заливка `--c-primary`, `border-radius: full`

### Кнопки
Все кнопки: `border-radius: 9999px`, `font-weight: 600`, без рамки, плавный transition.

| Вариант | Фон | Текст | Hover |
|---|---|---|---|
| `btn-primary` | `#E8811B` | белый | `#C5661A` + translateY(-1px) |
| `btn-outline-primary` | прозрачный | `#E8811B` | заливка `#E8811B`, текст белый |
| `btn-dark` | `#141414` | белый | `#1F1F1F` + translateY(-1px) |
| `btn-outline-secondary` | прозрачный | `--c-text-muted` | фон `--c-light-2` |
| `btn-danger` | `#C53030` | белый | `#A12626` |
| `btn-outline-danger` | прозрачный | `#C53030` | заливка `#C53030` |
| `btn-success` | `#2D7A4F` | белый | `#245F3E` |

Размеры:
- `btn-lg`: padding `0.75rem 2rem`, font-size `1rem`
- default: padding `0.5rem 1.25rem`
- `btn-sm`: padding `0.32rem 0.85rem`, font-size `0.8rem`

### Карточки
```css
border-radius: 16px;
border: 1px solid #E5DDD0;
background: #fff;
box-shadow: 0 1px 4px rgba(0,0,0,0.07);
transition: box-shadow 0.22s, transform 0.22s;
overflow: hidden;

/* hover */
box-shadow: 0 10px 36px rgba(0,0,0,0.14);
transform: translateY(-3px);
```

**card-header** (тёмный, по умолчанию):
- Фон: `#141414`, текст: `#F5F5F0`, font-weight: 700

**card-header-light** (светлый вариант):
- Фон: `#F2EDE4`, текст: `#1A1A1A`

### Карточка книги
```
┌─────────────────────┐
│   Обложка (240px)   │  ← тёмный фон-заглушка #1F1F1F если нет обложки
│         [♥]         │  ← кнопка избранного (абсолютная, top-right, 34px круг)
├─────────────────────┤
│ Badge Badge          │
│ Название книги       │  ← font-weight: 700, 0.92rem
│ Автор                │  ← color: --c-text-muted, 0.8rem
│ [  Подробнее  ]      │  ← btn-dark btn-sm w-100
└─────────────────────┘
```

Кнопка избранного на карточке:
- Позиция: `absolute`, top: 0.75rem, right: 0.75rem
- Размер: 34×34px, border-radius: 50%
- Фон: `rgba(255,255,255,0.92)`
- Иконка: `bi-heart` (пустое) / `bi-heart-fill text-danger` (добавлено)

### Поля ввода
```css
border: 1.5px solid #E5DDD0;
border-radius: 10px;
padding: 0.6rem 1rem;
font-size: 0.92rem;

/* focus */
border-color: #E8811B;
box-shadow: 0 0 0 3px rgba(232,129,27,0.14);
```

`input-group-text`: фон `#141414`, текст белый.

### Badge
```css
border-radius: 6px;
font-weight: 600;
font-size: 0.72rem;
padding: 0.32em 0.65em;
text-transform: uppercase;
letter-spacing: 0.03em;
```

Для жанров используется `bg-secondary` (`#E5DDD0` / тёмный текст) — нейтральный цвет, не конкурирует с акцентом.

### Аватар
```css
width/height: 96–120px;
border-radius: 50%;
background: #141414;
border: 3px solid #E8811B;
color: #E8811B; /* иконка внутри */
```

---

## Структура страниц

### Главная (home)
```
[HERO — тёмный блок на всю ширину]
  Лейбл (uppercase, primary) + H1 + описание + поиск | статистика

[row g-4]
  [col-lg-8]
    Новинки библиотеки   ← section-title + row карточек книг
    Рекомендации         ← section-title + row карточек / тёмный пустой блок
  [col-lg-4]  ← padding-top: 4.2rem (выравнивание по карточкам)
    Жанры (card, тёмный header, list-group)
    Статистика (card тёмный, stat-number)
    Предпочтения (если авторизован)
```

### Каталог (book_list)
```
[row g-4]
  [col-md-3]  Фильтры (sticky, тёмный header, list-group жанров)
  [col-md-9]
    Заголовок + счётчик + поиск
    row g-3 с карточками книг
```

### Страница книги (book_detail)
```
Breadcrumb
[row g-4]
  [col-md-4]  Обложка (sticky) + [Скачать][♥] + Назад
  [col-md-8]  Badge жанров + H1 + Автор + Описание + Форма отзыва
```

### Авторизация (login / register)
```
Центр страницы, col-lg-5/6
Иконка в тёмном квадрате (56px)
H1: "Войти Между строк" / "Присоединиться к Между строк"
card без border, shadow-lg, padding 2rem
```

### Профиль
```
Заголовок секции (section-title)
[row g-4]
  [col-md-4]  Аватар + Имя + @username + тёмный блок дней + btn-primary w-100 "Редактировать"
  [col-md-8]  Информация (card-header-light) + статистика (тёмный блок)
Избранные книги (section-title + горизонтальные карточки)
```

---

## Hero-секция

```css
background: #141414;
border-radius: 24px;
padding: 3.5rem 2.5rem;
position: relative;
overflow: hidden;

/* декоративный градиент справа */
position: absolute; right: 0; width: 40%;
background: linear-gradient(135deg, rgba(232,129,27,0.08), rgba(232,129,27,0.02));
clip-path: polygon(20% 0%, 100% 0%, 100% 100%, 0% 100%);
```

Лейбл над заголовком: `color: #E8811B`, `font-size: 0.8rem`, `font-weight: 700`, `letter-spacing: 0.12em`, `text-transform: uppercase`.

Поиск внутри hero: тёмный input (`background: #1F1F1F`, `border-color: #2C2C2C`, `color: #F5F5F0`), placeholder `rgba(255,255,255,0.4)`.

---

## Тёмные блоки (пустые состояния, статистика, подсказки)

Когда нужно показать пустое состояние или блок на тёмном фоне:
```css
background: #141414;
border-radius: 16px;
padding: 2–3rem;
text-align: center;
color: #F5F5F0;
```
Иконка сверху: `font-size: 2.5rem`, `color: #E8811B`.
Заголовок: `font-weight: 700`, белый.
Описание: `color: #A8A89E`, `font-size: 0.88rem`.
CTA: `btn-primary btn-sm`.

---

## Избранное — техническое

Избранное хранится в модели `Favorite(user, book)`. При проверке в шаблоне всегда использовать список ID, переданный из view:

```python
# в view
favorite_book_ids = set(
    Favorite.objects.filter(user=request.user).values_list('book_id', flat=True)
)
```

```django
{# в шаблоне #}
{% if book.id in favorite_book_ids %}
```

**Не использовать** `book in user.favorite_books.all` — это обращается к другому M2M полю (`favorited_by`), которое не синхронизировано с таблицей `Favorite`.

---

## Адаптивность

| Breakpoint | Изменения |
|---|---|
| `< 768px` | `section-title` → 1.3rem, `stat-number` → 2.2rem, `card-body` padding → 1.1rem, sticky sidebar → static |
| `< 992px` | sticky в ридере → static, padding ридера уменьшается |

---

## Чего избегать

- Градиентные кнопки и фоны (старый Bootstrap-стиль фиолетового/синего)
- `border-radius` меньше 6px на кнопках
- Синие/фиолетовые акценты (`#667eea`, `#764ba2`)
- `w-100` на кнопках вне карточки профиля — кнопки должны быть компактными
- Тени без тёплого оттенка
- Эмодзи в тексте интерфейса
