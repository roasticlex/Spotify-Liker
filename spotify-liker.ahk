#SingleInstance Force ;Skip instance prompt when reloading script
#Requires AutoHotkey >=2.0- <2.1 ;Bypasses version choice prompt on startup

; Like current song and play sound
^+l::
{
    ToggleSpotifyLike("like")
    SoundPlay(A_ScriptDir "\sounds\song-liked.wav")
}

; Unlike current song and play sound
^+u::
{ 
    ToggleSpotifyLike("unlike")
    SoundPlay(A_ScriptDir "\sounds\song-unliked.wav")
}

ToggleSpotifyLike(action) 
{
    script := A_ScriptDir "\spotify-liker.py"

    if !FileExist(script) 
    {
        MsgBox("Cannot find spotify-liker.py:`n" script,
            "Spotify", "Iconx")
        return
    }

    Run('pyw -3.15 "' script '" ' action, A_ScriptDir, "Hide")
}