#!/usr/bin/env bash
# exit on error
set -o errexit

# Cài đặt các thư viện trong Pipfile
pip install pipenv
pipenv install

# Thu thập các file tĩnh (CSS, JS, Images)
python manage.py collectstatic --no-input

# Chạy cập nhật cấu trúc Database
python manage.py migrate
