param(
    [string]$AudioPath = "",
    [string]$Culture = "zh-CN",
    [int]$TimeoutSeconds = 45,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Speech

$recognizerInfo = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() |
    Where-Object { $_.Culture.Name -eq $Culture } |
    Select-Object -First 1
if (-not $recognizerInfo) {
    throw "NO_ZH_RECOGNIZER"
}

if ($CheckOnly) {
    try {
        $probe = New-Object System.Speech.Recognition.SpeechRecognitionEngine($recognizerInfo)
        $probe.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
        $probe.Dispose()
    }
    catch {
        @{
            available = $false
            engine = $recognizerInfo.Name
            culture = $recognizerInfo.Culture.Name
            error = $_.Exception.Message
        } | ConvertTo-Json -Compress
        exit 0
    }
    @{
        available = $true
        engine = $recognizerInfo.Name
        culture = $recognizerInfo.Culture.Name
    } | ConvertTo-Json -Compress
    exit 0
}

if ([string]::IsNullOrWhiteSpace($AudioPath)) {
    throw "AUDIO_PATH_REQUIRED"
}

$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($recognizerInfo)
try {
    $engine.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    $engine.SetInputToWaveFile($AudioPath)

    $segments = New-Object System.Collections.Generic.List[string]
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $result = $engine.Recognize()
        }
        catch [System.InvalidOperationException] {
            break
        }
        if ($null -eq $result) {
            break
        }
        if (-not [string]::IsNullOrWhiteSpace($result.Text)) {
            $segments.Add($result.Text.Trim())
        }
    }

    $payload = @{
        text = ($segments -join "")
        engine = $recognizerInfo.Name
        culture = $recognizerInfo.Culture.Name
    }
    $payload | ConvertTo-Json -Compress
}
finally {
    $engine.Dispose()
}
