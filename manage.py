#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

FORCED_SETTINGS_MODULE = 'vms_backend.settings'


def enforce_settings_module():
    """Ensure we never boot with a stale DJANGO_SETTINGS_MODULE."""
    current_module = os.environ.get('DJANGO_SETTINGS_MODULE')
    if current_module and current_module != FORCED_SETTINGS_MODULE:
        instructions = (
            "Detected DJANGO_SETTINGS_MODULE set to "
            f"'{current_module}'. AuraVMS must run with "
            f"'{FORCED_SETTINGS_MODULE}'.\n\n"
            "Clear the variable before starting the server:\n"
            "  - PowerShell:  Remove-Item Env:DJANGO_SETTINGS_MODULE\n"
            "  - cmd.exe:     set DJANGO_SETTINGS_MODULE=\n"
            "  - bash/zsh:    unset DJANGO_SETTINGS_MODULE\n"
        )
        raise RuntimeError(instructions)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', FORCED_SETTINGS_MODULE)


def main():
    """Run administrative tasks."""
    enforce_settings_module()
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
