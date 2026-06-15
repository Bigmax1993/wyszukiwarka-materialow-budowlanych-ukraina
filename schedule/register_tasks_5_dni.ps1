# Rejestracja zadan Harmonogramu Windows (plan: piatek-nd-pon-wt).
# Uruchom PowerShell jako administrator.

param(
    [switch]$Unregister
)

$ScheduleDir = $PSScriptRoot
$Pwsh = (Get-Command powershell.exe).Source

function Register-WeekdayTask {
    param(
        [string]$Name,
        [string]$Script,
        [string]$Weekday,
        [string]$Time
    )
    $action = New-ScheduledTaskAction -Execute $Pwsh -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`""`
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Weekday -At $Time
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "OK: $Name -> $Weekday $Time"
}

$tasks = @(
    @{ Name = "Kanbud_GU_Sroda_Discovery"; Script = Join-Path $ScheduleDir "run_sroda_discovery.ps1"; Day = "Wednesday"; Time = "20:00" }
    @{ Name = "Kanbud_GU_Czwartek_Discovery"; Script = Join-Path $ScheduleDir "run_czwartek_discovery.ps1"; Day = "Thursday"; Time = "20:00" }
    @{ Name = "Kanbud_GU_Piatek_Discovery"; Script = Join-Path $ScheduleDir "run_piatek_discovery.ps1"; Day = "Friday"; Time = "17:00" }
    @{ Name = "Kanbud_GU_Niedziela_Backfill"; Script = Join-Path $ScheduleDir "run_czwartek.ps1"; Day = "Sunday"; Time = "06:00" }
    @{ Name = "Kanbud_GU_Poniedzialek_Prep"; Script = Join-Path $ScheduleDir "run_poniedzialek_prep.ps1"; Day = "Monday"; Time = "08:00" }
    @{ Name = "Kanbud_GU_Poniedzialek_Send"; Script = Join-Path $ScheduleDir "run_poniedzialek_send.ps1"; Day = "Monday"; Time = "07:00" }
    @{ Name = "Kanbud_GU_Wtorek_Send"; Script = Join-Path $ScheduleDir "run_wtorek.ps1"; Day = "Tuesday"; Time = "09:00" }
)

if ($Unregister) {
    foreach ($t in $tasks) {
        Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Usunieto: $($t.Name)"
    }
    foreach ($legacy in @(
            "Kanbud_GU_Sobota_Discovery",
            "Kanbud_GU_Sroda_Discovery",
            "Kanbud_GU_Czwartek_Backfill",
            "Kanbud_GU_Piatek_Send",
            "Kanbud_GU_Sroda_Send"
        )) {
        Unregister-ScheduledTask -TaskName $legacy -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Usunieto (legacy): $legacy"
    }
    exit 0
}

foreach ($t in $tasks) {
    Register-WeekdayTask -Name $t.Name -Script $t.Script -Weekday $t.Day -Time $t.Time
}

Write-Host "Gotowe. Sprawdz taskschd.msc (Kanbud_GU_*)"
Write-Host "Plan: sro-czw-pt discovery (20/20/17) | nd backfill | pon prep 8:00 + send 7:00 | wt send 9:00"
