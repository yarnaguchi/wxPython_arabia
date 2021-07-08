@echo off
if not exist ".\venv" (
  echo Python仮想環境を作成します
  python -m venv venv
  echo 必須パッケージをインストールします
  .\venv\Scripts\python.exe -m pip install -r requirements.txt
)

.\venv\Scripts\python.exe main.py