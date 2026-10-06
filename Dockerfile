# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY . .

# Создаем директорию для session файлов
RUN mkdir -p /app/sessions

# Запускаем бота (worker запускается отдельным сервисом через command)
CMD ["python", "bot.py"]
