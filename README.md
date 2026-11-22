# **Spotify Liker**
- This script will let you use a global shortcut (Ctrl+Shift+L) to like and (Ctrl+Shift+U) unlike songs globally (you could be inside a fullscreen game)
- Since it uses the official Spotify API with your account instead of hacky UI solutions this actually works :P
- Plays narrator sounds of liked or unliked vice versa

## **Instructions**
- **REQUIRES SPOTIFY PREMIUM** and also Python -> https://www.python.org/downloads/
- Copy spotify-liker.ahk and spotify-liker.py to your default AHK script folder
- Create a folder "sounds" in the script folder and copy song-liked.wav and song-unliked.wav into it
- Go to https://developer.spotify.com/dashboard and create an account, after that click create app. For redirect URI use: http://127.0.0.1:8888/callback and check Web API.
- A client ID will be generated for your app, put your client ID in the variable at the top of your spotify-liker.py
