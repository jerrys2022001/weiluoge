$out = "d:\GitHub\weiluoge\assets\images\stock-2026-03-extra20\stock-extra-05.jpg"
if (Test-Path $out) { Remove-Item $out -Force }

$picked = $null
$ids = @(1044,1045,1046,1047,1048,1049,1050,1060,1070,1080,1090,1100)

foreach ($id in $ids) {
  & curl.exe -L --max-time 20 "https://picsum.photos/id/$id/1920/1280" -o $out | Out-Null
  if ($LASTEXITCODE -ne 0) {
    if (Test-Path $out) { Remove-Item $out -Force }
    continue
  }

  $item = Get-Item $out -ErrorAction SilentlyContinue
  if ($null -eq $item -or $item.Length -lt 90000) {
    if (Test-Path $out) { Remove-Item $out -Force }
    continue
  }

  $picked = $id
  break
}

if ($null -eq $picked) {
  throw "failed_to_fill_05"
}

Write-Output "picked_id=$picked"
Get-Item $out | Select-Object Name,Length
