"""Quick standalone script to verify the WhatsApp alert messaging pipeline actually sends.

Prerequisites (see nodis_app/whatsapp_web.py docstring):
    1. Firefox running with -marionette -profile <dedicated profile>, logged into
       web.whatsapp.com in an open tab.
    2. geckodriver running: geckodriver --marionette-port 2828 --connect-existing --port 4444

Usage:
    python test_whatsapp.py                 # sends to settings.WHATSAPP_TARGET_NUMBER
    python test_whatsapp.py +9779800000000  # sends to an explicit number
"""
import os
import sys
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "NoDis.settings")
django.setup()

from nodis_app.whatsapp_web import send_whatsapp_message  # noqa: E402


def main() -> None:
    phone = sys.argv[1] if len(sys.argv) > 1 else None
    text = f"\u2705 AllDash test message - messaging system check at {time.strftime('%Y-%m-%d %H:%M:%S')}"
    print(f"Sending test WhatsApp message{f' to {phone}' if phone else ' to the default number'}...")
    ok = send_whatsapp_message(text, phone_number=phone)
    if ok:
        print("SUCCESS: send_whatsapp_message() reported the message was delivered.")
    else:
        print("FAILED: send_whatsapp_message() returned False - check the logged warning/exception above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
