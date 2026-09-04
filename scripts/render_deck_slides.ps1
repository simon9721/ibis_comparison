<#
.SYNOPSIS
  Export every slide of a .pptx to PNG so a deck can be checked by eye.

.DESCRIPTION
  Geometry checks are not enough. Building this study's first deck, python-pptx
  reported no off-slide shapes and no overlaps, and the slides were still wrong:
  a paragraph ran underneath a rounded code box, code boxes centred their text so
  every monospaced table lost its column alignment, an annotation printed straight
  through a figure title, and one stale call rendered a table at 2.8 pt. None of
  that is visible from shape coordinates.

  This drives the installed PowerPoint through COM to export each slide as an
  image, so the deck can actually be looked at before it is sent. No install is
  needed beyond PowerPoint itself.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/render_deck_slides.ps1 `
      -Deck results/meeting_deck_2026-09-04/ibis_pybis_status_2026-09-04.pptx
#>
param(
  [Parameter(Mandatory = $true)][string]$Deck,
  [string]$Out = "",
  [int]$Width = 1600,
  [int]$Height = 900
)

$deckPath = (Resolve-Path $Deck).Path
if ($Out -eq "") { $Out = Join-Path (Split-Path $deckPath) "slides" }
if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Out | Out-Null

$ppt = New-Object -ComObject PowerPoint.Application
try {
  # ReadOnly, so a deck open elsewhere is not disturbed.
  $pres = $ppt.Presentations.Open($deckPath, $true, $false, $false)
  $i = 1
  foreach ($slide in $pres.Slides) {
    $slide.Export((Join-Path $Out ("slide{0:d2}.png" -f $i)), "PNG", $Width, $Height)
    $i++
  }
  $pres.Close()
  Write-Output ("exported {0} slides to {1}" -f ($i - 1), $Out)
} finally {
  $ppt.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
}
