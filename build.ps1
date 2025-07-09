$nltkDataPath = "C:\Users\eridani\AppData\Roaming\nltk_data"
$spacyModelPath = "S:\dev\python\stock.adobe_parser\.venv\Lib\site-packages\en_core_web_sm"

$mainScript = "main.py"

$addData = @(
    "C:\Users\eridani\.conda\envs\miniconda\Lib\site-packages\browserforge\fingerprints\data;browserforge\fingerprints\data",
    "C:\Users\eridani\.conda\envs\miniconda\Lib\site-packages\browserforge\headers\data;browserforge\headers\data",
    "C:\Users\eridani\.conda\envs\miniconda\Lib\site-packages\camoufox\browserforge.yml;camoufox",
    "C:\Users\eridani\.conda\envs\miniconda\Lib\site-packages\language_tags\data;language_tags\data",

    "$($nltkDataPath);nltk_data",
    "$($spacyModelPath);en_core_web_sm"
)

$collectAll = @(
    "camoufox",
    "browserforge",
    "language_tags",
    "playwright",
    "patchright",
    "nltk",
    "spacy"
)

$addDataArgs = $addData | ForEach-Object { "--add-data `"$($_)`"" }
$addDataArgsString = $addDataArgs -join " "

$collectAllArgs = $collectAll | ForEach-Object { "--collect-all `"$($_)`"" }
$collectAllArgsString = $collectAllArgs -join " "

$pyinstallerCommand = "pyinstaller --noconfirm --clean $addDataArgsString $collectAllArgsString `"$mainScript`""

Write-Host "Выполняется команда PyInstaller:"
Write-Host $pyinstallerCommand
Write-Host "---"

Invoke-Expression $pyinstallerCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host "---"
    Write-Host "Сборка завершена успешно!" -ForegroundColor Green
    Write-Host "Исполняемый файл(ы) должны находиться в папке 'dist'"
} else {
    Write-Host "---"
    Write-Host "Во время сборки произошла ошибка" -ForegroundColor Red
    Write-Host "Код выхода: $LASTEXITCODE"
}