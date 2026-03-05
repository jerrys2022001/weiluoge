$ErrorActionPreference = "Stop"

$dest = "d:\GitHub\weiluoge\assets\images\stock-2026-03-extra20"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Get-ChildItem "$dest\stock-extra-*.jpg" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem "$dest\test-*.jpg" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem "$dest\curl-test-*.jpg" -ErrorAction SilentlyContinue | Remove-Item -Force
Remove-Item "$dest\probe.jpg" -ErrorAction SilentlyContinue

$target = 20
$downloaded = New-Object System.Collections.Generic.List[object]

$ids = @(
  1015,1016,1018,1020,1021,1022,1024,1025,1027,1031,
  1033,1035,1036,1037,1038,1039,1040,1041,1042,1043,
  1044,1045,1047,1048,1049,1050,1051,1052,1053,1054,
  1055,1056,1057,1060,1062,1063,1065,1066,1067,1068,
  1069,1070,1071,1072,1073,1074,1076,1077,1078,1080
)

foreach ($id in $ids) {
  if ($downloaded.Count -ge $target) { break }

  $index = $downloaded.Count + 1
  $outfile = Join-Path $dest ("stock-extra-{0:D2}.jpg" -f $index)
  $url = "https://picsum.photos/id/$id/1920/1280"

  & curl.exe -L --max-time 20 $url -o $outfile | Out-Null
  if ($LASTEXITCODE -ne 0) {
    if (Test-Path $outfile) { Remove-Item $outfile -Force }
    continue
  }

  $item = Get-Item $outfile -ErrorAction SilentlyContinue
  if ($null -eq $item -or $item.Length -lt 90000) {
    if (Test-Path $outfile) { Remove-Item $outfile -Force }
    continue
  }

  $downloaded.Add([PSCustomObject]@{
    Index = $index
    Id = $id
    File = $item.Name
    Bytes = $item.Length
    Url = $url
  }) | Out-Null
}

$downloaded | Format-Table -AutoSize
Write-Output "downloaded_count=$($downloaded.Count)"

if ($downloaded.Count -lt $target) {
  throw "Only downloaded $($downloaded.Count) images."
}
