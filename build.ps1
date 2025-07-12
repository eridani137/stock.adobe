# --- НАСТРОЙКА ПУТЕЙ ---

# Главный путь к папке 'site-packages' в вашем виртуальном окружении.
# Все остальные пути к библиотекам будут строиться от него.
$sitePackagesPath = "S:\dev\python\stock.adobe_parser\.venv\Lib\site-packages"

# Путь к данным NLTK (обычно он глобальный и находится в AppData, так что его можно оставить)
$nltkDataPath = "C:\Users\eridani\AppData\Roaming\nltk_data"

# Имя вашего основного Python-скрипта
$mainScript = "stock.adobe.py"


# --- СПИСКИ ДАННЫХ И БИБЛИОТЕК ---

# Источник: папка в вашем окружении. Назначение: папка внутри .exe файла.
$addData = @(
    "$($sitePackagesPath)\browserforge\fingerprints\data;browserforge\fingerprints\data",
    "$($sitePackagesPath)\browserforge\headers\data;browserforge\headers\data",
    "$($sitePackagesPath)\camoufox\browserforge.yml;camoufox",
    "$($sitePackagesPath)\language_tags\data;language_tags\data",
    "$($nltkDataPath);nltk_data",
    "$($sitePackagesPath)\en_core_web_sm;en_core_web_sm"
)

# Библиотеки, которые нужно собрать целиком
$collectAll = @(
    "camoufox",
    "browserforge",
    "language_tags",
    "playwright",
    "patchright",
    "nltk",
    "spacy"
)


# --- ФОРМИРОВАНИЕ И ВЫПОЛНЕНИЕ КОМАНДЫ ---

# Преобразуем массивы в строки аргументов для PyInstaller
$addDataArgs = $addData | ForEach-Object { "--add-data `"$($_)`"" }
$addDataArgsString = $addDataArgs -join " "

$collectAllArgs = $collectAll | ForEach-Object { "--collect-all `"$($_)`"" }
$collectAllArgsString = $collectAllArgs -join " "

# Собираем финальную команду
$pyinstallerCommand = "pyinstaller --noconfirm --clean $addDataArgsString $collectAllArgsString `"$mainScript`""

# Выводим команду в консоль для проверки
Write-Host "Выполняется команда PyInstaller:" -ForegroundColor Cyan
Write-Host $pyinstallerCommand
Write-Host "---"

# Запускаем сборку
Invoke-Expression $pyinstallerCommand


# --- ПРОВЕРКА РЕЗУЛЬТАТА ---

$distPath = $mainScript.Replace('.py', '')

if ($LASTEXITCODE -eq 0) {
    Write-Host "---"
    Write-Host "Сборка завершена успешно!" -ForegroundColor Green
    Write-Host "Исполняемый файл находится в папке 'dist\$distPath'"
} else {
    Write-Host "---"
    Write-Host "Во время сборки произошла ошибка" -ForegroundColor Red
    Write-Host "Код выхода: $LASTEXITCODE"
}