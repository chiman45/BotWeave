"""
BotSetu — Webhook Setup Automation
====================================
Starts ngrok, gets the public HTTPS URL, and sets it as the
Twilio webhook automatically — no manual console steps needed.

Usage:
    python setup_webhook.py

Requirements:
    pip install pyngrok
    ngrok must be installed: https://ngrok.com/download
    (or: pip install pyngrok  — pyngrok bundles ngrok automatically)

For the Twilio WhatsApp Sandbox, the script will print the URL
and open the Twilio console page where you paste it (one-time).
For real approved Twilio numbers it sets the webhook via API.
"""

import os
import sys
import time
import webbrowser
import subprocess
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID     = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN      = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', '')
PORT                   = int(os.getenv('PORT', 5000))

G   = "\033[92m"
R   = "\033[91m"
Y   = "\033[93m"
C   = "\033[96m"
W   = "\033[97m"
DIM = "\033[2m"
B   = "\033[1m"
RST = "\033[0m"

def ok(s):   print(f"  {G}✔{RST}  {s}")
def err(s):  print(f"  {R}✘{RST}  {s}")
def info(s): print(f"  {DIM}ℹ  {s}{RST}")
def sep():   print(f"  {DIM}{'─'*56}{RST}")
def ask(prompt, default=""):
    suffix = f" {DIM}[{default}]{RST}" if default else ""
    try:
        val = input(f"  {W}▶ {prompt}{suffix}: {RST}").strip()
    except (EOFError, KeyboardInterrupt):
        print(); return default
    return val if val else default


# ─────────────────────────────────────────────────────────────
# 1. Check pyngrok
# ─────────────────────────────────────────────────────────────
try:
    from pyngrok import ngrok, conf
    PYNGROK_OK = True
except ImportError:
    PYNGROK_OK = False


def _install_pyngrok():
    print(f"\n  {Y}pyngrok not found — installing…{RST}")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyngrok', '-q'])
    ok("pyngrok installed")
    # re-import
    from pyngrok import ngrok, conf
    return ngrok, conf


# ─────────────────────────────────────────────────────────────
# 2. Set Twilio webhook via API
# ─────────────────────────────────────────────────────────────
def _set_webhook_on_number(twilio_client, display_number: str, webhook_url: str) -> bool:
    """
    Try to update the webhook on a real (purchased) Twilio number.
    Returns True on success, False if the number isn't in the account.
    """
    try:
        numbers = twilio_client.incoming_phone_numbers.list(phone_number=display_number)
        if numbers:
            twilio_client.incoming_phone_numbers(numbers[0].sid).update(
                sms_url=webhook_url,
                sms_method='POST'
            )
            return True
    except Exception as e:
        info(f"API update attempt: {e}")
    return False


def _set_sandbox_webhook(twilio_client, webhook_url: str) -> bool:
    """
    Attempt to set the WhatsApp Sandbox inbound URL via Twilio REST API.
    Works for Twilio Flex / Messaging sandbox configurations.
    Returns True on success.
    """
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        # Twilio sandbox WhatsApp webhook endpoint
        url = (f"https://api.twilio.com/2010-04-01/Accounts/"
               f"{TWILIO_ACCOUNT_SID}/Sandbox.json")
        resp = requests.post(
            url,
            data={'WhatsAppWebhookStatusCallbackUrl': webhook_url,
                  'SmsUrl': webhook_url},
            auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=10
        )
        if resp.status_code in (200, 201):
            return True
        # Try the messaging sandbox resource
        url2 = (f"https://api.twilio.com/2010-04-01/Accounts/"
                f"{TWILIO_ACCOUNT_SID}/Messages/Sandbox.json")
        resp2 = requests.post(
            url2,
            data={'SmsUrl': webhook_url},
            auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=10
        )
        return resp2.status_code in (200, 201)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"\n{C}{B}  ╔══════════════════════════════════════════════╗")
    print(f"  ║     BotSetu — Webhook Setup Automation       ║")
    print(f"  ╚══════════════════════════════════════════════╝{RST}\n")

    display_number = TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', '')
    info(f"Twilio number : {display_number}")
    info(f"Flask port    : {PORT}")
    print()

    # ── Ensure Twilio is reachable ────────────────────────────
    try:
        from twilio.rest import Client as TwilioClient
        twilio = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        acct   = twilio.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        ok(f"Twilio connected — {acct.friendly_name}")
    except Exception as e:
        err(f"Twilio error: {e}")
        return

    # ── Ensure pyngrok is available ───────────────────────────
    if not PYNGROK_OK:
        try:
            ngrok, conf = _install_pyngrok()
        except Exception as e:
            err(f"Could not install pyngrok: {e}")
            err("Install manually:  pip install pyngrok")
            return
    else:
        from pyngrok import ngrok, conf

    # ── Optional: set ngrok auth token ───────────────────────
    ngrok_token = os.getenv('NGROK_AUTH_TOKEN', '')
    if not ngrok_token:
        print(f"\n  {Y}Tip{RST}: Set NGROK_AUTH_TOKEN in .env for a stable ngrok URL.")
        print(f"  Get your token at: {C}https://dashboard.ngrok.com/get-started/your-authtoken{RST}")
        ngrok_token = ask("Ngrok auth token (skip to use anonymous session)", "")
    if ngrok_token:
        ngrok.set_auth_token(ngrok_token)

    # ── Start ngrok tunnel ────────────────────────────────────
    sep()
    print(f"\n  Starting ngrok tunnel on port {PORT}…")
    try:
        tunnel = ngrok.connect(PORT, "http")
        public_url  = tunnel.public_url
        webhook_url = public_url.rstrip('/') + '/webhook/whatsapp'
        ok(f"ngrok tunnel active")
        print(f"\n  {B}Public URL   :{RST}  {C}{public_url}{RST}")
        print(f"  {B}Webhook URL  :{RST}  {G}{webhook_url}{RST}\n")
    except Exception as e:
        err(f"ngrok start failed: {e}")
        return

    # ── Set webhook on Twilio ─────────────────────────────────
    sep()
    print(f"\n  Setting Twilio webhook…\n")

    # Try real purchased number first
    set_ok = _set_webhook_on_number(twilio, display_number, webhook_url)

    if set_ok:
        ok(f"Webhook set on Twilio number {display_number}  ✓ Automatic")
    else:
        # Try sandbox API
        info("Number is a sandbox shared number — trying sandbox API…")
        sandbox_ok = _set_sandbox_webhook(twilio, webhook_url)
        if sandbox_ok:
            ok("Sandbox webhook updated via Twilio API  ✓ Automatic")
        else:
            # Manual fallback — open console and show URL
            print(f"\n  {Y}{B}  Action needed — paste the webhook URL in Twilio Console{RST}\n")
            print(f"  Webhook URL:\n\n      {G}{B}{webhook_url}{RST}\n")
            console_url = ("https://console.twilio.com/us1/develop/messaging/"
                           "try-it-out/whatsapp-learn")
            info(f"Opening Twilio sandbox settings: {console_url}")
            webbrowser.open(console_url)
            print(f"\n  In the console, set:")
            print(f"  {DIM}  WHEN A MESSAGE COMES IN  →  {webhook_url}  (HTTP POST){RST}\n")

    # ── Save URL to .env ──────────────────────────────────────
    sep()
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    try:
        with open(env_path, 'r') as f:
            env_content = f.read()

        if 'WEBHOOK_URL=' in env_content:
            lines = [
                f"WEBHOOK_URL={webhook_url}" if l.startswith('WEBHOOK_URL=') else l
                for l in env_content.splitlines()
            ]
            with open(env_path, 'w') as f:
                f.write('\n'.join(lines) + '\n')
        else:
            with open(env_path, 'a') as f:
                f.write(f"\n# Auto-set by setup_webhook.py\nWEBHOOK_URL={webhook_url}\n")
        ok(f"Saved WEBHOOK_URL to .env")
    except Exception as e:
        info(f"Could not update .env: {e}")

    # ── Keep running / start Flask ────────────────────────────
    sep()
    print()
    start_flask = ask("Start Flask server now? (y/N)", "y")
    if start_flask.lower() == 'y':
        print(f"\n  {G}Starting Flask on port {PORT}…{RST}\n")
        print(f"  {DIM}Press Ctrl+C to stop{RST}\n")
        sep()
        try:
            import app as flask_app
            flask_app.app.run(host='0.0.0.0', port=PORT, debug=False)
        except KeyboardInterrupt:
            print(f"\n\n  {Y}Server stopped.{RST}")
            ngrok.kill()
    else:
        print(f"\n  {DIM}ngrok is still running in the background.")
        print(f"  Start your server manually:  python app.py")
        print(f"  Webhook URL: {webhook_url}{RST}\n")
        print(f"  {DIM}Press Ctrl+C to stop ngrok…{RST}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            ngrok.kill()
            print(f"\n  {Y}ngrok stopped.{RST}\n")


if __name__ == '__main__':
    main()
