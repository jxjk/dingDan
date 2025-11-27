# 文件夹整理脚本

# 定义源目录和目标目录
$baseDir = "D:\Users\00596\Desktop\订单管理下发DNC"
$srcDir = "$baseDir\src"
$docsDir = "$baseDir\docs"

# 确保目标目录存在
New-Item -ItemType Directory -Path $srcDir -Force
New-Item -ItemType Directory -Path $docsDir -Force

# 定义要移动到src的目录
$dirsToMove = @("api", "config", "models", "services", "ui", "utils", "tests")

# 移动目录
foreach ($dir in $dirsToMove) {
    $sourcePath = "$baseDir\$dir"
    $destPath = "$srcDir\$dir"
    if (Test-Path $sourcePath) {
        Move-Item -Path $sourcePath -Destination $destPath -Force
        Write-Host "Moved directory: $dir"
    }
}

# 定义要移动到src的文件类型
$filesToMove = @("*.py", "*.yaml", "*.yml", "*.json", "*.cfg", "*.ini", "*.txt")

# 移动文件
foreach ($pattern in $filesToMove) {
    $items = Get-ChildItem -Path $baseDir -Filter $pattern
    foreach ($item in $items) {
        # 跳过已存在于docs目录的README.md
        if ($item.Name -ne "README.md") {
            Move-Item -Path $item.FullName -Destination $srcDir -Force
            Write-Host "Moved file: $($item.Name)"
        }
    }
}

# 确保README.md在根目录
$readmeSrc = "$srcDir\README.md"
$readmeDest = "$baseDir\README.md"
if (Test-Path $readmeSrc) {
    Move-Item -Path $readmeSrc -Destination $readmeDest -Force
    Write-Host "Moved README.md to root directory"
}

# 移动文档相关文件到docs目录
$docPatterns = @("*.md", "*.docx", "*.puml")
foreach ($pattern in $docPatterns) {
    $items = Get-ChildItem -Path $baseDir -Filter $pattern
    foreach ($item in $items) {
        Move-Item -Path $item.FullName -Destination $docsDir -Force
        Write-Host "Moved document: $($item.Name)"
    }
}

Write-Host "文件夹整理完成！"