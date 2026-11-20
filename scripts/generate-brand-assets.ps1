param(
    [string]$AppSource = "",
    [string]$DesktopSource = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $AppSource) {
    $AppSource = Join-Path $root "branding\source\sayo-sense-app-wordmark.png"
}
if (-not $DesktopSource) {
    $DesktopSource = Join-Path $root "branding\source\sayo-sense-desktop.png"
}
$AppSource = (Resolve-Path -LiteralPath $AppSource).Path
$DesktopSource = (Resolve-Path -LiteralPath $DesktopSource).Path

$background = [System.Drawing.Color]::FromArgb(255, 13, 4, 57)
$iconRoot = Join-Path $root "branding\icons"
$androidRes = Join-Path $root "mobile-app\android\app\src\main\res"
$iosIcon = Join-Path $root "mobile-app\ios\App\App\Assets.xcassets\AppIcon.appiconset"
$desktopBuild = Join-Path $root "desktop-app\build"
$desktopAssets = Join-Path $root "desktop-app\electron\assets"
$mobileStatic = Join-Path $root "mobile-app\src\static"
$desktopPublic = Join-Path $root "desktop-app\public"

function Ensure-Directory([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

function New-RoundedPath([System.Drawing.RectangleF]$rect, [float]$radius) {
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $diameter = [Math]::Min([Math]::Max($radius * 2, 1), [Math]::Min($rect.Width, $rect.Height))
    $arc = New-Object System.Drawing.RectangleF($rect.X, $rect.Y, $diameter, $diameter)
    $path.AddArc($arc, 180, 90)
    $arc.X = $rect.Right - $diameter
    $path.AddArc($arc, 270, 90)
    $arc.Y = $rect.Bottom - $diameter
    $path.AddArc($arc, 0, 90)
    $arc.X = $rect.X
    $path.AddArc($arc, 90, 90)
    $path.CloseFigure()
    return $path
}

function New-CleanBitmap(
    [string]$sourcePath,
    [int]$size,
    [double]$radiusRatio = 0.22,
    [double]$insetRatio = 0.03
) {
    $source = [System.Drawing.Image]::FromFile($sourcePath)
    $bitmap = New-Object System.Drawing.Bitmap($size, $size, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)

    try {
        $graphics.Clear($background)
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality

        $inset = [float]([Math]::Round($size * $insetRatio))
        $rect = New-Object System.Drawing.RectangleF(
            $inset,
            $inset,
            [float]($size - ($inset * 2)),
            [float]($size - ($inset * 2))
        )
        $path = New-RoundedPath $rect ([float]($rect.Width * $radiusRatio))

        try {
            $graphics.SetClip($path)
            $sourceInset = [float]($source.Width * 0.025)
            $sourceRect = New-Object System.Drawing.RectangleF(
                $sourceInset,
                $sourceInset,
                [float]($source.Width - ($sourceInset * 2)),
                [float]($source.Height - ($sourceInset * 2))
            )
            $graphics.DrawImage($source, $rect, $sourceRect, [System.Drawing.GraphicsUnit]::Pixel)
            $graphics.ResetClip()
        } finally {
            $path.Dispose()
        }
    } finally {
        $graphics.Dispose()
        $source.Dispose()
    }

    return $bitmap
}

function New-RoundBitmap([string]$sourcePath, [int]$size) {
    $base = New-CleanBitmap $sourcePath $size
    $round = New-Object System.Drawing.Bitmap($size, $size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($round)
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath

    try {
        $graphics.Clear([System.Drawing.Color]::Transparent)
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        $path.AddEllipse(0, 0, $size, $size)
        $graphics.SetClip($path)
        $graphics.DrawImageUnscaled($base, 0, 0)
        $graphics.ResetClip()
    } finally {
        $path.Dispose()
        $graphics.Dispose()
        $base.Dispose()
    }

    return $round
}

function New-AdaptiveForeground([string]$sourcePath, [int]$size) {
    $contentSize = [int]([Math]::Round($size * 0.78))
    $content = New-CleanBitmap $sourcePath $contentSize 0.22
    $bitmap = New-Object System.Drawing.Bitmap($size, $size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)

    try {
        $graphics.Clear($background)
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $offset = [int](($size - $contentSize) / 2)
        $graphics.DrawImageUnscaled($content, $offset, $offset)
    } finally {
        $graphics.Dispose()
        $content.Dispose()
    }

    return $bitmap
}

function Export-Png([System.Drawing.Bitmap]$bitmap, [string]$path) {
    Ensure-Directory (Split-Path -Parent $path)
    $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
}

function Get-PngBytes([System.Drawing.Bitmap]$bitmap) {
    $stream = New-Object System.IO.MemoryStream
    try {
        $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
        return [byte[]]$stream.ToArray()
    } finally {
        $stream.Dispose()
    }
}

function Export-Ico([string]$sourcePath, [string]$path, [int[]]$sizes) {
    $entries = @()
    foreach ($size in $sizes) {
        $bitmap = New-CleanBitmap $sourcePath $size 0.22
        try {
            $entries += [pscustomobject]@{
                Size = $size
                Bytes = Get-PngBytes $bitmap
            }
        } finally {
            $bitmap.Dispose()
        }
    }

    Ensure-Directory (Split-Path -Parent $path)
    $stream = [System.IO.File]::Open($path, [System.IO.FileMode]::Create)
    $writer = New-Object System.IO.BinaryWriter($stream)
    try {
        $writer.Write([uint16]0)
        $writer.Write([uint16]1)
        $writer.Write([uint16]$entries.Count)
        $offset = 6 + (16 * $entries.Count)

        foreach ($entry in $entries) {
            $dimension = if ($entry.Size -ge 256) { 0 } else { $entry.Size }
            $writer.Write([byte]$dimension)
            $writer.Write([byte]$dimension)
            $writer.Write([byte]0)
            $writer.Write([byte]0)
            $writer.Write([uint16]1)
            $writer.Write([uint16]32)
            $writer.Write([uint32]$entry.Bytes.Length)
            $writer.Write([uint32]$offset)
            $offset += $entry.Bytes.Length
        }

        foreach ($entry in $entries) {
            $writer.Write([byte[]]$entry.Bytes)
        }
    } finally {
        $writer.Dispose()
        $stream.Dispose()
    }
}

Ensure-Directory $iconRoot
Ensure-Directory (Join-Path $iconRoot "app")
Ensure-Directory (Join-Path $iconRoot "desktop")
Ensure-Directory (Join-Path $iconRoot "web")
Ensure-Directory $desktopBuild
Ensure-Directory $desktopAssets
Ensure-Directory $mobileStatic
Ensure-Directory $desktopPublic
Ensure-Directory $iosIcon

$appSizes = @(1024, 512, 192, 128)
foreach ($size in $appSizes) {
    $bitmap = New-CleanBitmap $AppSource $size 0.22
    try {
        Export-Png $bitmap (Join-Path $iconRoot ("app\app-icon-{0}.png" -f $size))
    } finally {
        $bitmap.Dispose()
    }
}

$desktopSizes = @(1024, 512, 192, 128)
foreach ($size in $desktopSizes) {
    $bitmap = New-CleanBitmap $DesktopSource $size 0.22
    try {
        Export-Png $bitmap (Join-Path $iconRoot ("desktop\desktop-icon-{0}.png" -f $size))
    } finally {
        $bitmap.Dispose()
    }
}

foreach ($size in @(16, 32, 64, 192)) {
    $bitmap = New-CleanBitmap $DesktopSource $size 0.22
    try {
        Export-Png $bitmap (Join-Path $iconRoot ("web\favicon-{0}.png" -f $size))
    } finally {
        $bitmap.Dispose()
    }
}

Export-Ico $DesktopSource (Join-Path $iconRoot "desktop\desktop-icon.ico") @(16, 24, 32, 48, 64, 128, 256)

$iosBitmap = New-CleanBitmap $AppSource 1024 0.22
try {
    Export-Png $iosBitmap (Join-Path $iosIcon "AppIcon-512@2x.png")
} finally {
    $iosBitmap.Dispose()
}

$androidDensities = @{
    "mdpi" = @(48, 108)
    "hdpi" = @(72, 162)
    "xhdpi" = @(96, 216)
    "xxhdpi" = @(144, 324)
    "xxxhdpi" = @(192, 432)
}

foreach ($density in $androidDensities.Keys) {
    $legacySize = $androidDensities[$density][0]
    $foregroundSize = $androidDensities[$density][1]
    $densityDir = Join-Path $androidRes ("mipmap-{0}" -f $density)
    Ensure-Directory $densityDir

    $legacy = New-CleanBitmap $DesktopSource $legacySize 0.22
    try {
        Export-Png $legacy (Join-Path $densityDir "ic_launcher.png")
    } finally {
        $legacy.Dispose()
    }

    $round = New-RoundBitmap $DesktopSource $legacySize
    try {
        Export-Png $round (Join-Path $densityDir "ic_launcher_round.png")
    } finally {
        $round.Dispose()
    }

    $foreground = New-AdaptiveForeground $DesktopSource $foregroundSize
    try {
        Export-Png $foreground (Join-Path $densityDir "ic_launcher_foreground.png")
    } finally {
        $foreground.Dispose()
    }
}

$desktop512 = New-CleanBitmap $DesktopSource 512 0.22
try {
    Export-Png $desktop512 (Join-Path $desktopBuild "icon.png")
} finally {
    $desktop512.Dispose()
}

Copy-Item -LiteralPath (Join-Path $iconRoot "desktop\desktop-icon.ico") -Destination (Join-Path $desktopBuild "icon.ico") -Force

$desktopRuntime = New-CleanBitmap $DesktopSource 256 0.22
try {
    Export-Png $desktopRuntime (Join-Path $desktopAssets "app-icon.png")
} finally {
    $desktopRuntime.Dispose()
}

$trayRuntime = New-CleanBitmap $DesktopSource 64 0.22
try {
    Export-Png $trayRuntime (Join-Path $desktopAssets "tray-icon.png")
} finally {
    $trayRuntime.Dispose()
}

Copy-Item -LiteralPath (Join-Path $iconRoot "web\favicon-64.png") -Destination (Join-Path $mobileStatic "favicon.png") -Force
Copy-Item -LiteralPath (Join-Path $iconRoot "web\favicon-64.png") -Destination (Join-Path $desktopPublic "favicon.png") -Force

Write-Host "Generated Sayo Sense icons:"
Write-Host "  Master/app: $iconRoot\app"
Write-Host "  Desktop:    $iconRoot\desktop"
Write-Host "  Web:        $iconRoot\web"
Write-Host "  Android:    $androidRes"
Write-Host "  iOS:        $iosIcon"
Write-Host "  Electron:   $desktopBuild and $desktopAssets"
