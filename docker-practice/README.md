# Book Reviews Service

Микросервис для управления отзывами и рейтингами книг.

## Запуск с Docker (с live-reload)

```bash
# Сборка образа
docker build -t book-reviews-service .

# Запуск с bind mount для live-reload
docker run -p 8000:8000 -v $(pwd):/app book-reviews-service