import os
import time
from instagrapi import Client
from dotenv import load_dotenv
import json
import http.cookiejar # Import http.cookiejar

# Load secrets and override existing environment variables
load_dotenv(override=True)

USERNAME = os.getenv("IG_USERNAME")
PASSWORD = os.getenv("IG_PASSWORD")
TOTP_SEED = os.getenv("IG_TOTP_SEED")
PROXY = os.getenv("IG_PROXY")  # Format: "http://user:pass@ip:port"

def convert_to_netscape_format(cookie_jar_from_requests):
    """
    Converts a http.cookiejar.CookieJar to Netscape format for yt-dlp.
    """
    lines = ["# Netscape HTTP Cookie File"]
    for cookie in cookie_jar_from_requests: # http.cookiejar.CookieJar is iterable
        # Filter for cookies relevant to instagram.com
        if "instagram.com" in cookie.domain:
            domain = cookie.domain
            flag = "TRUE" if cookie.domain_initial_dot else "FALSE"
            path = cookie.path
            secure = "TRUE" if cookie.secure else "FALSE"
            expiration = str(int(cookie.expires)) if cookie.expires else "0" 
            name = cookie.name
            value = cookie.value
            lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}")
    return "\n".join(lines)

def refresh_session() -> bool: # Added type hint for clarity
    # --- Pre-flight check for credentials ---
    if not all([USERNAME, PASSWORD, TOTP_SEED]):
        print("ERROR: Instagram credentials (IG_USERNAME, IG_PASSWORD, IG_TOTP_SEED) are not set in your environment. Cannot refresh session.")
        return False
        
    cl = Client()
    
    # 1. Set Proxy (CRITICAL for DigitalOcean)
    if PROXY:
        cl.set_proxy(PROXY)
        print(f"Proxy set: {PROXY.split('@')[-1]}")

    print("Attempting login...")
    
    try:
        # 2. Login with TOTP (Bypasses SMS/Email check)
        cl.login(USERNAME, PASSWORD, verification_code=cl.totp_generate_code(TOTP_SEED))
        print("Login Successful!")

        # 3. Dump Instagrapi Session (for internal use)
        # Using dump_settings which internally saves the session to session.json
        cl.dump_settings("session.json")
        print("session.json updated successfully!")
        
        # 4. Generate cookies.txt for yt-dlp using the live cookie jar
        netscape_content = convert_to_netscape_format(cl.cookie_jar)
        
        with open("instagram_cookies.txt", "w") as f:
            f.write(netscape_content)
            
        print("instagram_cookies.txt updated successfully!")
        return True # Indicate success
        
    except Exception as e:
        print(f"Login Failed: {e}")
        # Add Sentry logging here if you have it
        return False # Indicate failure

if __name__ == "__main__":
    refresh_session()
