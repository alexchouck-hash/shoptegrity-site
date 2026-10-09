# encode.ps1 - PowerShell encoder for The Loop animation
$ErrorActionPreference = "Stop"

if (-not (Test-Path "out")) {
    New-Item -ItemType Directory -Path "out" | Out-Null
}

# Ensure gifski and ffmpeg are in PATH
$gifskiPath = "C:\Program Files\gifski\gifski.exe"
$gifskiCmd = if (Test-Path $gifskiPath) { $gifskiPath } else { "gifski" }

# 1. GIF (gifski: best quality per byte)
Write-Host "Encoding GIF with gifski..."
$frames = Get-ChildItem -Path "frames\f_*.png" | Sort-Object Name | ForEach-Object { $_.FullName }
& $gifskiCmd --fps 20 --width 760 --quality 80 -o "out/loop.gif" $frames

# Check size
$gifSize = (Get-Item "out/loop.gif").Length
if ($gifSize -gt 10MB) {
    Write-Host "GIF size is $([math]::Round($gifSize / 1MB, 2)) MB (> 10MB). Re-encoding with --quality 65..."
    & $gifskiCmd --fps 20 --width 760 --quality 65 -o "out/loop.gif" $frames
    $gifSize = (Get-Item "out/loop.gif").Length
    if ($gifSize -gt 10MB) {
        Write-Host "Still over 10MB. Re-encoding with --fps 15..."
        & $gifskiCmd --fps 15 --width 760 --quality 65 -o "out/loop.gif" $frames
        $gifSize = (Get-Item "out/loop.gif").Length
        if ($gifSize -gt 10MB) {
            Write-Host "Still over 10MB. Re-encoding with --width 640..."
            & $gifskiCmd --fps 15 --width 640 --quality 65 -o "out/loop.gif" $frames
        }
    }
}

# 2. MP4 (H.264, universally playable)
Write-Host "Encoding MP4 with ffmpeg..."
& ffmpeg -y -framerate 20 -i "frames/f_%04d.png" -c:v libx264 -pix_fmt yuv420p -crf 20 -preset slow -movflags +faststart "out/loop.mp4"

# 3. WebM (VP9, smallest)
Write-Host "Encoding WebM with ffmpeg..."
& ffmpeg -y -framerate 20 -i "frames/f_%04d.png" -c:v libvpx-vp9 -pix_fmt yuv420p -crf 32 -b:v 0 "out/loop.webm"

# 4. Poster = final frame (also the reduced-motion still)
Write-Host "Generating poster..."
Copy-Item "frames/f_0479.png" -Destination "out/loop_poster.png"

Write-Host "`nDone! Generated assets in out/:"
Get-ChildItem "out" | Select-Object Name, @{Name="Size (KB)"; Expression={[math]::Round($_.Length / 1KB, 1)}}, @{Name="Size (MB)"; Expression={[math]::Round($_.Length / 1MB, 2)}}
