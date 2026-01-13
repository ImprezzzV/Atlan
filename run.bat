@echo off
title Запуск двух узлов

echo Запускаю узел 1 (порт 5000)...
start "Node 5000" cmd /k python run.py 5000

echo Запускаю узел 2 (порт 5001)...
start "Node 5001" cmd /k python run.py 5001

pause
