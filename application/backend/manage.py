#!/usr/bin/env python
"""Django command-line utility."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Khong import duoc Django. Ban da kich hoat venv va chay "
            "'pip install -r requirements.txt' chua?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
