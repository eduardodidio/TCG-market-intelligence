@echo off
REM ============================================================
REM  catalog-seed-fra.bat — Seed Scryfall catalog + scan FRA via MYP
REM  Run once after Reality Fracture (FRA) data is available on Scryfall
REM  Liga provider was removed in F210; uses MYP sweep for prices.
REM ============================================================

cd /d "%~dp0\.."

echo ============================================================
echo  TEDHC Catalog Seed - Reality Fracture (FRA) - %date% %time%
echo ============================================================

echo  [%time%] Step 1/3: Seeding Scryfall catalog (includes FRA, FRC, TFRA, TFRC)...
python -m src.cli.main catalog seed || echo  [WARN] catalog seed failed

echo  [%time%] Step 2/3: Scanning FRA prices via MYP...
python -m src.cli.main myp-sweep --set fra --delay 1.5 --batch-size 20 --batch-pause 30 || echo  [WARN] FRA MYP sweep failed

echo  [%time%] Step 3/3: Scanning FRC (Commander) prices via MYP...
python -m src.cli.main myp-sweep --set frc --delay 1.5 --batch-size 20 --batch-pause 30 || echo  [WARN] FRC MYP sweep failed

echo.
echo  [DONE] %date% %time%
echo  Note: TFRA and TFRC are token sets (no MYP prices expected).
echo ============================================================
