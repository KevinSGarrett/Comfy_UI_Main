param(
  [Parameter(Mandatory=$true)][string]$VoiceName,
  [Parameter(Mandatory=$true)][string]$TextPath,
  [Parameter(Mandatory=$true)][string]$OutputPath,
  [Parameter(Mandatory=$true)][int]$Rate
)
Add-Type -AssemblyName System.Speech
$text = Get-Content -LiteralPath $TextPath -Raw
$s = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
  $s.SelectVoice($VoiceName)
  $s.Rate = $Rate
  $s.Volume = 100
  $format = [System.Speech.AudioFormat.SpeechAudioFormatInfo]::new(
    22050,
    [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
    [System.Speech.AudioFormat.AudioChannel]::Mono
  )
  $s.SetOutputToWaveFile($OutputPath, $format)
  [void]$s.Speak($text)
} finally {
  $s.Dispose()
}
