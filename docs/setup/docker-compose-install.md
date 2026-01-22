# Установка Docker и Docker Compose

Гайд по установке Docker и Docker Compose для разных операционных систем.

## Windows

### Вариант 1: Docker Desktop (Рекомендуется)

Docker Desktop для Windows включает Docker Engine, Docker CLI и Docker Compose.

1. **Скачать Docker Desktop:**
   - Перейти на https://www.docker.com/products/docker-desktop/
   - Скачать установщик для Windows

2. **Требования:**
   - Windows 10 64-bit: Pro, Enterprise, или Education (Build 15063 или выше)
   - Windows 11 64-bit: Home или Pro версия 21H2 или выше
   - WSL 2 (Windows Subsystem for Linux 2) должен быть включен
   - Виртуализация должна быть включена в BIOS

3. **Установка:**
   - Запустить установщик `Docker Desktop Installer.exe`
   - Следовать инструкциям мастера установки
   - После установки перезагрузить компьютер

4. **Проверка установки:**
   ```powershell
   docker --version
   docker-compose --version
   ```

5. **Запуск:**
   - Запустить Docker Desktop из меню Пуск
   - Дождаться полной загрузки (иконка в трее перестанет мигать)

### Вариант 2: Установка через WSL 2

Если предпочитаете использовать Docker в WSL 2:

1. **Установить WSL 2:**
   ```powershell
   wsl --install
   ```

2. **Установить Docker в WSL 2:**
   См. инструкции для Linux ниже (выбрать дистрибутив Ubuntu)

## Linux

### Ubuntu / Debian

1. **Обновить пакеты:**
   ```bash
   sudo apt-get update
   ```

2. **Установить зависимости:**
   ```bash
   sudo apt-get install \
       ca-certificates \
       curl \
       gnupg \
       lsb-release
   ```

3. **Добавить официальный GPG ключ Docker:**
   ```bash
   sudo mkdir -p /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   ```

4. **Настроить репозиторий:**
   ```bash
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   ```

5. **Установить Docker Engine и Docker Compose:**
   ```bash
   sudo apt-get update
   sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin
   ```

6. **Добавить пользователя в группу docker (чтобы не использовать sudo):**
   ```bash
   sudo usermod -aG docker $USER
   ```
   После этого нужно выйти и войти снова.

7. **Проверка установки:**
   ```bash
   docker --version
   docker compose version
   ```

### CentOS / RHEL / Fedora

1. **Установить зависимости:**
   ```bash
   sudo yum install -y yum-utils
   # или для Fedora:
   sudo dnf install -y dnf-plugins-core
   ```

2. **Добавить репозиторий Docker:**
   ```bash
   sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
   # или для Fedora:
   sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
   ```

3. **Установить Docker Engine и Docker Compose:**
   ```bash
   sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin
   # или для Fedora:
   sudo dnf install docker-ce docker-ce-cli containerd.io docker-compose-plugin
   ```

4. **Запустить Docker:**
   ```bash
   sudo systemctl start docker
   sudo systemctl enable docker
   ```

5. **Добавить пользователя в группу docker:**
   ```bash
   sudo usermod -aG docker $USER
   ```

6. **Проверка:**
   ```bash
   docker --version
   docker compose version
   ```

### Arch Linux

1. **Установить Docker:**
   ```bash
   sudo pacman -S docker docker-compose
   ```

2. **Запустить Docker:**
   ```bash
   sudo systemctl start docker
   sudo systemctl enable docker
   ```

3. **Добавить пользователя в группу docker:**
   ```bash
   sudo usermod -aG docker $USER
   ```

## macOS

### Вариант 1: Docker Desktop (Рекомендуется)

1. **Скачать Docker Desktop:**
   - Перейти на https://www.docker.com/products/docker-desktop/
   - Скачать установщик для Mac (Intel или Apple Silicon)

2. **Установка:**
   - Открыть скачанный `.dmg` файл
   - Перетащить Docker в папку Applications
   - Запустить Docker Desktop из Applications

3. **Проверка:**
   ```bash
   docker --version
   docker-compose --version
   ```

### Вариант 2: Установка через Homebrew

1. **Установить Homebrew (если еще не установлен):**
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Установить Docker и Docker Compose:**
   ```bash
   brew install --cask docker
   brew install docker-compose
   ```

3. **Запустить Docker Desktop:**
   - Открыть Docker Desktop из Applications

## Проверка установки

После установки проверьте, что все работает:

```bash
# Проверить версию Docker
docker --version

# Проверить версию Docker Compose
docker compose version
# или (старая версия):
docker-compose --version

# Проверить, что Docker работает
docker run hello-world
```

## Настройка Docker Compose

В новых версиях Docker (v2.0+) Docker Compose встроен как плагин и используется через команду `docker compose` (без дефиса).

Старая версия использует `docker-compose` (с дефисом).

Для совместимости в проекте используется `docker-compose.yml`, который работает с обеими версиями.

## Устранение проблем

### Windows: WSL 2 не установлен

```powershell
# Установить WSL 2
wsl --install

# Перезагрузить компьютер
```

### Linux: Проблемы с правами

Если получаете ошибку "permission denied":

```bash
# Добавить пользователя в группу docker
sudo usermod -aG docker $USER

# Выйти и войти снова, затем проверить:
docker ps
```

### macOS: Docker не запускается

1. Проверить, что Docker Desktop запущен (иконка в строке меню)
2. Перезапустить Docker Desktop
3. Проверить системные требования (минимум macOS 10.15)

### Общие проблемы

**Docker daemon не запущен:**
```bash
# Linux
sudo systemctl start docker

# macOS/Windows - запустить Docker Desktop
```

**Проблемы с сетью:**
- Проверить настройки файрвола
- Убедиться, что порты не заняты другими приложениями

## Дополнительные ресурсы

- Официальная документация Docker: https://docs.docker.com/
- Docker Compose документация: https://docs.docker.com/compose/
- Docker Desktop для Windows: https://docs.docker.com/desktop/install/windows-install/
- Docker Desktop для Mac: https://docs.docker.com/desktop/install/mac-install/
