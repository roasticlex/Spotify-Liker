
import base64
import hashlib
import json
import secrets
import time
import urllib.parse
import urllib.request
import urllib.error
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import ctypes

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

CLIENT_ID = "390b9ea4e8964e769259306b2c1ac02b"
REDIRECT_URI = "http://127.0.0.1:8888/callback"

SCOPES = (
    "user-read-currently-playing "
    "user-library-read "
    "user-library-modify"
)

APP_DIR = Path.home() / "AppData" / "Roaming" / "SpotifyLike"
TOKEN_FILE = APP_DIR / "token.json"

API = "https://api.spotify.com/v1"
TOKEN_URL = "https://accounts.spotify.com/api/token"
AUTH_URL = "https://accounts.spotify.com/authorize"


# --------------------------------------------------
# WINDOWS NOTIFICATION
# --------------------------------------------------

def notify(message, title="Spotify"):
    ctypes.windll.user32.MessageBoxW(
        0, message, title, 0x40
    )


# --------------------------------------------------
# HTTP HELPERS
# --------------------------------------------------

def request(url, method="GET", data=None, headers=None):
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers or {},
        method=method
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        body = response.read()

        if not body:
            return None

        return json.loads(body.decode("utf-8"))


def token_request(data):
    encoded = urllib.parse.urlencode(data).encode()

    return request(
        TOKEN_URL,
        method="POST",
        data=encoded,
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )


# --------------------------------------------------
# TOKEN STORAGE
# --------------------------------------------------

def save_token(token):
    APP_DIR.mkdir(parents=True, exist_ok=True)

    token["expires_at"] = (
        time.time() + token.get("expires_in", 3600)
    )

    TOKEN_FILE.write_text(
        json.dumps(token, indent=2),
        encoding="utf-8"
    )


def load_token():
    if not TOKEN_FILE.exists():
        return None

    return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))


# --------------------------------------------------
# OAUTH PKCE
# --------------------------------------------------

def authorize():
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(24)

    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge
    }

    auth_url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    result = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)

            if parsed.path != "/callback":
                self.send_error(404)
                return

            if query.get("state", [""])[0] != state:
                result["error"] = "OAuth state mismatch."
            elif "error" in query:
                result["error"] = query["error"][0]
            else:
                result["code"] = query.get("code", [""])[0]

            message = (
                "Spotify authorization received. "
                "You can close this browser window."
            )

            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(message.encode())

        def log_message(self, *args):
            pass

    try:
        server = HTTPServer(
            ("127.0.0.1", 8888),
            CallbackHandler
        )
    except OSError:
        raise RuntimeError(
            "Cannot open port 8888. Is another application using it?"
        )

    server.timeout = 180

    webbrowser.open(auth_url)

    try:
        while not result:
            server.handle_request()

            if not result and server.timeout is None:
                break
    finally:
        server.server_close()

    if "error" in result:
        raise RuntimeError(result["error"])

    if not result.get("code"):
        raise RuntimeError("Spotify authorization timed out.")

    token = token_request({
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "code": result["code"],
        "redirect_uri": REDIRECT_URI,
        "code_verifier": verifier
    })

    save_token(token)
    return token


# --------------------------------------------------
# ACCESS TOKEN
# --------------------------------------------------

def get_access_token():
    token = load_token()

    if token is None:
        token = authorize()

    if time.time() >= token.get("expires_at", 0) - 60:
        refresh_token = token.get("refresh_token")

        if not refresh_token:
            token = authorize()
        else:
            refreshed = token_request({
                "client_id": CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            })

            if "refresh_token" not in refreshed:
                refreshed["refresh_token"] = refresh_token

            token = refreshed
            save_token(token)

    return token["access_token"]


# --------------------------------------------------
# SPOTIFY API
# --------------------------------------------------

def spotify_api(method, endpoint, token, params=None):
    url = API + endpoint

    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers = {
        "Authorization": "Bearer " + token
    }

    return request(
        url,
        method=method,
        headers=headers
    )


# --------------------------------------------------
# LIKE / UNLIKE CURRENT SONG
# --------------------------------------------------


def set_like(should_like):
    token = get_access_token()

    playing = spotify_api(
        "GET",
        "/me/player/currently-playing",
        token
    )

    if not playing or not playing.get("item"):
        raise RuntimeError("Nothing is currently playing.")

    track = playing["item"]

    if track.get("type") != "track":
        raise RuntimeError("The currently playing item is not a song.")

    uri = track["uri"]

    saved = spotify_api(
        "GET",
        "/me/library/contains",
        token,
        {"uris": uri}
    )

    is_saved = saved[0] if saved else False

    title = track.get("name", "Unknown track")
    artist = ", ".join(
        a["name"] for a in track.get("artists", [])
    )

    if should_like and is_saved:
        return f"Already liked: {title}\n{artist}"

    if not should_like and not is_saved:
        return f"Already unliked: {title}\n{artist}"

    action = "PUT" if should_like else "DELETE"

    spotify_api(
        action,
        "/me/library",
        token,
        {"uris": uri}
    )

    status = "Liked" if should_like else "Unliked"

    return f"{status}: {title}\n{artist}"


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    import sys    

    try:
        if len(sys.argv) < 2:
            raise RuntimeError("Missing action argument.")

        action = sys.argv[1].lower()

        if action == "like":
            #notify(set_like(True))
            set_like(True)
        elif action == "unlike":
            #notify(set_like(False))
            set_like(False)
        else:
            raise RuntimeError("Unknown action: " + action)

    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        notify(f"Spotify API error ({e.code}):\n{detail}", "Spotify Error")
    except Exception as e:
        notify(str(e), "Spotify Error")
