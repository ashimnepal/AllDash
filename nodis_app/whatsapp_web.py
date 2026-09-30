r"""Send WhatsApp messages through an already-logged-in WhatsApp Web tab in Firefox,
by attaching Selenium to your existing Firefox session instead of launching a new one.

One-time setup:
  1. Fully close all Firefox windows.
  2. Launch Firefox with Marionette enabled and a dedicated profile, e.g. in PowerShell:
       & "C:\Program Files\Mozilla Firefox\firefox.exe" -marionette -profile "C:\firefox-whatsapp-profile"
     (this starts the Marionette server on port 2828 by default)
  3. In that window, open https://web.whatsapp.com and scan the QR code once (the session
     persists in that profile folder from then on).
  4. In a separate terminal, start geckodriver in 'attach to existing browser' mode so
     Selenium never launches its own Firefox instance:
       geckodriver --marionette-port 2828 --connect-existing --port 4444
  5. Leave the Firefox window, the WhatsApp tab, and the geckodriver process all running.

Configure via .env: WHATSAPP_TARGET_NUMBER (who to message) and WHATSAPP_GECKODRIVER_ADDRESS
(geckodriver's own host:port from step 4, default 127.0.0.1:4444).
"""
import logging
import re
import time
import urllib.parse

from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

# WhatsApp Web's DOM/attribute names change across redesigns, so each of these tries a
# couple of known variants rather than betting on one exact selector.
MESSAGE_BOX_SELECTOR = "div[contenteditable='true'][data-tab], div[contenteditable='true'][aria-label='Type a message']"
SEND_BUTTON_SELECTOR = "button[aria-label='Send'], span[data-icon='send'], span[data-icon='wds-ic-send-filled']"
CONTINUE_TO_CHAT_XPATH = "//div[@role='button'][contains(., 'Continue to Chat')]"
WAIT_SECONDS = 20


def _attach_driver():
    return webdriver.Remote(
        command_executor=f"http://{settings.WHATSAPP_GECKODRIVER_ADDRESS}",
        options=FirefoxOptions(),
    )


def _find_whatsapp_tab(driver):
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "web.whatsapp.com" in driver.current_url:
            return True
    return False


def send_whatsapp_message(text, phone_number=None):
    """Send `text` via the open WhatsApp Web tab to `phone_number`, or settings.WHATSAPP_TARGET_NUMBER
    if no recipient-specific number is given (e.g. an alert with no AlertRecipient assigned).

    Returns True on success, False otherwise (Chrome not running with the debug port,
    no WhatsApp Web tab open, DOM/selectors changed, etc). Never raises - callers
    (price alert checks) must not crash if the browser feed is unavailable.
    """
    phone = re.sub(r"\D", "", phone_number or settings.WHATSAPP_TARGET_NUMBER or "")
    if not phone:
        logger.warning("No WhatsApp number configured; skipping WhatsApp alert: %s", text)
        return False

    try:
        driver = _attach_driver()
    except WebDriverException:
        logger.exception(
            "Could not attach to geckodriver at %s - is it running with --connect-existing?",
            settings.WHATSAPP_GECKODRIVER_ADDRESS,
        )
        return False

    try:
        if not _find_whatsapp_tab(driver):
            logger.warning("No open web.whatsapp.com tab found in the attached Firefox window")
            return False

        driver.get(f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(text)}")

        try:
            WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, CONTINUE_TO_CHAT_XPATH))
            ).click()
        except TimeoutException:
            pass  # chat opened directly, no confirmation dialog shown

        try:
            message_box = WebDriverWait(driver, WAIT_SECONDS).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, MESSAGE_BOX_SELECTOR))
            )
            message_box.send_keys(Keys.ENTER)
        except TimeoutException:
            # Compose box selector didn't match this WhatsApp Web version - fall back
            # to clicking the send icon/button directly.
            send_button = WebDriverWait(driver, WAIT_SECONDS).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, SEND_BUTTON_SELECTOR))
            )
            send_button.click()
        time.sleep(1)  # give WhatsApp a moment to actually dispatch the message
        return True
    except WebDriverException:
        logger.exception("Selenium failed to send the WhatsApp message")
        return False
    finally:
        # Ends this Marionette session so the next call can attach again - with
        # --connect-existing, geckodriver only allows one session at a time, and
        # quit() here does NOT close the actual Firefox window/tab.
        try:
            driver.quit()
        except WebDriverException:
            pass
