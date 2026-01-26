# Скрипт установки Yandex Cloud CLI для Windows
# Использование: .\install-yc-cli.ps1

Write-Host "Установка Yandex Cloud CLI..." -ForegroundColor Green

try {
    # Скачать и выполнить официальный скрипт установки
    iex (New-Object System.Net.WebClient).DownloadString('https://storage.yandexcloud.net/yandexcloud-yc/install.ps1')
    
    Write-Host "`nУстановка завершена!" -ForegroundColor Green
    Write-Host "Перезапустите терминал или выполните: refreshenv" -ForegroundColor Yellow
    Write-Host "Затем выполните: yc init" -ForegroundColor Yellow
}
catch {
    Write-Host "Ошибка при установке: $_" -ForegroundColor Red
    exit 1
}
