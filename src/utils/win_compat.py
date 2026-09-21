#!/usr/bin/env python3
"""
win_compat.py - Windows Compatibility Layer for Quick Panel
Provides native Windows volume control and media session integration.
"""
import os
import sys

IS_WINDOWS = (os.name == 'nt' or sys.platform == 'win32')

# ── Windows Volume Control via Pycaw / CoreAudio ──────────────────
def get_windows_volume():
    if not IS_WINDOWS:
        return 50
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current_val = volume.GetMasterVolumeLevelScalar()
        return int(current_val * 100)
    except Exception:
        return 50

def set_windows_volume(vol_pct):
    if not IS_WINDOWS:
        return
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        target_val = max(0.0, min(1.0, float(vol_pct) / 100.0))
        volume.SetMasterVolumeLevelScalar(target_val, None)
    except Exception:
        pass

# ── Windows Media Session Control via Winsdk ─────────────────────
def get_windows_media_info():
    title, artist, art_path = "", "", ""
    if not IS_WINDOWS:
        return title, artist, art_path

    try:
        import asyncio
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager

        async def _async_get_media():
            manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
            session = manager.get_current_session()
            if session:
                info = await session.try_get_media_properties_async()
                t = info.title or ""
                a = info.artist or ""
                
                # Extract Thumbnail if available
                temp_art = os.path.join(os.environ.get("TEMP", "C:\\Windows\\Temp"), "win_osd_art.jpg")
                if info.thumbnail:
                    try:
                        stream = await info.thumbnail.open_read_async()
                        buffer = bytearray(stream.size)
                        await stream.read_async(buffer, stream.size, 0)
                        with open(temp_art, "wb") as f:
                            f.write(buffer)
                        return t, a, temp_art
                    except Exception:
                        pass
                return t, a, ""
            return "", "", ""

        loop = asyncio.new_event_loop()
        title, artist, art_path = loop.run_until_complete(_async_get_media())
        loop.close()
    except Exception:
        pass

    return title, artist, art_path

def run_windows_playerctl(cmd_name):
    if not IS_WINDOWS:
        return
    try:
        import asyncio
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager

        async def _async_control():
            manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
            session = manager.get_current_session()
            if session:
                if cmd_name == "previous":
                    await session.try_skip_previous_async()
                elif cmd_name == "next":
                    await session.try_skip_next_async()
                elif cmd_name == "play-pause":
                    await session.try_toggle_play_pause_async()

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_async_control())
        loop.close()
    except Exception:
        pass
