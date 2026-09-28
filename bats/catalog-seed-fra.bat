@echo off
REM ============================================================
REM  catalog-seed-fra.bat — Seed Scryfall catalog + scan FRA via Liga
REM  Run once after Reality Fracture (FRA) data is available on Scryfall
REM ============================================================

cd /d "%~dp0\.."

echo ============================================================
echo  TEDHC Catalog Seed - Reality Fracture (FRA) - %date% %time%
echo ============================================================

echo  [%time%] Seeding Scryfall catalog (includes FRA, FRC, TFRA, TFRC)...
python -m src.cli.main catalog seed || echo  [WARN] catalog seed failed

echo  [%time%] Scanning FRA prices via Liga...
python -m src.cli.main catalog scan --set fra --delay 5 --batch-size 20 --batch-pause 60 || echo  [WARN] FRA scan failed

echo  [%time%] Scanning FRC (Commander) prices via Liga...
python -m src.cli.main catalog scan --set frc --delay 5 --batch-size 20 --batch-pause 60 || echo  [WARN] FRC scan failed

echo.
echo  [DONE] %date% %time%
echo  Note: TFRA and TFRC are token sets (no Liga prices expected).
echo ============================================================
