#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SpeedTV Box — agente de TV Box, pensado para o Termux no celular.

No Termux, cole este bloco inteiro (ele acha o arquivo na pasta Download):

    f=$(find "$HOME/storage/downloads" "$HOME/storage/shared/Download" "$HOME/storage/shared/Downloads" -iname 'speedtvbox.py*' 2>/dev/null | head -n 1)
    cp "$f" "$HOME/speedtvbox.py"
    cd "$HOME"
    python speedtvbox.py

Na primeira vez, escolha 1. O agente lê, limpa e grava o relatório.
O celular e a TV Box na mesma rede. Nada é apagado do /system: o
debloat usa `pm disable-user`, reversível com a opção Desfazer ou com
o reset físico. A chave e o IP são gravados pela página na hora do download.
SPEEDTV_API_KEY e SPEEDTV_DEVICE substituem esses valores se existirem.
"""
from __future__ import annotations

import argparse
import json
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

DISPOSITIVO_PADRAO = "192.168.1.88:5555"
API_KEY_PADRAO = ""
MODELO = "gemini-3.8-flash"
MODELOS_RESERVA = ("gemini-3.8-flash", "gemini-4-hydrogen")
VERSAO = "9"

RAIZ = Path(__file__).resolve().parent
_DADOS = None

PKG_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")
CHAVE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_\.]{0,80}$")

# Nunca desativar. O reparo da Play Store pode reativar estes.
PROTECTED_EXACT = {
    "android",
    "com.android.systemui",
    "com.android.settings",
    "com.android.tv.settings",
    "com.android.providers.settings",
    "com.android.providers.media",
    "com.android.providers.media.module",
    "com.android.providers.downloads",
    "com.android.providers.downloads.ui",
    "com.android.externalstorage",
    "com.android.packageinstaller",
    "com.google.android.packageinstaller",
    "com.android.permissioncontroller",
    "com.google.android.permissioncontroller",
    "com.android.bluetooth",
    "com.android.shell",
    "com.android.inputmethod.latin",
    "com.google.android.inputmethod.latin",
    "com.android.webview",
    "com.google.android.webview",
    "com.google.android.trichromelibrary",
    "com.android.trichromelibrary",
    "com.android.vending",
    "com.google.android.gms",
    "com.google.android.gsf",
    "com.google.android.gsf.login",
    "com.google.android.partnersetup",
    "com.google.android.backuptransport",
    "com.google.android.configupdater",
    "com.google.android.ext.services",
    "com.google.android.ext.shared",
    "com.google.android.modulemetadata",
    "com.android.modulemetadata",
    "com.android.networkstack",
    "com.android.networkstack.tethering",
    "com.android.wifi.resources",
    "com.android.connectivity.resources",
    "com.android.phone",
    "com.android.server.telecom",
    "com.android.keychain",
    "com.android.location.fused",
    "com.android.providers.telephony",
    "com.android.se",
    "com.android.dynsystem",
    "com.android.rkpdapp",
    "com.google.android.tv.remote.service",
    "com.google.android.katniss",
    "com.google.android.apps.tv.launcherx",
    "com.google.android.tvlauncher",
    "com.google.android.leanbacklauncher",
    "com.google.android.tungsten.setupwraith",
    "com.google.android.setupwizard",
    "com.google.android.apps.mediashell",
    "com.android.providers.tv",
    "com.android.tv",
    "com.android.tv.frameworkpackagestubs",
    "com.android.captiveportallogin",
    "com.android.statementservice",
    "com.android.certinstaller",
    "com.android.vpndialogs",
    "com.android.proxyhandler",
    "com.android.managedprovisioning",
    "com.android.provision",
    "com.android.defcontainer",
    "com.android.storagemanager",
    "com.android.documentsui",
    "com.android.companiondevicemanager",
    "com.android.localtransport",
    "com.android.backupconfirm",
    "com.android.sharedstoragebackup",
    "com.android.providers.contacts",
    "com.android.wifi.dialog",
    "com.google.android.networkstack",
    "com.google.android.networkstack.tethering",
    "com.android.cts.priv.ctsshim",
    "com.android.cts.ctsshim",
}

PROTECTED_PREFIXES = (
    "com.google.android.gms.",
    "com.google.android.gsf.",
)

# Substring no nome. Overlay errado e HDMI derrubam a imagem.
DANGER_BITS = (
    "systemui",
    "tvinput",
    "hdmi",
    "livetv",
    "live_tv",
    "inputmethod",
    "setupwraith",
    "permissioncontroller",
    "packageinstaller",
    "networkstack",
    "webview",
    "trichrome",
    "keychain",
    "bluetooth",
    "wwtv",
    "droidtv",
    "launcherx",
    "tvlauncher",
    "leanbacklauncher",
    "mediashell",
    "katniss",
    ".overlay",
    "overlay.",
)

# Onda 1 — resto de telefone, telemetria e serviço que TV Box não usa.
WAVE1 = [
    "com.google.android.feedback",
    "com.android.printspooler",
    "com.android.bips",
    "com.google.android.printservice.recommendation",
    "com.android.bookmarkprovider",
    "com.android.providers.partnerbookmarks",
    "com.android.dreams.basic",
    "com.android.dreams.phototable",
    "com.android.wallpaperbackup",
    "com.android.egg",
    "com.android.traceur",
    "com.android.stk",
    "com.android.simappdialog",
    "com.android.carrierconfig",
    "com.android.carrierdefaultapp",
    "com.android.emergency",
    "com.google.android.apps.safetyhub",
    "com.android.cellbroadcastreceiver",
    "com.android.cellbroadcastreceiver.module",
    "com.google.android.cellbroadcastreceiver",
    "com.google.android.cellbroadcastservice",
    "com.google.android.ims",
    "com.android.mms",
    "com.android.mms.service",
    "com.android.hotspot2.osulogin",
    "com.android.nfc",
    "com.android.calllogbackup",
    "com.android.providers.blockednumber",
    "com.android.htmlviewer",
    "com.android.providers.userdictionary",
    "com.android.musicfx",
    "com.android.soundrecorder",
    "com.google.android.projection.gearhead",
    "com.android.wallpaper.livepicker",
]

# Onda 2 — pesados que não são o sistema de vídeo. Streaming (YouTube TV,
# Netflix, Prime, Globoplay, Disney) fica de fora de propósito.
WAVE2 = [
    "com.google.android.apps.maps",
    "com.google.android.apps.photos",
    "com.google.android.apps.docs",
    "com.google.android.apps.tachyon",
    "com.google.android.music",
    "com.google.android.videos",
    "com.google.android.youtube.tvmusic",
    "com.google.android.play.games",
    "com.google.android.apps.youtube.kids",
    "com.google.android.apps.magazines",
    "com.google.android.apps.books",
    "com.google.android.apps.podcasts",
    "com.google.android.apps.subscriptions.red",
    "com.google.android.apps.walletnfcrel",
    "com.facebook.katana",
    "com.facebook.system",
    "com.facebook.appmanager",
    "com.facebook.services",
    "com.facebook.orca",
    "com.tv.clean",
    "com.yxt.factorytest",
    "com.android.app.cus.aging",
    "com.android.amediatech.fota",
    "com.abupdate.fota_demo_iot",
    "com.google.android.youtube.tv.recommendations",
    "com.google.android.partnersetup",
    "com.google.android.backuptransport",
    "com.google.android.syncadapters.contacts",
    "com.android.calculator2",
    "com.google.android.calculator",
    "com.android.camera2",
    "com.google.android.GoogleCamera",
    "com.android.gallery3d",
    "com.android.music",
    "com.google.android.apps.restore",
    "com.google.android.apps.wellbeing",
    "com.google.android.apps.turbo",
    "com.google.android.onetimeinitializer",
    "com.google.android.as",
    "com.google.android.as.oss",
    "com.google.android.apps.work.oobconfig",
    "com.google.android.gms.location.history",
    "com.google.android.contacts",
    "com.android.contacts",
    "com.android.dialer",
    "com.google.android.dialer",
    "com.google.android.apps.messaging",
    "com.google.android.talk",
    "com.google.android.gm",
    "com.android.email",
    "com.google.android.tvrecommendations",
    "com.google.android.backdrop",
    "com.google.android.leanbacklauncher.recommendations",
    "com.google.android.syncadapters.calendar",
    "com.android.providers.calendar",
    "com.android.calendar",
    "com.google.android.calendar",
    "com.amazon.kindle",
    "com.microsoft.skydrive",
    "com.skype.raider",
]

WAVE2_CONTAINS = (
    "adups",
    "advert",
    ".ads.",
    "adservice",
    "adservices",
    "analytics",
    "telemetry",
    "bugreport",
    "logreport",
    "recommend",
    "sponsor",
    "otaupdate",
    "otaupgrade",
)

# Onda 3 — ainda reversível, mas mexe em coisa que alguém pode usar.
WAVE3 = [
    "com.android.chrome",
    "com.android.browser",
    "com.estrongs.android.pop",
    "com.google.android.apps.nbu.files",
    "com.android.deskclock",
    "com.google.android.deskclock",
    "com.softwinner.update",
    "com.allwinnertech.superupgrade",
    "android.rockchip.update.service",
    "com.droidlogic.otaupgrade",
    "com.ionitech.airscreen",
    "com.google.android.marvin.talkback",
]

# Apps que a fábrica enfia e não são codec, loja nem launcher.
# A primeira vez pergunta. YouTube da TV fica de fora: muita TV Box só tem ele.
LIXO_FABRICA = (
    ("org.xbmc.kodi", "Kodi"),
    ("com.netflix.ninja", "Netflix"),
    ("com.netflix.mediaclient", "Netflix"),
    ("com.amazon.amazonvideo.livingroom", "Prime Video"),
    ("com.amazon.avod.thirdpartyclient", "Prime Video"),
    ("com.disney.disneyplus", "Disney+"),
    ("com.globo.globotv", "Globoplay"),
    ("com.google.android.videos", "Filmes Google"),
    ("com.ionitech.airscreen", "AirScreen"),
    ("com.softwinner.fireplayer", "Player da placa"),
    ("tv.pluto.android", "Pluto TV"),
    ("org.videolan.vlc", "VLC"),
)

BAD_EXACT = {
    "com.adups.fota",
    "com.adups.fota.sysoper",
    "com.adups.fota.oper",
    "com.adups.sdk",
    "com.adups.installation",
    "com.android.adups",
    "com.changhong.tvupdate",
    # Backdoor XCPE, descrito pelo Google em novembro de 2026. Vem na
    # firmware, se reinstala a partir de /oem e aluga o IP da casa.
    "com.oemservice",
    "x.cpe",
    "com.abc.nexus",
    "com.android.system.ntp",
    "com.android.sso.auth.handler",
    "com.ota.service",
    "com.sdt.ota",
    "com.sdt.backupappmanger",
    "com.sdt.producttest",
    "com.oem.qa",
}
BAD_BITS = (
    "coinhive", "xmrig", "minergate", "luckypatcher", "spyware", "adwarecore",
    "oemservice",
)

PLAY_STACK = [
    "com.android.vending",
    "com.google.android.gms",
    "com.google.android.gsf",
    "com.google.android.gsf.login",
    "com.google.android.partnersetup",
    "com.google.android.backuptransport",
    "com.google.android.configupdater",
    "com.google.android.ext.services",
    "com.google.android.ext.shared",
    "com.android.vending",
    "com.google.android.webview",
    "com.android.webview",
    "com.google.android.trichromelibrary",
    "com.android.trichromelibrary",
    "com.android.providers.downloads",
    "com.android.providers.downloads.ui",
    "com.google.android.packageinstaller",
    "com.android.packageinstaller",
    "com.android.certinstaller",
    "com.android.proxyhandler",
    "com.android.networkstack",
    "com.google.android.networkstack",
    "com.android.permissioncontroller",
    "com.google.android.permissioncontroller",
]

VENDING_ACTIVITIES = [
    "com.android.vending/com.google.android.finsky.tvmainactivity.TvMainActivity",
    "com.android.vending/com.google.android.finsky.activities.TvMainActivity",
    "com.android.vending/com.google.android.finsky.activities.MainActivity",
    "com.android.vending/.AssetBrowserActivity",
]

UPDATES_OK = {
    "com.android.vending",
    "com.google.android.webview",
    "com.android.webview",
    "com.google.android.trichromelibrary",
    "com.android.trichromelibrary",
}
CLEAR_DATA_OK = {"com.android.vending"}
CLEAR_CACHE_OK = {
    "com.android.vending",
    "com.google.android.gms",
    "com.google.android.gsf",
    "com.google.android.webview",
    "com.android.webview",
}
SETTING_OK = {
    "auto_time",
    "auto_time_zone",
    "private_dns_mode",
    "private_dns_specifier",
    "captive_portal_mode",
    "captive_portal_detection_enabled",
    "package_verifier_enable",
    "verifier_verify_adb_installs",
    "wifi_sleep_policy",
    "network_recommendations_enabled",
    "ble_scan_always_enabled",
    "window_animation_scale",
    "transition_animation_scale",
    "animator_duration_scale",
    "app_standby_enabled",
    "webview_provider",
    "stay_on_while_plugged_in",
}

SDK_RELEASE = {
    21: 5, 22: 5, 23: 6, 24: 7, 25: 7, 26: 8, 27: 8, 28: 9, 29: 10,
    30: 11, 31: 12, 32: 12, 33: 13, 34: 14, 35: 15, 36: 16, 37: 17,
}
# kernel (major, minor) → SDK honesto máximo, com folga de backport
KERNEL_MAX_SDK = {
    (3, 4): 22, (3, 10): 24, (3, 14): 25, (3, 18): 26,
    (4, 4): 29, (4, 9): 30, (4, 14): 32, (4, 19): 34,
    (5, 4): 34, (5, 10): 35, (5, 15): 36, (6, 1): 36, (6, 6): 37, (6, 12): 37,
}

PERIGOSAS = (
    "android.permission.INSTALL_PACKAGES",
    "android.permission.REQUEST_INSTALL_PACKAGES",
    "android.permission.BIND_DEVICE_ADMIN",
    "android.permission.BIND_ACCESSIBILITY_SERVICE",
    "android.permission.WRITE_SECURE_SETTINGS",
    "android.permission.READ_SMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.SEND_SMS",
    "android.permission.MASTER_CLEAR",
)


def agora_iso():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def setup_stdio():
    if os.name == "nt":
        try:
            os.system("chcp 65001 > nul")
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_SESSAO = None


def iniciar_sessao():
    global _SESSAO
    if _SESSAO:
        return _SESSAO
    try:
        pasta = pasta_visivel() or garantir_dados()
    except Exception:
        return None
    _SESSAO = pasta / ("sessao_%s.txt" % datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    try:
        _SESSAO.write_text("SpeedTV Box — sessão completa\n", encoding="utf-8")
    except Exception:
        _SESSAO = None
    return _SESSAO


def say(msg=""):
    print(msg, flush=True)
    if not _SESSAO:
        return
    try:
        with _SESSAO.open("a", encoding="utf-8") as fh:
            fh.write((msg or "") + "\n")
    except Exception:
        pass


def titulo(texto):
    say("")
    say("─" * 62)
    say(texto)
    say("─" * 62)


def ram_usavel_kb(mem):
    """No kernel 3.10 não existe MemAvailable. Livre + cache é o que dá para usar."""
    if not mem:
        return None
    if mem.get("MemAvailable"):
        return mem["MemAvailable"]
    if mem.get("MemFree") is None and not mem.get("Cached") and not mem.get("Buffers"):
        return None
    return (mem.get("MemFree") or 0) + (mem.get("Cached") or 0) + (mem.get("Buffers") or 0)


def kb_mb(kb):
    if kb is None:
        return "—"
    mb = kb / 1024.0
    if mb >= 1024:
        return "%.2f GB" % (mb / 1024.0)
    return "%d MB" % int(round(mb))


def validar_pacote(pkg):
    return bool(pkg) and bool(PKG_RE.match(pkg))


def validar_valor(valor):
    if valor is None:
        return False
    s = str(valor).strip()
    if not s or len(s) > 80:
        return False
    if any(c in s for c in "\n\r;&|$`<>\"'\\"):
        return False
    return True


class DeviceOffline(Exception):
    pass


def find_adb():
    env = os.environ.get("SPEEDTV_ADB", "").strip() or os.environ.get("NEXO_ADB", "").strip()
    if env and os.path.isfile(env):
        return env
    found = shutil.which("adb")
    if found:
        return found
    here = Path(__file__).resolve().parent
    for rel in ("platform-tools/adb", "platform-tools/adb.exe", "adb", "adb.exe"):
        p = here / rel
        if p.is_file():
            return str(p)
    return None


class Adb:
    def __init__(self, serial, binary):
        self.serial = serial
        self.binary = binary
        self.user = "0"

    def _exec(self, args, timeout=30):
        try:
            proc = subprocess.run(
                [self.binary, *args],
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return 124, "[timeout]"
        except FileNotFoundError:
            return 127, "[adb ausente]"
        blob = (proc.stdout or b"") + b"\n" + (proc.stderr or b"")
        text = blob.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")
        return proc.returncode, text.strip()

    def connect(self):
        if ":" not in self.serial:
            return self.state()
        _code, out = self._exec(["connect", self.serial], 20)
        return out

    def state(self):
        _code, out = self._exec(["-s", self.serial, "get-state"], 12)
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        return lines[-1] if lines else ""

    def shell(self, command, timeout=40):
        _code, out = self._exec(["-s", self.serial, "shell", command], timeout)
        low = out.lower()
        if (
            "device offline" in low
            or "no devices/emulators" in low
            or "device '" in low and "not found" in low
            or "unauthorized" in low
        ):
            raise DeviceOffline(out[:400])
        return out

    def pair(self, endpoint, code):
        _c, out = self._exec(["pair", endpoint, code], 40)
        return out

    def prop(self, name):
        if not CHAVE_RE.match(name):
            return ""
        return self.shell("getprop " + name, 15).strip().splitlines()[-1].strip() if False else self._prop(name)

    def _prop(self, name):
        out = self.shell("getprop " + name, 15).strip()
        lines = [ln.strip() for ln in out.splitlines() if ln.strip() and not ln.startswith("[")]
        return lines[-1] if lines else ""

    def getprop_all(self):
        text = self.shell("getprop", 30)
        props = {}
        for line in text.splitlines():
            m = re.match(r"\[([^\]]+)\]:\s*\[(.*)\]\s*$", line.strip())
            if m:
                props[m.group(1)] = m.group(2)
        return props

    def refresh_user(self):
        try:
            out = self.shell("am get-current-user", 15)
        except DeviceOffline:
            self.user = "0"
            return
        m = re.search(r"(\d+)", out)
        self.user = m.group(1) if m else "0"

    def installed_map(self):
        """nome -> caminho, só o que está instalado."""
        return parse_pm_paths(self.shell("pm list packages -f", 40))

    def system_names(self):
        return set(parse_pm_names(self.shell("pm list packages -s", 30)))

    def third_names(self):
        return set(parse_pm_names(self.shell("pm list packages -3", 25)))

    def disabled_names(self):
        return set(parse_pm_names(self.shell("pm list packages -d", 25)))

    def uninstalled_names(self):
        todos = set(parse_pm_names(self.shell("pm list packages -u", 30)))
        vivos = set(self.installed_map())
        return todos - vivos

    def enabled_code(self, pkg):
        if not validar_pacote(pkg):
            return None
        text = self.shell("dumpsys package " + pkg, 25)
        m = re.search(r"User\s+" + re.escape(self.user) + r":[^\n]*\benabled=(\d+)", text)
        if not m:
            m = re.search(r"\benabled=(\d+)", text)
        if m:
            return int(m.group(1))
        path = self.shell("pm path " + pkg, 12)
        if "package:" in path:
            return 1
        return None

    def existe(self, pkg):
        if not validar_pacote(pkg):
            return False
        return "package:" in self.shell("pm path " + pkg, 15)


def parse_pm_names(text):
    names = []
    for line in text.splitlines():
        line = line.strip()
        if "package:" not in line:
            continue
        name = line.split("package:", 1)[1].strip()
        if "=" in name and "/" in name:
            name = name.rsplit("=", 1)[-1]
        name = name.strip()
        if validar_pacote(name):
            names.append(name)
    return names


def parse_pm_paths(text):
    found = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("package:"):
            continue
        body = line[len("package:"):]
        path, sep, name = body.rpartition("=")
        if sep and validar_pacote(name):
            found[name] = path
    return found


def parse_meminfo(text):
    data = {}
    for line in text.splitlines():
        m = re.match(r"(\w+):\s+(\d+)\s+kB", line.strip())
        if m:
            data[m.group(1)] = int(m.group(2))
    return data


def parse_iomem_mb(text):
    total = 0
    hits = 0
    for a, b in re.findall(r"([0-9a-fA-F]+)-([0-9a-fA-F]+)\s*:\s*System RAM", text):
        start = int(a, 16)
        end = int(b, 16)
        if end >= start:
            total += end - start + 1
            hits += 1
    if not hits:
        return None
    return int(total / (1024 * 1024))


def parse_zoneinfo_mb(text):
    """Páginas que o kernel realmente administra. Em TV Box barata o meminfo mente; isto quase nunca."""
    paginas = 0
    for n in re.findall(r"managed\s+(\d+)", text or ""):
        paginas += int(n)
    if paginas < 4096:
        return None
    return max(1, (paginas * 4) // 1024)


def parse_dmesg_mb(text):
    m = re.search(r"Memory:\s+\d+K/(\d+)K", text or "")
    if not m:
        return None
    mb = int(m.group(1)) // 1024
    return mb or None


def escolher_ram(meminfo_mb, zone_mb, iomem_mb, dmesg_mb, dumpsys_mb):
    fisicas = [n for n in (zone_mb, iomem_mb, dmesg_mb) if n]
    if fisicas:
        real = min(fisicas)
        if zone_mb and real == zone_mb:
            fonte = "zoneinfo"
        elif iomem_mb and real == iomem_mb:
            fonte = "mapa de memória"
        else:
            fonte = "dmesg"
    elif meminfo_mb:
        real, fonte = meminfo_mb, "meminfo"
    elif dumpsys_mb:
        real, fonte = dumpsys_mb, "dumpsys"
    else:
        return None, "", False
    mentira = bool(meminfo_mb and real and meminfo_mb > int(real * 1.25) and meminfo_mb - real > 256)
    return real, fonte, mentira


def parse_kernel(text):
    m = re.search(r"(\d+)\.(\d+)(?:\.\d+)?", text or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def release_major(rel):
    m = re.search(r"(\d+)", rel or "")
    return int(m.group(1)) if m else None


def kernel_max_sdk(kernel):
    if not kernel:
        return None
    best = None
    for (maj, minor), sdk in KERNEL_MAX_SDK.items():
        if kernel[0] > maj or (kernel[0] == maj and kernel[1] >= minor):
            if best is None or (maj, minor) >= best[0]:
                best = ((maj, minor), sdk)
    return best[1] if best else None


def avaliar_android(sdk, release, kernel):
    """Devolve dict com inconsistência de versão. Não acusa só por patch antigo."""
    notas = []
    spoof = False
    major = release_major(release)
    esperado = SDK_RELEASE.get(sdk)
    if esperado and major and abs(esperado - major) >= 2:
        spoof = True
        notas.append(
            "release %s não combina com SDK %s (o par honesto dessa API é Android %s)"
            % (release, sdk, esperado)
        )
    teto = kernel_max_sdk(kernel)
    if teto and sdk and sdk > teto + 1:
        spoof = True
        notas.append(
            "kernel %s.%s não sustenta SDK %s (teto honesto por volta do SDK %s). "
            "A tela pode dizer Android %s e o sistema ser bem mais velho."
            % (kernel[0], kernel[1], sdk, teto, release or "?")
        )
    if not notas:
        notas.append("SDK, release e kernel contam a mesma história, dentro da folga de fabricante.")
    return {"mentira": spoof, "notas": notas, "teto_sdk": teto, "release_esperado": esperado}


def numero_mb(valor):
    if valor is None:
        return None
    s = str(valor).strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(gb|g\b|mb|m\b)", s, re.I)
    if m:
        n = float(m.group(1))
        unit = m.group(2).lower()
        return int(n * 1024) if unit.startswith("g") else int(n)
    if re.fullmatch(r"\d{3,8}", s):
        n = int(s)
        if n > 1024 * 1024 * 8:
            return n // (1024 * 1024)
        if n > 64 * 1024:
            return n // 1024
        return n
    return None


def parse_df_data(text):
    livre = None
    uso = None
    escolhido = None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        mount = parts[-1]
        if mount not in ("/data", "/sdcard", "/storage/emulated/0"):
            continue
        # Available é o antepenúltimo na toybox df quando tem Use%
        try:
            if parts[-2].endswith("%"):
                avail = int(parts[-3])
                uso = parts[-2]
            else:
                avail = int(parts[3])
                uso = None
        except ValueError:
            continue
        if mount == "/data" or livre is None:
            livre = avail
            escolhido = mount
            if mount == "/data":
                break
    return {"livre_kb": livre, "uso": uso, "onde": escolhido}


def parse_widevine(text):
    if not text:
        return "sem resposta do DRM"
    low = text.lower()
    if "widevine" not in low and "level" not in low:
        return "Widevine não apareceu no dumpsys. TV Box sem certificação, ou o serviço de DRM não respondeu."
    nivel = None
    for token in ("L1", "L2", "L3", "level1", "level3", "HW_SECURE_ALL", "HW_SECURE_DECODE", "SW_SECURE_CRYPTO"):
        if token.lower() in low or token in text:
            if token in ("L1", "HW_SECURE_ALL"):
                nivel = "L1"
            elif token in ("L2", "HW_SECURE_DECODE") and nivel != "L1":
                nivel = "L2"
            elif token in ("L3", "level3", "SW_SECURE_CRYPTO") and nivel is None:
                nivel = "L3"
    if nivel == "L1":
        return "Widevine L1 (hardware). Netflix e afins podem ir além de SD, se o app deixar."
    if nivel == "L2":
        return "Widevine L2."
    if nivel == "L3":
        return (
            "Widevine L3 (software). Catálogo protegido fica em SD. "
            "Isto é o nível honesto de quase toda TV Box genérica."
        )
    return "Widevine presente, nível não identificado no texto. Trecho salvo no relatório."


def extrair_json(texto):
    t = (texto or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def ultimo_componente(text):
    comps = re.findall(r"([A-Za-z][\w.]*/[\w.$]+)", text or "")
    for c in reversed(comps):
        pkg = c.split("/", 1)[0]
        if validar_pacote(pkg):
            return c
    return None


def pacote_de(ref):
    return ref.split("/", 1)[0]


class Gate:
    def __init__(self, dinamicos=None):
        self.dinamicos = set(dinamicos or ())

    def motivo(self, pkg):
        if not validar_pacote(pkg):
            return "nome inválido"
        low = pkg.lower()
        if pkg in PROTECTED_EXACT:
            return "lista protegida (sistema, Play, launcher, teclado ou HDMI)"
        if pkg in self.dinamicos:
            return "está em uso agora (home, teclado, acessibilidade ou entrada de vídeo)"
        for pref in PROTECTED_PREFIXES:
            if low.startswith(pref):
                return "prefixo protegido " + pref
        for bit in DANGER_BITS:
            if bit in low:
                return "nome contém '%s'" % bit
        if low.endswith("overlay"):
            return "overlay de sistema"
        return None


def _storage_partilhado(path):
    s = str(path)
    return s.startswith(("/sdcard", "/storage", "/mnt/runtime", "/mnt/media_rw"))


def garantir_dados():
    """No Termux o Download do Android não deixa criar pasta. Grava no $HOME."""
    global _DADOS
    if _DADOS is not None:
        return _DADOS
    ordem = []
    home = os.environ.get("HOME")
    if _storage_partilhado(RAIZ) and home:
        ordem.append(Path(home) / "speedtv-dados")
    ordem.append(RAIZ / "speedtv-dados")
    if home:
        ordem.append(Path(home) / "speedtv-dados")
    visto = set()
    for pasta in ordem:
        chave = str(pasta)
        if chave in visto:
            continue
        visto.add(chave)
        try:
            pasta.mkdir(parents=True, exist_ok=True)
            prova = pasta / ".ok"
            prova.write_text("1", encoding="utf-8")
            prova.unlink()
            _DADOS = pasta
            return pasta
        except Exception:
            continue
    raise SystemExit(
        "Não consegui gravar a pasta speedtv-dados. "
        "Copie o agente para $HOME e rode: python speedtvbox.py"
    )


def caminho_journal():
    return garantir_dados() / "journal.json"


def carregar_journal():
    p = caminho_journal()
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"disabled": [], "settings": [], "wm": {}, "ondas": [], "notas": [], "package_states": {}, "removidos": []}


def salvar_journal(j):
    caminho_journal().write_text(json.dumps(j, indent=2, ensure_ascii=False), encoding="utf-8")


def anexar_log(nome, texto, resumo=""):
    """Grava em $HOME/speedtv-dados e copia para a pasta SpeedTV da memória do celular."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    titulo_log = _nome_arquivo(nome)
    quando = datetime.now().strftime("%Y-%m-%d %H:%M")
    bruto = texto if isinstance(texto, str) else json.dumps(texto, indent=2, ensure_ascii=False)
    blob = (
        "SpeedTV Box — %s\nQuando: %s\n"
        "Este arquivo começa pelo resumo, para você ler ou colar numa IA. O bruto vem depois.\n\n"
        "RESUMO\n%s\n\nBRUTO\n%s\n"
    ) % (titulo_log, quando, (resumo or "(sem resumo)").strip(), bruto)
    pasta = garantir_dados()
    path = pasta / ("%s_%s.txt" % (stamp, titulo_log))
    path.write_text(blob, encoding="utf-8")
    copia = publicar_relatorio(path)
    return copia or path


def _nome_arquivo(nome):
    limpo = re.sub(r"[^A-Za-z0-9_-]+", "-", nome or "").strip("-")
    return (limpo or "log")[:40]


def dizer_onde(path):
    if not path:
        say("Não consegui gravar o arquivo.")
        say("No Termux, rode uma vez: termux-setup-storage")
        say("e aceite o acesso aos arquivos. Aí a pasta SpeedTV aparece na memória do celular.")
        return
    say("Arquivo: %s" % path)
    if "Download" in str(path) or "downloads" in str(path):
        say("Abra o app Arquivos, pasta Download, pasta SpeedTV.")
    else:
        say("Ficou só dentro do Termux. Rode uma vez: termux-setup-storage")
        say("Aceite o acesso. Aí os próximos relatórios vão para Download/SpeedTV.")


def anexar_metricas(item):
    pasta = garantir_dados()
    with (pasta / "metricas.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item, ensure_ascii=False) + "\n")


def escrever_rollback(serial, binary, pkgs, estados=None):
    pasta = garantir_dados()
    estados = estados or {}
    linhas = ['"%s" connect %s' % (binary, serial)]
    for pkg in pkgs:
        if not validar_pacote(pkg):
            continue
        estado = estados.get(pkg) or {}
        linhas.append('"%s" -s %s shell pm install-existing --user 0 %s' % (binary, serial, pkg))
        if estado.get("enabled") == 0:
            linhas.append('"%s" -s %s shell pm default-state --user 0 %s' % (binary, serial, pkg))
        else:
            linhas.append('"%s" -s %s shell pm enable --user 0 %s' % (binary, serial, pkg))
    (pasta / "reverter.sh").write_text("#!/bin/sh\n" + "\n".join(linhas) + "\n", encoding="utf-8")
    (pasta / "reverter.bat").write_text("\r\n".join(linhas) + "\r\n", encoding="utf-8")

def perguntar(msg, default_sim=True, forcar=None):
    if forcar is True:
        say(msg + " → sim")
        return True
    if forcar is False:
        say(msg + " → não")
        return False
    suf = " [S/n] " if default_sim else " [s/N] "
    try:
        r = input(msg + suf).strip().lower()
    except EOFError:
        return default_sim
    if not r:
        return default_sim
    return r in ("s", "sim", "y", "yes")


def coletar_dinamicos(adb):
    nomes = set()
    blocos = []
    try:
        blocos.append(adb.shell(
            "cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME",
            20,
        ))
    except DeviceOffline:
        raise
    except Exception:
        pass
    try:
        blocos.append(adb.shell("settings get secure default_input_method", 12))
        blocos.append(adb.shell("settings get secure enabled_accessibility_services", 12))
        blocos.append(adb.shell("dumpsys tv_input | head -n 160", 20))
    except DeviceOffline:
        raise
    except Exception:
        pass
    blob = "\n".join(blocos)
    for achado in re.findall(r"([A-Za-z][\w.]*)/", blob):
        if validar_pacote(achado):
            nomes.add(achado)
    # o resolve --brief às vezes devolve só o pacote na última linha
    for line in blob.splitlines():
        line = line.strip()
        if validar_pacote(line):
            nomes.add(line)
    return nomes


def home_package(adb):
    text = adb.shell(
        "cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME",
        20,
    )
    comp = ultimo_componente(text)
    if comp:
        return pacote_de(comp)
    for line in reversed(text.splitlines()):
        line = line.strip()
        if validar_pacote(line):
            return line
    return ""


def coletar_metricas(adb, etiqueta):
    mem = parse_meminfo(adb.shell("cat /proc/meminfo", 15))
    df = parse_df_data(adb.shell("df /data", 15))
    des = adb.disabled_names()
    ps = adb.shell("ps -A", 20)
    if "unknown" in ps.lower()[:80] or "bad pid" in ps.lower() or len(ps.splitlines()) < 2:
        ps = adb.shell("ps", 20)
    item = {
        "quando": agora_iso(),
        "etiqueta": etiqueta,
        "mem_total_kb": mem.get("MemTotal"),
        "mem_available_kb": ram_usavel_kb(mem),
        "mem_free_kb": mem.get("MemFree"),
        "mem_cache_kb": (mem.get("Cached") or 0) + (mem.get("Buffers") or 0),
        "swap_total_kb": mem.get("SwapTotal"),
        "swap_free_kb": mem.get("SwapFree"),
        "zram_kb": mem.get("Zram") or mem.get("SwapCached"),
        "desativados": len(des),
        "processos": max(0, len([ln for ln in ps.splitlines() if ln.strip()]) - 1),
        "data_livre_kb": df.get("livre_kb"),
        "data_uso": df.get("uso"),
    }
    anexar_metricas(item)
    return item


def linha_metrica(m):
    return "%s | usável %s | sem uso %s | processos %s | desligados %s | /data %s" % (
        m.get("etiqueta"),
        kb_mb(m.get("mem_available_kb")),
        kb_mb(m.get("mem_free_kb")),
        m.get("processos"),
        m.get("desativados"),
        kb_mb(m.get("data_livre_kb")),
    )


def ler_zram(adb):
    info = {"existe": False}
    try:
        swaps = adb.shell("cat /proc/swaps", 12)
    except DeviceOffline:
        raise
    info["swaps"] = swaps.strip()
    disk = adb.shell("cat /sys/block/zram0/disksize 2>/dev/null", 12).strip()
    algo = adb.shell("cat /sys/block/zram0/comp_algorithm 2>/dev/null", 12).strip()
    mm = adb.shell("cat /sys/block/zram0/mm_stat 2>/dev/null", 12).strip()
    if disk.isdigit():
        info["existe"] = True
        info["disco_mb"] = int(disk) // (1024 * 1024)
    if algo:
        info["algoritmo"] = algo.replace("[", "").replace("]", "")
        # toybox mostra o ativo entre colchetes
        m = re.search(r"\[([^\]]+)\]", algo)
        if m:
            info["algoritmo"] = m.group(1)
    if mm:
        parts = mm.split()
        if len(parts) >= 3 and parts[0].isdigit():
            info["dados_mb"] = int(parts[0]) // (1024 * 1024)
            info["comprimido_mb"] = int(parts[1]) // (1024 * 1024)
            info["memoria_mb"] = int(parts[2]) // (1024 * 1024)
    return info


def varredura_portas(texto):
    """Só porta em escuta (estado 0A). Conexão de saída não é serviço aberto."""
    portas = set()
    for line in texto.splitlines():
        parts = line.split()
        if len(parts) < 4 or ":" not in parts[1]:
            continue
        if parts[3].upper() != "0A":
            continue
        _ip, port = parts[1].rsplit(":", 1)
        try:
            portas.add(int(port, 16))
        except ValueError:
            continue
    conhecidas = {53, 67, 68, 123, 1900, 5353, 5355, 5555, 6466, 6467, 8008, 8009, 8443, 9000, 10001}
    estranhas = sorted(p for p in portas if p not in conhecidas and p > 0)
    return sorted(portas), estranhas


def init_e_suspeito(nome):
    """Não marca bootanim: a palavra ota aparece no meio de um nome legítimo."""
    return bool(re.search(
        r"(^|[._@-])(adups|xmrig|coinhive|telemetry|adware|fota|oemservice)([._@-]|$)",
        nome or "",
        re.I,
    ))


def parse_rss(texto):
    itens = []
    for line in (texto or "").splitlines():
        m = re.match(r"^\s*([\d,]+)K:\s+(\S+)", line)
        if not m:
            continue
        itens.append({
            "kb": int(m.group(1).replace(",", "")),
            "nome": m.group(2),
            "aberto": "activities" in line,
        })
    return itens


def frases_relatorio(r):
    frases = []
    if (r.get("android") or {}).get("mentira"):
        frases.append(
            "A versão de Android da etiqueta não combina com o kernel. É firmware remarcado. "
            "App que exige a versão de verdade pode falhar mesmo a loja dizendo que serve."
        )
    else:
        frases.append("A versão de Android e o kernel não se contradizem, ou não deu para cravar uma mentira.")
    if r.get("ram_mentira"):
        frases.append(
            "A RAM anunciada é maior que a medida no kernel. O número real é o que decide 1080p. "
            "Não acredite no 4 GB de vitrine."
        )
    else:
        frases.append("A RAM medida é a que vale. Não achei propaganda de memória acima do meminfo.")
    w = r.get("widevine") or ""
    if w.startswith("Widevine L1"):
        frases.append(
            "O DRM respondeu L1. Em TV Box genérica isso só vale se um app protegido tocar em HD. "
            "Tela preta: a opção Widevine esconde a biblioteca falsa e assume L3 de verdade, em SD."
        )
    elif "L3" in w:
        frases.append("Widevine L3. Catálogo protegido fica em SD. Nenhum ajuste sobe isso para 4K.")
    else:
        frases.append("Widevine: " + (w or "sem leitura."))
    if r.get("ruins"):
        frases.append(
            "Nome de risco instalado: %s. A opção Segurança desativa, não apaga."
            % ", ".join(r["ruins"][:6])
        )
    else:
        frases.append("Não achei Adups nem o backdoor XCPE (com.oemservice) entre os pacotes.")
    if r.get("portas_estranhas"):
        frases.append(
            "Tem porta escutando fora do comum de TV: %s. Porta alta de app saindo para a internet não entra nessa conta."
            % ", ".join(str(p) for p in r["portas_estranhas"][:8])
        )
    else:
        frases.append("Nenhuma porta escutando fora do conjunto normal de TV e do ADB.")
    return frases


def processos_pesados(texto, instalados, gate):
    """Processos que comem RAM e são um pacote. O núcleo do Android fica de fora."""
    nucleo = {
        "system_server", "surfaceflinger", "mediaserver", "mediaserver64",
        "netd", "vold", "zygote", "zygote64", "adbd", "keystore", "installd",
        "servicemanager", "lmkd", "logd", "audioserver", "cameraserver", "drmserver",
        "android.hardware.graphics.composer", "tombstoned",
    }
    vistos = set()
    itens = []
    for item in parse_rss(texto or "")[:20]:
        nome = (item.get("nome") or "").split(":")[0]
        if nome in nucleo or nome in vistos:
            continue
        if not validar_pacote(nome) or nome not in instalados:
            continue
        vistos.add(nome)
        motivo = gate.motivo(nome) if gate else None
        itens.append({"pacote": nome, "kb": item.get("kb") or 0, "protegido": motivo or ""})
    return itens


def varrer_boot(adb):
    """Scripts de boot que recriam vírus a cada liga. Não mexe no init principal."""
    lista = adb.shell(
        "grep -l -i -E 'xmrig|adups|coinhive|minergate|oemservice|nohup|classes.dex' "
        "/system/etc/init/* /vendor/etc/init/* /system/etc/*.sh /system/bin/*.sh 2>/dev/null",
        25,
    )
    achados = []
    for linha in lista.splitlines():
        arq = linha.strip()
        if not re.match(r"^/[\w./\-]+$", arq):
            continue
        nome = arq.rsplit("/", 1)[-1]
        protegido = nome in ("init.rc", "init.environ.rc", "ueventd.rc", "bootanim.rc") or nome.startswith("init.")
        trecho = adb.shell("head -c 400 %s 2>/dev/null" % arq, 12)
        achados.append({"arquivo": arq, "protegido": protegido, "trecho": (trecho or "")[:200]})
        if len(achados) >= 12:
            break
    return achados


def afastar_scripts(adb, journal, itens):
    root = tem_root(adb)
    if not root:
        say("Sem root. Não dá para tirar script de boot. Dá para desativar o app, mas ele pode voltar ao ligar.")
        return []
    movidos = []
    for item in itens:
        arq = item.get("arquivo") or ""
        if item.get("protegido"):
            say("  deixo %s no lugar. É script do sistema. Mover isso pode impedir a TV Box de ligar." % arq)
            continue
        if not re.match(r"^/[\w./\-]+$", arq):
            continue
        bak = arq + ".speedtv-bak"
        adb.shell("%s -c 'mv %s %s'" % (root, arq, bak), 15)
        journal.setdefault("scripts", []).append({"de": arq, "bak": bak})
        salvar_journal(journal)
        movidos.append(arq)
        say("  tirei do boot: %s" % arq)
        say("  a cópia ficou em %s. A opção Desfazer coloca de volta." % bak)
    return movidos


def auditar(adb, falar=True):
    if falar:
        titulo("Auditoria forense — só leitura")
        say("Nada é desativado nesta etapa.")
    props = adb.getprop_all()
    mem_txt = adb.shell("cat /proc/meminfo", 15)
    mem = parse_meminfo(mem_txt)
    iomem = adb.shell("cat /proc/iomem 2>/dev/null | grep -i 'System RAM'", 15)
    iomem_mb = parse_iomem_mb(iomem)
    dmesg = adb.shell("dmesg 2>/dev/null | grep -i -m 5 Memory:", 15)
    kernel_txt = adb.shell("cat /proc/version", 12)
    kernel = parse_kernel(kernel_txt) or parse_kernel(props.get("ro.kernel.version", ""))
    try:
        sdk = int(props.get("ro.build.version.sdk") or adb.prop("ro.build.version.sdk") or "0")
    except ValueError:
        sdk = 0
    release = props.get("ro.build.version.release", "")
    veredito = avaliar_android(sdk, release, kernel)
    dumpsys_mem = adb.shell("dumpsys meminfo | head -n 30", 25)
    total_ram_dump = None
    m = re.search(r"Total RAM:\s+([\d,]+)", dumpsys_mem)
    if m:
        total_ram_dump = int(m.group(1).replace(",", "")) // 1024

    zone_txt = adb.shell("grep managed /proc/zoneinfo 2>/dev/null", 15)
    zone_mb = parse_zoneinfo_mb(zone_txt)
    dmesg_mb = parse_dmesg_mb(dmesg)
    mem_mb = (mem.get("MemTotal") or 0) // 1024 or None
    real_mb, ram_fonte, meminfo_mente = escolher_ram(mem_mb, zone_mb, iomem_mb, dmesg_mb, total_ram_dump)

    anuncios = []
    for k, v in props.items():
        if re.search(r"ram|memsize|ddrsize|memorysize", k, re.I):
            mb = numero_mb(v)
            anuncios.append({"chave": k, "valor": v, "mb": mb})
    mentira_ram = []
    if real_mb:
        for a in anuncios:
            if a["mb"] and a["mb"] > real_mb * 1.25 and a["mb"] - real_mb > 256:
                mentira_ram.append(a)
    if meminfo_mente and mem_mb:
        mentira_ram.append({"chave": "MemTotal", "valor": "%d MB" % mem_mb, "mb": mem_mb})

    wide_txt = adb.shell(
        "dumpsys media.drm | grep -i -E 'widevine|securityLevel|security level|plugin|vendor' | head -n 40",
        25,
    )
    if "widevine" not in wide_txt.lower():
        wide_txt = wide_txt + "\n" + adb.shell("dumpsys media.drm | head -n 80", 25)
    wide = parse_widevine(wide_txt)

    df = parse_df_data(adb.shell("df -k /data /system 2>/dev/null || df /data", 15))
    zram = ler_zram(adb)
    uptime = adb.shell("cat /proc/uptime", 10).strip().split()
    up_s = None
    if uptime:
        try:
            up_s = float(uptime[0])
        except ValueError:
            up_s = None

    boot_events = adb.shell("logcat -b events -d -t 1500 2>/dev/null | grep -m 30 boot_progress", 25)
    boot_ms = None
    nums = [int(n) for n in re.findall(r"boot_progress\w*\s*[:=]\s*(\d+)", boot_events)]
    if not nums:
        nums = [int(n) for n in re.findall(r"\b(\d{4,7})\b", boot_events)]
    if nums:
        boot_ms = max(nums)
        if boot_ms > 1000 * 60 * 15:
            boot_ms = None

    abis = props.get("ro.product.cpu.abilist") or props.get("ro.product.cpu.abi") or ""
    cpu = adb.shell("grep -m 1 -E 'Hardware|model name|Processor' /proc/cpuinfo", 12)
    ncpu = adb.shell("grep -c ^processor /proc/cpuinfo", 12).strip()

    packages = adb.installed_map()
    sistema = adb.system_names()
    terceiros = adb.third_names()
    desativados = adb.disabled_names()
    removidos = adb.uninstalled_names()

    play_estado = []
    for pkg in dict.fromkeys(PLAY_STACK):
        if pkg in packages:
            code = adb.enabled_code(pkg)
            play_estado.append({"pacote": pkg, "situacao": "instalado", "enabled": code})
        elif pkg in removidos:
            play_estado.append({"pacote": pkg, "situacao": "removido para o usuário", "enabled": None})
        elif pkg in desativados:
            play_estado.append({"pacote": pkg, "situacao": "desativado", "enabled": 3})

    tcp = adb.shell("grep ' 0A ' /proc/net/tcp /proc/net/tcp6 2>/dev/null | head -n 80", 15)
    portas, estranhas = varredura_portas(tcp)

    ruins = []
    for nome in packages:
        low = nome.lower()
        if nome in BAD_EXACT or any(b in low for b in BAD_BITS):
            ruins.append(nome)
    for nome in removidos:
        if nome in BAD_EXACT:
            ruins.append(nome + " (já removido do usuário)")

    # permissão só em terceiro e em nome suspeito, teto de 50
    suspeitos_perm = []
    candidatos = list(terceiros) + [n for n in ruins if n in packages]
    vistos = set()
    for nome in candidatos:
        if nome in vistos or nome not in packages:
            continue
        vistos.add(nome)
        if len(vistos) > 50:
            break
        dump = adb.shell(
            "dumpsys package %s | grep -E '%s' | head -n 20" % (nome, "|".join(PERIGOSAS)),
            18,
        )
        achou = [p.split(".")[-1] for p in PERIGOSAS if p in dump or p.split(".")[-1] in dump]
        if achou:
            suspeitos_perm.append({"pacote": nome, "permissoes": sorted(set(achou)), "sistema": nome in sistema})

    inits = {}
    for pasta in ("/system/etc/init", "/vendor/etc/init", "/odm/etc/init", "/product/etc/init"):
        lista = adb.shell("ls %s 2>/dev/null" % pasta, 12)
        nomes = [ln.strip() for ln in lista.splitlines() if ln.strip() and " " not in ln.strip()]
        if nomes and "No such" not in lista and "Permission" not in lista:
            inits[pasta] = nomes
    sus_init = []
    for pasta, nomes in inits.items():
        for nome in nomes:
            if re.search(r"adups|miner|xmrig|telemetry|spyware|adware", nome, re.I):
                sus_init.append("%s/%s" % (pasta, nome))

    servicos = [k for k, v in props.items() if k.startswith("init.svc.") and v == "running"]

    crash = adb.shell("logcat -b crash -d -t 80 2>/dev/null", 20)
    if not crash.strip():
        crash = adb.shell("logcat -d -t 120 *:E 2>/dev/null", 20)

    patch = props.get("ro.build.version.security_patch", "")
    modelo = props.get("ro.product.model", "")
    marca = props.get("ro.product.brand", "") or props.get("ro.product.manufacturer", "")
    plataforma = props.get("ro.board.platform", "") or props.get("ro.hardware", "")
    fingerprint = props.get("ro.build.fingerprint", "")
    display = props.get("ro.build.display.id", "")

    try:
        root_ok = bool(tem_root(adb))
    except Exception:
        root_ok = False
    try:
        boot_scripts = varrer_boot(adb)
    except Exception:
        boot_scripts = []
    try:
        pesados = processos_pesados(dumpsys_mem, set(packages), Gate(coletar_dinamicos(adb)))
    except Exception:
        pesados = []

    relatorio = {
        "quando": agora_iso(),
        "serial": adb.serial,
        "modelo": modelo,
        "marca": marca,
        "plataforma": plataforma,
        "fingerprint": fingerprint,
        "display": display,
        "sdk": sdk,
        "release": release,
        "patch": patch,
        "kernel": ".".join(str(x) for x in kernel) if kernel else "",
        "kernel_bruto": kernel_txt.strip()[:300],
        "android": veredito,
        "abi": abis,
        "cpu": cpu.strip(),
        "nucleos": ncpu,
        "ram_real_mb": real_mb,
        "ram_fonte": ram_fonte,
        "ram_meminfo_mb": mem_mb,
        "ram_zone_mb": zone_mb,
        "ram_iomem_mb": iomem_mb,
        "ram_dmesg_mb": dmesg_mb,
        "ram_dumpsys_mb": total_ram_dump,
        "ram_disponivel_kb": mem.get("MemAvailable") or mem.get("MemFree"),
        "ram_usavel_kb": ram_usavel_kb(mem),
        "ram_livre_kb": mem.get("MemFree"),
        "anuncios_ram": anuncios,
        "ram_mentira": mentira_ram,
        "dmesg_memory": dmesg.strip()[:500],
        "widevine": wide,
        "widevine_bruto": wide_txt.strip()[:1500],
        "armazenamento": df,
        "zram": {k: v for k, v in zram.items() if k != "swaps"},
        "uptime_s": up_s,
        "boot_ms": boot_ms,
        "usuario": adb.user,
        "pacotes": len(packages),
        "sistema": len(sistema),
        "terceiros": len(terceiros),
        "pacotes_instalados": sorted(packages),
        "pacotes_sistema": sorted(sistema),
        "pacotes_terceiros": sorted(terceiros),
        "desativados": sorted(desativados),
        "removidos_pilha": [p for p in removidos if p in PLAY_STACK or p in PROTECTED_EXACT],
        "play": play_estado,
        "ruins": ruins,
        "permissoes": suspeitos_perm,
        "portas": portas,
        "portas_estranhas": estranhas,
        "init_suspeito": sus_init,
        "init_contagem": {k: len(v) for k, v in inits.items()},
        "servicos_rodando": len(servicos),
        "crash_trecho": crash.strip()[:2500],
        "root": root_ok,
        "boot_scripts": boot_scripts,
        "pesados": pesados,
    }
    path = garantir_dados() / "auditoria-ultima.json"
    path.write_text(json.dumps(relatorio, indent=2, ensure_ascii=False), encoding="utf-8")
    resumo = "\n".join(frases_relatorio(relatorio))
    log = anexar_log("auditoria", json.dumps(relatorio, indent=2, ensure_ascii=False), resumo)
    if falar:
        imprimir_auditoria(relatorio)
        parecer_relatorio(relatorio)
        dizer_onde(log)
    return relatorio


def imprimir_auditoria(r):
    say("%s  %s" % (r.get("marca") or "?", r.get("modelo") or "?"))
    say("placa %s   abi %s   núcleos %s" % (r.get("plataforma") or "?", r.get("abi") or "?", r.get("nucleos") or "?"))
    say("fingerprint %s" % (r.get("fingerprint") or "—"))
    say("")
    say("Android na etiqueta : %s   (SDK %s)" % (r.get("release") or "?", r.get("sdk") or "?"))
    say("patch de segurança  : %s" % (r.get("patch") or "—"))
    say("kernel              : %s" % (r.get("kernel") or "—"))
    for nota in r.get("android", {}).get("notas", []):
        selo = "VERSÃO MENTIROSA" if r.get("android", {}).get("mentira") else "versão"
        say("  [%s] %s" % (selo, nota))
    say("")
    say("RAM de verdade       : %s (%s)" % (
        ("%d MB" % r["ram_real_mb"]) if r.get("ram_real_mb") else "—",
        r.get("ram_fonte") or "?",
    ))
    say("  meminfo           : %s" % (("%d MB" % r["ram_meminfo_mb"]) if r.get("ram_meminfo_mb") else "—"))
    say("  zoneinfo          : %s" % (("%d MB" % r["ram_zone_mb"]) if r.get("ram_zone_mb") else "sem leitura"))
    say("  mapa iomem        : %s" % (("%d MB" % r["ram_iomem_mb"]) if r.get("ram_iomem_mb") else "sem leitura"))
    say("  livre agora       : %s" % kb_mb(r.get("ram_disponivel_kb")))
    if r.get("ram_mentira"):
        for a in r["ram_mentira"]:
            say("  RAM DE VITRINE    : %s = %s  (~%s MB) contra ~%s MB reais" % (
                a["chave"], a["valor"], a["mb"], r.get("ram_real_mb")))
    elif r.get("anuncios_ram"):
        for a in r["anuncios_ram"][:6]:
            say("  prop de memória   : %s = %s" % (a["chave"], a["valor"]))
    else:
        say("  as medidas batem. Não achei RAM de vitrine.")
    if r.get("dmesg_memory"):
        say("  dmesg             : %s" % r["dmesg_memory"].splitlines()[0][:180])
    say("")
    say("Widevine            : %s" % r.get("widevine"))
    arm = r.get("armazenamento") or {}
    say("Armazenamento /data : %s livres (%s)" % (kb_mb(arm.get("livre_kb")), arm.get("uso") or "sem %"))
    z = r.get("zram") or {}
    if z.get("existe"):
        say("ZRAM                : disco %s MB, algoritmo %s, comprimido %s MB em %s MB de RAM" % (
            z.get("disco_mb", "?"), z.get("algoritmo", "?"), z.get("comprimido_mb", "?"), z.get("memoria_mb", "?")))
    else:
        say("ZRAM                : não apareceu em /sys/block/zram0 (pode estar com outro nome, ou não existe).")
    if r.get("uptime_s"):
        say("Ligado há           : %d min" % int(r["uptime_s"] // 60))
    if r.get("boot_ms"):
        say("Boot até a marca    : %.1f s (evento boot_progress)" % (r["boot_ms"] / 1000.0))
    say("")
    say("Pacotes             : %s no total, %s de sistema, %s de terceiros, %s desativados" % (
        r.get("pacotes"), r.get("sistema"), r.get("terceiros"), len(r.get("desativados") or [])))
    say("Serviços init vivos : %s" % r.get("servicos_rodando"))
    if r.get("init_contagem"):
        say("Scripts de boot     : %s" % ", ".join("%s=%s" % (k.split("/")[-2] + "/" + k.split("/")[-1], v) for k, v in r["init_contagem"].items()))
    if r.get("init_suspeito"):
        say("Boot suspeito       : %s" % ", ".join(r["init_suspeito"]))
    say("")
    say("Pilha da Play Store:")
    for item in r.get("play") or []:
        if item["situacao"] != "instalado" or item.get("enabled") not in (0, 1, None):
            say("  ! %s — %s (enabled=%s)" % (item["pacote"], item["situacao"], item.get("enabled")))
    ok = [i for i in (r.get("play") or []) if i["situacao"] == "instalado" and i.get("enabled") in (0, 1)]
    say("  %d pacotes da pilha presentes e ligados." % len(ok))
    if r.get("removidos_pilha"):
        say("  removidos do usuário (dá para restore com install-existing):")
        for nome in r["removidos_pilha"]:
            say("    %s" % nome)
    if r.get("ruins"):
        say("")
        say("Nomes de risco      : %s" % ", ".join(r["ruins"]))
    else:
        say("")
        say("Nomes de risco      : nenhum da lista conhecida (Adups, miner, spyware).")
    if r.get("permissoes"):
        say("Terceiros com permissão forte:")
        for item in r["permissoes"]:
            say("  %s → %s" % (item["pacote"], ", ".join(item["permissoes"])))
    if r.get("portas_estranhas"):
        say("Portas fora do comum: %s" % ", ".join(str(p) for p in r["portas_estranhas"][:24]))
    else:
        say("Portas              : só serviços esperados de TV/ADB, ou nenhuma leitura.")
    if r.get("crash_trecho"):
        say("")
        say("Últimos erros (trecho):")
        for ln in r["crash_trecho"].splitlines()[:12]:
            say("  " + ln[:160])


def parecer_relatorio(r):
    titulo("O que isto quer dizer")
    for frase in frases_relatorio(r):
        say(frase)
        say("")
    say("Nada foi desativado. O caminho completo é a opção 1, Primeira vez.")


def setting_get(adb, ns, chave):
    out = adb.shell("settings get %s %s" % (ns, chave), 12).strip()
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def setting_put(adb, journal, ns, chave, valor):
    if ns not in ("global", "secure", "system"):
        return False, "namespace"
    if chave not in SETTING_OK or not validar_valor(valor):
        return False, "chave ou valor fora da lista"
    antigo = setting_get(adb, ns, chave)
    if antigo == str(valor):
        return True, "já estava"
    adb.shell("settings put %s %s %s" % (ns, chave, valor), 12)
    journal.setdefault("settings", []).append({"ns": ns, "chave": chave, "antigo": antigo})
    salvar_journal(journal)
    return True, "de %s para %s" % (antigo or "vazio", valor)


# Não entra na limpeza funda. Codec, rede e a tela inicial.
KEEP_FUNDO = (
    "codec", "extractor", "omx", "stagefright", "keystore", "widevine",
    "hdmi", "cec", "tvinput", "launcher", "webview", "trichrome",
    "bluetooth", "wifi", "ethernet", "drm",
)


def candidatos_profundos(nomes, gate):
    # Serviços proprietários podem ser essenciais mesmo sem nome óbvio.
    # Não oferecer remoção em massa de pacotes desconhecidos em hardware variado.
    conhecidos = set(WAVE1) | set(WAVE2) | set(WAVE3) | set(BAD_EXACT)
    return [nome for nome in sorted(set(nomes or [])) if nome in conhecidos and not (gate and gate.motivo(nome))]


def desativar(adb, gate, journal, pacotes, onda):
    mudou = []
    pulou = []
    sistema = adb.system_names()
    instalados = set(adb.installed_map())
    for pkg in pacotes:
        if pkg in mudou:
            continue
        motivo = gate.motivo(pkg)
        if motivo:
            pulou.append((pkg, motivo))
            continue
        if pkg not in instalados and pkg not in BAD_EXACT:
            continue
        if pkg not in instalados:
            pulou.append((pkg, "não está instalado"))
            continue
        # onda automática não mexe em app que a pessoa instalou, salvo malicioso conhecido
        if pkg not in sistema and pkg not in BAD_EXACT and not any(b in pkg.lower() for b in BAD_BITS):
            pulou.append((pkg, "app de usuário, não entra na onda automática"))
            continue
        code = adb.enabled_code(pkg)
        if code in (2, 3, 4):
            pulou.append((pkg, "já estava desativado"))
            continue
        journal.setdefault("package_states", {}).setdefault(pkg, {
            "enabled": code, "removido_para_usuario": False, "quando": agora_iso(),
        })
        salvar_journal(journal)
        out = adb.shell("pm disable-user --user %s %s" % (adb.user, pkg), 20)
        low = out.lower()
        if "new state: disabled" in low:
            mudou.append(pkg)
            if pkg not in journal["disabled"]:
                journal["disabled"].append(pkg)
            salvar_journal(journal)
            escrever_rollback(adb.serial, adb.binary, journal["disabled"], journal.get("package_states"))
            say("  desativado  %s" % pkg)
            saiu = adb.shell("pm uninstall --user %s %s" % (adb.user, pkg), 20)
            if "Success" in saiu:
                journal.setdefault("removidos", []).append(pkg)
                journal.setdefault("package_states", {}).setdefault(pkg, {})["removido_para_usuario"] = True
                salvar_journal(journal)
                say("  removido para o usuário  %s (volta com Desfazer)" % pkg)
        else:
            journal.get("package_states", {}).pop(pkg, None)
            salvar_journal(journal)
            pulou.append((pkg, (out or "sem confirmação").strip().splitlines()[-1][:160]))
    journal.setdefault("ondas", []).append({
        "onda": onda, "quando": agora_iso(), "desativados": mudou,
        "pulados": [{"pacote": a, "motivo": b} for a, b in pulou[:80]],
    })
    salvar_journal(journal)
    return mudou, pulou


def candidatos_onda2(sistema):
    # Não desativar pacotes desconhecidos por substring genérica (ex.: "ota" ou "recommend").
    # Só entram indicadores de malware explicitamente conhecidos.
    return [nome for nome in sorted(sistema) if nome in BAD_EXACT or any(bit in nome.lower() for bit in BAD_BITS)]


def reativar(adb, pacotes, estados=None):
    feitos = []
    estados = estados or {}
    for pkg in pacotes:
        if not validar_pacote(pkg):
            continue
        estado = estados.get(pkg) or {}
        adb.shell("pm install-existing --user %s %s" % (adb.user, pkg), 18)
        if estado.get("enabled") == 0:
            resultado = adb.shell("pm default-state --user %s %s" % (adb.user, pkg), 18)
            if "unknown command" in resultado.lower() or "unknown" in resultado.lower():
                adb.shell("pm enable --user %s %s" % (adb.user, pkg), 18)
        else:
            adb.shell("pm enable --user %s %s" % (adb.user, pkg), 18)
        adb.shell("pm unhide --user %s %s" % (adb.user, pkg), 15)
        adb.shell("pm unsuspend --user %s %s" % (adb.user, pkg), 15)
        feitos.append(pkg)
        say("  estado anterior restaurado  %s" % pkg)
    return feitos


def saudavel(adb, home_antes, vending_antes, gms_antes):
    bc = adb._prop("sys.boot_completed")
    if bc != "1":
        return False, "o boot não chegou em sys.boot_completed=1"
    if adb.existe("com.android.systemui"):
        code = adb.enabled_code("com.android.systemui")
        if code not in (0, 1, None):
            return False, "SystemUI ficou desativado (enabled=%s)" % code
    ajustes_ok = False
    for pkg in ("com.android.tv.settings", "com.android.settings"):
        if adb.existe(pkg) and adb.enabled_code(pkg) in (0, 1, None):
            ajustes_ok = True
    if not ajustes_ok:
        return False, "o app de configurações não está utilizável"
    home = home_package(adb)
    if home_antes and not home:
        return False, "a tela inicial (HOME) sumiu"
    if home_antes and home and home != home_antes:
        return False, "a tela inicial mudou de %s para %s" % (home_antes, home)
    if vending_antes and adb.existe("com.android.vending"):
        if adb.enabled_code("com.android.vending") not in (0, 1, None):
            return False, "a Play Store foi desativada — isto não devia acontecer"
    if gms_antes and adb.existe("com.google.android.gms"):
        if adb.enabled_code("com.google.android.gms") not in (0, 1, None):
            return False, "o Google Play Services foi desativado"
    return True, "boot ok, ajustes no lugar, launcher igual, Play Store intacta"


def reiniciar_esperar(adb):
    say("Reiniciando a TV Box. A TV vai apagar. Não desligue da tomada.")
    adb._exec(["-s", adb.serial, "reboot"], 20)
    time.sleep(12)
    limite = time.time() + 210
    while time.time() < limite:
        try:
            adb.connect()
            if adb.state() == "device":
                try:
                    if adb._prop("sys.boot_completed") == "1":
                        time.sleep(8)
                        adb.refresh_user()
                        return True
                except DeviceOffline:
                    pass
        except Exception:
            pass
        falta = int(limite - time.time())
        say("  esperando a TV Box voltar… %ss" % max(falta, 0))
        time.sleep(12)
    return False


def ajustar_video(adb, journal, ram_mb, forcar=False):
    tamanho = adb.shell("wm size", 12)
    densidade = adb.shell("wm density", 12)
    phys = re.search(r"Physical size:\s*(\d+)x(\d+)", tamanho)
    override = re.search(r"Override size:\s*(\d+)x(\d+)", tamanho)
    if not phys:
        return "não li o tamanho da tela"
    pw, ph = int(phys.group(1)), int(phys.group(2))
    if max(pw, ph) < 2000:
        return "a tela física já é %dx%d. Não forcei 1080 por cima de uma saída menor." % (pw, ph)
    if not forcar and (ram_mb is None or ram_mb >= 1536):
        return "RAM real %s MB — não travei a resolução. 1080p forçado é só para TV Box fraca." % (ram_mb or "?")
    if override and override.group(2) == "1080":
        return "já existe override 1080p."
    journal.setdefault("wm", {})
    journal["wm"]["size_antes"] = tamanho.strip()
    journal["wm"]["density_antes"] = densidade.strip()
    salvar_journal(journal)
    adb.shell("wm size 1920x1080", 12)
    dens = re.search(r"Physical density:\s*(\d+)", densidade)
    if dens and int(dens.group(1)) >= 400:
        adb.shell("wm density 320", 12)
        journal["wm"]["density_set"] = 320
    journal["wm"]["size_set"] = "1920x1080"
    salvar_journal(journal)
    return "override 1920x1080 aplicado (era %dx%d). Desfaz com: wm size reset && wm density reset" % (pw, ph)


def onda_ajustes(adb, journal, ram_mb, video=True):
    pares = [
        ("global", "window_animation_scale", "0.5"),
        ("global", "transition_animation_scale", "0.5"),
        ("global", "animator_duration_scale", "0.5"),
        ("global", "network_recommendations_enabled", "0"),
        ("global", "app_standby_enabled", "1"),
    ]
    # DNS privado é preferência de rede do usuário: nunca alterar automaticamente.
    pares.append(("global", "stay_on_while_plugged_in", "3"))
    for ns, chave, valor in pares:
        ok, msg = setting_put(adb, journal, ns, chave, valor)
        say("  %s %s: %s" % (chave, "ok" if ok else "não", msg))
    adb.shell("pm trim-caches 999999999K", 40)
    say("  cache de aplicativos pedido ao sistema (pm trim-caches).")
    if video:
        say("  vídeo: " + ajustar_video(adb, journal, ram_mb, forcar=False))


def executar_ondas(adb, sim=False, sem_onda3=False):
    titulo("Debloat em ondas")
    say("Cada onda desativa, reinicia, mede de novo e só continua se a TV Box voltar.")
    say("Launcher, Play Store, GMS, WebView, teclado, HDMI e SystemUI estão fora.")
    say("YouTube da TV fica. Netflix, Kodi e o resto de fábrica só saem se você")
    say("confirmou na opção 1. Calendário, mapa e telefone podem sair: não são codec.")
    conectar_ou_explicar(adb)
    adb.refresh_user()
    home = home_package(adb)
    vend_antes = adb.existe("com.android.vending") and adb.enabled_code("com.android.vending") in (0, 1, None)
    gms_antes = adb.existe("com.google.android.gms") and adb.enabled_code("com.google.android.gms") in (0, 1, None)
    dinamicos = coletar_dinamicos(adb)
    if home:
        dinamicos.add(home)
    gate = Gate(dinamicos)
    journal = carregar_journal()
    say("Protegidos pelo uso atual: %s" % (", ".join(sorted(dinamicos)[:12]) or "—"))
    sistema = adb.system_names()
    instalados = set(adb.installed_map())

    def presentes(lista):
        vistos = []
        for pkg in lista:
            if pkg in instalados and pkg not in vistos:
                vistos.append(pkg)
        return vistos

    o1 = presentes(WAVE1)
    topo = adb.shell("dumpsys meminfo | head -n 40", 20)
    pesados = processos_pesados(topo, instalados, gate)
    extra_ram = [p["pacote"] for p in pesados if not p.get("protegido") and (p.get("kb") or 0) >= 30000]
    o2 = presentes(list(dict.fromkeys(WAVE2 + candidatos_onda2(sistema) + extra_ram)))
    o3 = presentes(WAVE3)
    if pesados:
        say("Quem mais usa RAM agora:")
        for item in pesados[:6]:
            say("  %s  %s%s" % (kb_mb(item.get("kb")), item.get("pacote"), "  (fica)" if item.get("protegido") else ""))
    say("")
    say("Onda 1, %d aplicativos (telefone, impressão, telemetria)." % len(o1))
    say("Onda 2, %d aplicativos (anúncio, recomendação, app de telefone e o que está gastando RAM à toa)." % len(o2))
    say("Onda 3, %d pacotes (Chrome, arquivos, relógio, OTA da placa) — pesa mais." % len(o3))
    say("Onda 4, ajustes reversíveis: animação, recomendações, cache e modo ligado na tomada. DNS e resolução ficam intactos.")
    if not perguntar("Executar as ondas 1, 2 e 4?", default_sim=True, forcar=True if sim else None):
        say("Cancelado. Nada foi desativado.")
        return
    fazer3 = (not sem_onda3) and perguntar(
        "Incluir a onda 3?",
        default_sim=False if not sim else True,
        forcar=(False if sem_onda3 else True) if sim else None,
    )
    base = coletar_metricas(adb, "antes")
    say("Antes: " + linha_metrica(base))
    rel = auditar(adb, falar=False)
    ram = rel.get("ram_real_mb")

    plano = [(1, o1), (2, o2)]
    if fazer3:
        plano.append((3, o3))
    fundo = [p for p in candidatos_profundos(sistema, gate) if p not in set(o1 + o2 + o3)]
    if fundo and perguntar(
        "Tem mais %d aplicativos que não são loja, vídeo nem tela inicial. Tirar em grupos de 12?" % len(fundo),
        True,
        True if sim else None,
    ):
        for i in range(0, len(fundo), 12):
            plano.append(("extra %d" % (i // 12 + 1), fundo[i:i + 12]))

    for numero, lista in plano:
        titulo("Onda %s" % numero)
        if not lista:
            say("Nada desta onda está instalado. Seguindo.")
            continue
        try:
            mudou, pulou = desativar(adb, gate, journal, lista, numero)
        except DeviceOffline as exc:
            say("Perdi o ADB no meio da onda: %s" % exc)
            say("Quando a TV Box voltar: python speedtvbox.py reverter")
            return
        say("Desativados nesta onda: %d. Recusas do portão: %d." % (len(mudou), len(pulou)))
        if not mudou:
            say("Onda vazia de mudança. Sem reinício.")
            continue
        if not reiniciar_esperar(adb):
            say("")
            say("A TV Box não voltou em cerca de 3 minutos.")
            say("Tire da tomada por 30 segundos e ligue de novo.")
            say("Se o ADB voltar, rode:  python speedtvbox.py reverter")
            say("Se não voltar, o reset físico desfaz: nada foi apagado do /system,")
            say("só desativado para o usuário. A lista está em speedtv-dados/reverter.bat (e .sh).")
            journal["falha"] = {"onda": numero, "quando": agora_iso(), "motivo": "não voltou do reboot"}
            salvar_journal(journal)
            return
        ok, motivo = saudavel(adb, home, vend_antes, gms_antes)
        depois = coletar_metricas(adb, "depois-onda-%s" % numero)
        say(linha_metrica(depois))
        if not ok:
            say("A onda %s não passou na checagem: %s" % (numero, motivo))
            say("Revertendo só esta onda e reiniciando.")
            reativar(adb, mudou, journal.get("package_states"))
            journal["disabled"] = [p for p in journal["disabled"] if p not in mudou]
            journal["removidos"] = [p for p in journal.get("removidos", []) if p not in mudou]
            for pkg in mudou:
                journal.get("package_states", {}).pop(pkg, None)
            journal["falha"] = {"onda": numero, "quando": agora_iso(), "motivo": motivo}
            salvar_journal(journal)
            escrever_rollback(adb.serial, adb.binary, journal["disabled"])
            reiniciar_esperar(adb)
            say("Parei na onda %s. As ondas anteriores continuam. Rode auditoria de novo." % numero)
            return
        say("Onda %d estável. %s" % (numero, motivo))
        # reaprende o home depois do boot
        home = home_package(adb) or home

    titulo("Onda 4 — ajustes reversíveis, sem DNS ou resolução forçados")
    onda_ajustes(adb, journal, ram, video=False)
    fim = coletar_metricas(adb, "fim")
    say(linha_metrica(fim))
    say("")
    say("Antes → agora:")
    say("  RAM livre   %s → %s" % (kb_mb(base.get("mem_available_kb")), kb_mb(fim.get("mem_available_kb"))))
    say("  processos   %s → %s" % (base.get("processos"), fim.get("processos")))
    say("  desativados %s → %s" % (base.get("desativados"), fim.get("desativados")))
    say("  /data       %s → %s" % (kb_mb(base.get("data_livre_kb")), kb_mb(fim.get("data_livre_kb"))))
    say("")
    say("Para desfazer tudo que este agente desativou: python speedtvbox.py reverter")


def reverter(adb, sim=False):
    titulo("Reverter")
    journal = carregar_journal()
    pkgs = list(dict.fromkeys((journal.get("disabled") or []) + list((journal.get("package_states") or {}).keys())))
    tem_oem = bool(journal.get("oemcrypto"))
    scripts = list(journal.get("scripts") or [])
    if not pkgs and not journal.get("settings") and not journal.get("wm") and not tem_oem and not scripts:
        say("Não há journal em %s. Nada para reverter por aqui." % garantir_dados())
        say("Se você desativou na mão, o relatório da auditoria lista os desativados.")
        return
    say("%d pacotes para reativar." % len(pkgs))
    if tem_oem:
        say("Também há biblioteca Widevine escondida. Vou tentar colocar de volta.")
    if not perguntar("Reativar e restaurar os ajustes que o SpeedTV Box mudou?", True, True if sim else None):
        return
    conectar_ou_explicar(adb)
    adb.refresh_user()
    reativar(adb, pkgs, journal.get("package_states"))
    for item in reversed(journal.get("settings") or []):
        antigo = item.get("antigo")
        ns, chave = item.get("ns"), item.get("chave")
        if ns not in ("global", "secure", "system") or not CHAVE_RE.match(chave or ""):
            continue
        if antigo in (None, "", "null"):
            adb.shell("settings delete %s %s" % (ns, chave), 12)
        elif validar_valor(antigo):
            adb.shell("settings put %s %s %s" % (ns, chave, antigo), 12)
        say("  ajuste %s restaurado" % chave)
    if journal.get("wm", {}).get("size_set"):
        adb.shell("wm size reset", 12)
        adb.shell("wm density reset", 12)
        say("  resolução e densidade voltaram ao padrão da TV Box.")
    if tem_oem:
        say(restaurar_oem(adb, tem_root(adb), journal))
    if scripts:
        root = tem_root(adb)
        for item in scripts:
            origem, bak = item.get("de") or "", item.get("bak") or ""
            if root and re.match(r"^/[\w./\-]+$", origem) and re.match(r"^/[\w./\-]+$", bak):
                adb.shell("%s -c 'mv %s %s'" % (root, bak, origem), 15)
                say("  script de volta: %s" % origem)
            else:
                say("  não consegui devolver %s" % origem)
    journal["disabled"] = []
    journal["package_states"] = {}
    journal["removidos"] = []
    journal["settings"] = []
    journal["wm"] = {}
    journal["scripts"] = []
    journal.setdefault("notas", []).append("revertido em " + agora_iso())
    salvar_journal(journal)
    escrever_rollback(adb.serial, adb.binary, [])
    if perguntar("Reiniciar para assentar a reversão?", True, True if sim else None):
        reiniciar_esperar(adb)
    say("Revertido.")


def limpar_cache(adb):
    titulo("Cache e processos parados")
    conectar_ou_explicar(adb)
    antes = coletar_metricas(adb, "cache-antes")
    say(adb.shell("pm trim-caches 999999999K", 40))
    say(adb.shell("am kill-all", 20))
    depois = coletar_metricas(adb, "cache-depois")
    say(linha_metrica(antes))
    say(linha_metrica(depois))
    say("Isso não apaga login. Só cache e processo que estava em segundo plano.")


def tem_root(adb):
    for cmd in ("su -c id", "su 0 id"):
        out = adb.shell(cmd, 12)
        if "uid=0" in out:
            return cmd.split()[0] if cmd.startswith("su ") else "su"
    return None


def limpar_zram(adb, sim=False):
    titulo("ZRAM")
    conectar_ou_explicar(adb)
    info = ler_zram(adb)
    if info.get("existe"):
        say("Disco %s MB, em uso comprimido %s MB, RAM ocupada pelo ZRAM %s MB, algoritmo %s." % (
            info.get("disco_mb", "?"), info.get("comprimido_mb", "?"),
            info.get("memoria_mb", "?"), info.get("algoritmo", "?")))
    else:
        say("Não achei /sys/block/zram0.")
    say(info.get("swaps") or "")
    root = tem_root(adb)
    say(adb.shell("pm trim-caches 999999999K", 30))
    say(adb.shell("am kill-all", 15))
    if not root:
        say("")
        say("Sem root. O Android não deixa esvaziar o ZRAM pelo shell comum.")
        say("O que deu para fazer sem root: trim-caches e kill-all.")
        say("Não vou tentar swapoff — sem su isso falha ou, pior, deixa a troca desligada.")
        return
    if not perguntar("Tenho root. Esvaziar o ZRAM agora? A imagem pode engasgar por alguns segundos.", False, False if sim else None):
        say("ZRAM deixado como está.")
        return
    cmd = (
        "swapoff /dev/block/zram0; swapoff /dev/block/zram1; "
        "echo 3 > /proc/sys/vm/drop_caches; "
        "swapon /dev/block/zram0"
    )
    say(adb.shell("%s -c '%s'" % (root, cmd), 30))
    say("Estado agora:")
    say(adb.shell("cat /proc/swaps", 12))
    if "zram" not in adb.shell("cat /proc/swaps", 12):
        say("O ZRAM não voltou. Tentando de novo.")
        adb.shell("%s -c 'swapon /dev/block/zram0'" % root, 15)


def ajustar_rede(adb, sim=False):
    titulo("Rede")
    conectar_ou_explicar(adb)
    journal = carregar_journal()
    say("Vou aplicar apenas os ajustes gerais reversíveis. Não altero o DNS, o Bluetooth ou a política de sono do Wi-Fi.")
    if not perguntar("Aplicar?", True, True if sim else None):
        return
    onda_ajustes(adb, journal, ram_mb=99999, video=False)
    modo = setting_get(adb, "global", "captive_portal_mode")
    say("Portal cativo (captive_portal_mode) está '%s'." % (modo or "padrão"))
    say("Em TV Box chinesa isso às vezes marca a rede como 'sem internet' mesmo com internet.")
    if perguntar("Desligar a checagem de portal cativo?", False, False if sim else None):
        ok, msg = setting_put(adb, journal, "global", "captive_portal_mode", "0")
        say(msg if ok else "não apliquei: " + msg)
    say("Feito. O DNS e as opções de rádio permaneceram como estavam.")


def forcar_1080(adb, sim=False):
    titulo("Vídeo 1080p")
    conectar_ou_explicar(adb)
    rel = auditar(adb, falar=False)
    say("RAM real estimada: %s MB." % (rel.get("ram_real_mb") or "?"))
    say(adb.shell("wm size", 12))
    say(adb.shell("wm density", 12))
    if not perguntar("Aplicar override 1920x1080 se a saída for 4K?", True, True if sim else None):
        return
    journal = carregar_journal()
    say(ajustar_video(adb, journal, rel.get("ram_real_mb"), forcar=True))


def analisar_boot(adb, sim=False):
    titulo("Boot — leitura e parecer")
    say("Vou ler serviço, memória e porta em escuta. O miolo do kernel não vai para a tela.")
    say("No fim eu digo o que é normal, o que pesa, e pergunto antes de fechar qualquer coisa.")
    conectar_ou_explicar(adb)
    props = adb.getprop_all()
    vivos = sorted(k[len("init.svc."):] for k, v in props.items() if k.startswith("init.svc.") and v == "running")
    suspeitos = []
    for pasta in ("/system/etc/init", "/vendor/etc/init", "/odm/etc/init", "/product/etc/init", "/system/etc/init.d"):
        lista = adb.shell("ls -1 %s 2>/dev/null" % pasta, 12)
        for nome in lista.splitlines():
            nome = nome.strip()
            if nome and init_e_suspeito(nome):
                suspeitos.append("%s/%s" % (pasta, nome))
    topo = adb.shell("dumpsys meminfo | head -n 40", 25)
    apps = parse_rss(topo)
    tcp = adb.shell("grep ' 0A ' /proc/net/tcp /proc/net/tcp6 2>/dev/null | head -n 80", 12)
    portas, estranhas = varredura_portas(tcp)
    placa = props.get("ro.board.platform") or props.get("ro.hardware") or "?"
    frases = []
    frases.append("Placa %s. %d serviços de boot ligados. Isso é o Android de pé, não é uma lista de vírus." % (placa, len(vivos)))
    if any(s in vivos for s in ("mediadrm", "drm")) or any("widevine" in s for s in vivos):
        frases.append("O serviço de DRM está rodando. Isso não prova Widevine L1. Prova que a pilha de DRM subiu.")
    if "update_engine" in vivos:
        frases.append("update_engine ligado é o atualizador normal do Android, não é Adups.")
    if suspeitos:
        frases.append("Script de boot com nome de risco: " + ", ".join(suspeitos))
    else:
        frases.append("Nenhum script de boot com nome de Adups, miner ou backdoor. bootanim é animação de ligar, não é OTA.")
    if estranhas:
        frases.append("Porta escutando fora do comum: " + ", ".join(str(p) for p in estranhas) + ".")
    elif portas:
        frases.append("Portas em escuta: " + ", ".join(str(p) for p in portas) + ". O resto que aparecia antes era app saindo para a internet, não serviço aberto.")
    else:
        frases.append("Não li porta em escuta. Isso não significa que a rede está fechada.")
    pesados = []
    for app in apps[:8]:
        mb = app["kb"] // 1024
        if mb < 40:
            continue
        estado = "aberto na tela" if app["aberto"] else "em segundo plano"
        pesados.append("%s com %d MB (%s)" % (app["nome"], mb, estado))
    if pesados:
        frases.append("Quem mais come RAM: " + "; ".join(pesados[:5]) + ".")
    titulo("O que isto quer dizer")
    for frase in frases:
        say(frase)
        say("")
    say("Consultando o Gemini para um parecer curto…")
    parecer = gemini_leitura("boot, RAM e portas em escuta", "\n".join(frases))
    if parecer:
        say(parecer.strip())
        say("")
    else:
        say("Sem parecer do Gemini. O resumo acima já é a leitura.")
        say("")
    oferecer_alivio(adb, apps, sim)
    bruto = "SERVIÇOS\n" + ", ".join(vivos) + "\n\nSUSPEITOS\n" + "\n".join(suspeitos) + "\n\nMEMINFO\n" + topo + "\n\nPORTAS EM ESCUTA\n" + ", ".join(str(p) for p in portas)
    log = anexar_log("boot", bruto, "\n".join(frases) + ("\n\nGEMINI\n" + parecer if parecer else ""))
    dizer_onde(log)


def oferecer_alivio(adb, apps, sim):
    """Fecha ou desativa só o que não é sistema, e só se a pessoa disser sim."""
    gate = Gate(coletar_dinamicos(adb))
    journal = carregar_journal()
    viu = False
    for app in apps:
        nome = app["nome"]
        mb = app["kb"] // 1024
        if mb < 70 or not validar_pacote(nome):
            continue
        if gate.motivo(nome):
            continue
        if nome.startswith((
            "com.google.android.gms", "com.google.android.gsf", "com.android.vending",
            "com.android.systemui", "com.google.android.inputmethod", "com.android.inputmethod",
            "com.android.webview", "com.google.android.webview", "com.google.android.apps.mediashell",
            "com.android.tv.settings", "com.google.android.ext.", "com.android.permissioncontroller",
            "com.google.android.permissioncontroller", "com.android.providers.", "com.google.process.",
            "com.android.networkstack", "com.droidlogic", "android.",
        )):
            continue
        viu = True
        if app["aberto"]:
            say("%s está com %d MB e está na tela. Não fecho sozinho." % (nome, mb))
            if perguntar("Fechar mesmo assim?", False, False if sim else None):
                adb.shell("am force-stop " + nome, 15)
                say("  fechei " + nome)
            continue
        janela = any(b in nome.lower() for b in ("movewindow", "floatwindow", "floater"))
        if janela:
            say("%s ocupa %d MB e parece janela flutuante de fábrica, não é o Android." % (nome, mb))
            if perguntar("Desativar %s? Dá para reverter." % nome, False, False if sim else None):
                desativar(adb, gate, journal, [nome], "boot")
            continue
        say("%s está com %d MB em segundo plano." % (nome, mb))
        if perguntar("Fechar agora? Não desinstala e não apaga login.", False, False if sim else None):
            adb.shell("am force-stop " + nome, 15)
            say("  fechei " + nome)
    if not viu:
        say("Nenhum app de terceiro grande o bastante para eu oferecer fechar.")


def gemini_leitura(assunto, resumo):
    chave = api_key()
    if not chave or not resumo:
        return None
    prompt = (
        "Você é o técnico do SpeedTV Box, no Termux, falando com o dono de uma TV Box. "
        "Responda em português, no máximo 8 linhas, sem lista de comando cru. "
        "Diga o que o exame significa, o que é normal, e no máximo uma ação segura. "
        "Não peça pm uninstall. Não peça desligar gms, vending, systemui, launcher, webview ou hdmi. "
        "Se não houver o que fazer, diga isso claramente.\n\n"
        "ASSUNTO: %s\n\nEXAME:\n%s" % (assunto, resumo[:5000])
    )
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % MODELO
    corpo = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700},
    }
    texto, err = _post_json(url, corpo, chave, timeout=25)
    if not texto:
        if err:
            say("Gemini não respondeu (%s). Sigo sem ele." % err[:160])
        return None
    return _texto_resposta(texto)


def varrer_virus(adb, sim=False):
    titulo("Pacotes suspeitos")
    conectar_ou_explicar(adb)
    rel = auditar(adb, falar=False)
    ruins = [r for r in rel.get("ruins") or [] if "removido" not in r]
    perms = rel.get("permissoes") or []
    if not ruins and not perms:
        say("Nada na lista de nomes conhecidos e nenhum terceiro com permissão de instalação, admin ou SMS.")
        say("Isso não é um antivírus. É uma peneira de nome, permissão, porta e script de boot.")
        return
    if ruins:
        say("Nomes conhecidos de lixo/spyware:")
        for nome in ruins:
            say("  %s" % nome)
    if perms:
        say("Terceiros com permissão forte (pode ser legítimo, leia o nome):")
        for item in perms:
            say("  %s → %s" % (item["pacote"], ", ".join(item["permissoes"])))
    alvos = [n for n in ruins if validar_pacote(n)]
    if not alvos:
        return
    if not perguntar("Desativar estes nomes conhecidos (dá para reverter)?", False, False if sim else None):
        say("Só o relatório. Nada desativado.")
        return
    gate = Gate(coletar_dinamicos(adb))
    journal = carregar_journal()
    desativar(adb, gate, journal, alvos, "virus")


def iniciar_pacote(adb, ref):
    pkg = pacote_de(ref)
    if not validar_pacote(pkg):
        return {"erro": "pacote inválido"}
    adb.shell("logcat -c", 15)
    saidas = []
    if "/" in ref:
        saidas.append(adb.shell("am start -n %s" % ref, 18))
    else:
        for comp in VENDING_ACTIVITIES if pkg == "com.android.vending" else []:
            saidas.append(comp + " → " + adb.shell("am start -n %s" % comp, 18))
            if "Error" not in saidas[-1] and "does not exist" not in saidas[-1]:
                break
        else:
            if pkg != "com.android.vending" or all("Error" in s or "does not exist" in s for s in saidas):
                resolved = adb.shell(
                    "cmd package resolve-activity --brief -a android.intent.action.MAIN "
                    "-c android.intent.category.LEANBACK_LAUNCHER %s" % pkg,
                    18,
                )
                comp = ultimo_componente(resolved)
                if not comp:
                    resolved = adb.shell(
                        "cmd package resolve-activity --brief -a android.intent.action.MAIN "
                        "-c android.intent.category.LAUNCHER %s" % pkg,
                        18,
                    )
                    comp = ultimo_componente(resolved)
                if comp:
                    saidas.append(adb.shell("am start -n %s" % comp, 18))
                else:
                    saidas.append(adb.shell(
                        "monkey -p %s -c android.intent.category.LEANBACK_LAUNCHER 1" % pkg, 18))
                    if "No activities" in saidas[-1] or "aborted" in saidas[-1].lower():
                        saidas.append(adb.shell(
                            "monkey -p %s -c android.intent.category.LAUNCHER 1" % pkg, 18))
    time.sleep(4)
    log = adb.shell("logcat -d -t 350", 25)
    foco = adb.shell("dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity' | head -n 12", 18)
    ps = adb.shell("ps -A 2>/dev/null | grep -m 5 %s" % pkg, 15)
    if not ps.strip():
        ps = adb.shell("ps | grep -m 5 %s" % pkg, 15)
    fatal = "FATAL EXCEPTION" in log and pkg.split(".")[-1] in log
    aberto = (pkg in (foco or "")) or (bool(ps.strip()) and "Error" not in "\n".join(saidas) and not fatal)
    return {
        "saidas": saidas,
        "log": log,
        "foco": foco,
        "processo": ps.strip(),
        "aberto": aberto,
        "fatal": fatal,
    }


def classificar_log(log):
    texto = log or ""
    low = texto.lower()
    tags = []
    regras = [
        ("webview", ("missingwebview", "awbrowserprocess", "trichromelibrary", "webviewfactory", "failed to load webview")),
        ("ssl_hora", ("certpathvalidator", "sslhandshake", "trust anchor", "current time")),
        ("atividade", ("activitynotfound", "unable to resolve", "does not exist")),
        ("gms", ("googleplayservicesnotavailable", "api_unavailable", "securityexception")),
        ("atualizacao", ("resources$notfound", "incompatibleclasschange", "verifyerror")),
        ("rede", ("unknownhost", "failed to connect", "enotfound")),
        ("conta", ("no account", "signin", "auth_failure")),
    ]
    for nome, chaves in regras:
        if any(c in low for c in chaves):
            tags.append(nome)
    if "FATAL EXCEPTION" in texto and not tags:
        tags.append("crash")
    return tags


def restaurar_pilha(adb, pacote):
    if not validar_pacote(pacote):
        return "nome inválido"
    passos = []
    passos.append(adb.shell("pm enable %s" % pacote, 15))
    passos.append(adb.shell("pm unhide --user %s %s" % (adb.user, pacote), 12))
    passos.append(adb.shell("pm unsuspend --user %s %s" % (adb.user, pacote), 12))
    inst = adb.shell("cmd package install-existing --user %s %s" % (adb.user, pacote), 25)
    passos.append(inst)
    return " | ".join(p.strip().splitlines()[-1][:120] for p in passos if p.strip())


def limpar_cache_pacote(adb, pacote):
    if pacote not in CLEAR_CACHE_OK:
        return "fora da lista"
    out = adb.shell("pm clear --cache-only %s" % pacote, 20)
    if "Error" in out or "Unknown" in out or not out.strip():
        # algumas versões não têm --cache-only; não caio para pm clear (isso apaga dados)
        return out.strip()[:200] or "sem --cache-only neste Android"
    return out.strip()[:200]


def desatualizar(adb, pacote):
    if pacote not in UPDATES_OK:
        return "não desatualizo este pacote"
    return adb.shell("cmd package uninstall-system-updates %s" % pacote, 40).strip()[:300]


def playstore(adb, sim=False):
    titulo("Play Store — diagnóstico e reparo")
    say("Não desativo nada aqui. A ordem é: religar a pilha, WebView, cache,")
    say("desatualizar o que estiver quebrado, e só então apagar os dados da loja.")
    say("Dados do Play Services (GMS) não são apagados sozinhos — isso desloga a conta.")
    conectar_ou_explicar(adb)
    adb.refresh_user()
    journal = carregar_journal()

    say("")
    say("1) Como está agora, antes de mexer.")
    base = iniciar_pacote(adb, "com.android.vending")
    tags = classificar_log(base.get("log", ""))
    say("  tentativa inicial: %s" % ("apareceu em foco ou processo" if base.get("aberto") else "não ficou aberta"))
    if tags:
        say("  pista no log: %s" % ", ".join(tags))
    anexar_log("playstore-antes", json.dumps({
        "saidas": base.get("saidas"),
        "foco": base.get("foco"),
        "tags": tags,
        "log": (base.get("log") or "")[:8000],
    }, ensure_ascii=False, indent=2))

    say("")
    say("2) Hora automática e pilha Google.")
    setting_put(adb, journal, "global", "auto_time", "1")
    setting_put(adb, journal, "global", "auto_time_zone", "1")
    say("  hora do aparelho: " + adb.shell("date", 10).strip())
    removidos = adb.uninstalled_names()
    instalados = set(adb.installed_map())
    for pkg in dict.fromkeys(PLAY_STACK):
        if pkg in instalados or pkg in removidos:
            resumo = restaurar_pilha(adb, pkg)
            code = adb.enabled_code(pkg) if pkg in set(adb.installed_map()) else None
            say("  %s → enabled=%s | %s" % (pkg, code, resumo[:140]))

    say("")
    say("3) WebView, que é a causa mais comum da loja fechar na hora.")
    web = adb.shell("dumpsys webviewupdate | head -n 40", 18)
    say(web.strip()[:600] or "  sem dumpsys webviewupdate")
    provedor = setting_get(adb, "global", "webview_provider")
    say("  webview_provider: %s" % (provedor or "vazio"))
    for pkg in ("com.google.android.webview", "com.android.webview", "com.google.android.trichromelibrary"):
        if adb.existe(pkg) or pkg in removidos:
            say("  " + pkg + " → " + restaurar_pilha(adb, pkg)[:160])
    if "webview" in tags or "null" in (provedor or "").lower():
        say("  pista de WebView. Vou tirar a atualização por cima da versão de fábrica.")
        for pkg in ("com.google.android.webview", "com.android.webview", "com.google.android.trichromelibrary"):
            if adb.existe(pkg):
                say("  desatualizar %s: %s" % (pkg, desatualizar(adb, pkg)[:180]))

    say("")
    say("4) Cache da loja e do GMS, sem apagar conta.")
    for pkg in ("com.android.vending", "com.google.android.gms", "com.google.android.gsf"):
        if adb.existe(pkg):
            say("  cache %s: %s" % (pkg, limpar_cache_pacote(adb, pkg)[:160]))

    say("")
    say("5) Nova tentativa de abrir.")
    tenta = iniciar_pacote(adb, "com.android.vending")
    tags2 = classificar_log(tenta.get("log", ""))
    say("  aberta: %s" % ("sim" if tenta.get("aberto") else "não"))
    if tags2:
        say("  pista: %s" % ", ".join(tags2))
    if tenta.get("aberto") and not tenta.get("fatal"):
        say("")
        say("A Play Store chegou a abrir. Se a tela ainda ficar em branco, o próximo passo")
        say("é entrar na conta Google — isso a loja pede sozinha.")
        anexar_log("playstore-ok", tenta.get("log") or "")
        return

    say("")
    say("6) Ainda fechou. Vou tirar a atualização da própria loja (volta a versão de fábrica).")
    if adb.existe("com.android.vending"):
        say("  " + desatualizar(adb, "com.android.vending")[:300])
        restaurar_pilha(adb, "com.android.vending")
    tenta = iniciar_pacote(adb, "com.android.vending")
    if tenta.get("aberto") and not tenta.get("fatal"):
        say("Abriu depois de desatualizar a loja.")
        return

    say("")
    say("7) Apagar só os dados da Play Store (não desloga o GMS).")
    if perguntar("Apagar dados de com.android.vending?", True, True if sim else None):
        say(adb.shell("pm clear com.android.vending", 25)[:300])
        tenta = iniciar_pacote(adb, "com.android.vending")
        if tenta.get("aberto") and not tenta.get("fatal"):
            say("Abriu depois de limpar os dados da loja.")
            return

    tags3 = classificar_log(tenta.get("log", ""))
    if "ssl_hora" in tags3 or "rede" in tags3:
        say("O log sugere problema de certificado ou rede. O DNS privado pode ser testado, mas muda a configuração de rede.")
        if perguntar("Trocar o DNS privado para dns.google agora?", False, False if sim else None):
            setting_put(adb, journal, "global", "private_dns_mode", "hostname")
            setting_put(adb, journal, "global", "private_dns_specifier", "dns.google")

    say("")
    say("8) Reinício e teste de novo. Várias falhas de GMS só assentam depois do boot.")
    if perguntar("Reiniciar a TV Box agora?", True, True if sim else None):
        if reiniciar_esperar(adb):
            tenta = iniciar_pacote(adb, "com.android.vending")
            if tenta.get("aberto") and not tenta.get("fatal"):
                say("Abriu depois do reinício.")
                return
        else:
            say("Não voltou do reinício a tempo. Quando voltar, rode de novo: python speedtvbox.py playstore")
            return

    say("")
    say("9) Gemini olha o log e só pode pedir ação da lista branca.")
    contexto = {
        "tags": classificar_log(tenta.get("log", "")),
        "saidas": tenta.get("saidas"),
        "foco": tenta.get("foco"),
        "log": (tenta.get("log") or "")[-6000:],
        "webview": web[:1500],
    }
    acao = gemini_play(contexto)
    if not acao:
        say("Sem resposta útil do Gemini. O log ficou em speedtv-dados.")
        anexar_log("playstore-log", tenta.get("log") or "")
        imprimir_resto_play(tenta)
        return
    say("Diagnóstico: %s" % acao.get("diagnostico", "—"))
    aplicar_acoes_play(adb, journal, acao.get("acoes") or [], sim)
    tenta = iniciar_pacote(adb, "com.android.vending")
    if tenta.get("aberto") and not tenta.get("fatal"):
        say("Abriu depois das ações do Gemini.")
        return
    say("Ainda não ficou aberta.")
    imprimir_resto_play(tenta)
    anexar_log("playstore-log", tenta.get("log") or "")


def imprimir_resto_play(tenta):
    say("Trecho do log:")
    linhas = (tenta.get("log") or "").splitlines()
    for ln in linhas[-25:]:
        say("  " + ln[:170])
    say("")
    say("O que ainda vale testar na mão, se este fluxo não bastou:")
    say("  • Confirme conta Google em Configurações. Sem conta a loja abre na tela de login, não 'não abre'.")
    say("  • TV Box sem certificação Google (a maioria das MXQ) nunca atualiza GMS direito.")
    say("  • Último recurso, e desloga a conta: pm clear com.google.android.gms")
    say("    O SpeedTV Box não faz isso sozinho.")


def aplicar_acoes_play(adb, journal, acoes, sim):
    if not isinstance(acoes, list):
        return
    for acao in acoes[:8]:
        if not isinstance(acao, dict):
            continue
        op = str(acao.get("op") or "")
        pkg = str(acao.get("pacote") or "")
        if op in ("enable", "unhide", "unsuspend", "install_existing"):
            if pkg not in PLAY_STACK and pkg not in UPDATES_OK:
                say("  ignorei %s em %s (fora da pilha)" % (op, pkg))
                continue
            say("  %s %s → %s" % (op, pkg, restaurar_pilha(adb, pkg)[:160]))
        elif op == "clear_cache":
            say("  cache %s: %s" % (pkg, limpar_cache_pacote(adb, pkg)[:160]))
        elif op == "clear_data":
            if pkg not in CLEAR_DATA_OK:
                say("  não apago dados de %s" % pkg)
                continue
            if perguntar("Gemini pediu para apagar dados de %s. Confirma?" % pkg, False, True if sim else None):
                say(adb.shell("pm clear %s" % pkg, 25)[:200])
        elif op == "uninstall_updates":
            say("  desatualizar %s: %s" % (pkg, desatualizar(adb, pkg)[:200]))
        elif op == "setting":
            ok, msg = setting_put(
                adb, journal,
                str(acao.get("namespace") or "global"),
                str(acao.get("chave") or ""),
                str(acao.get("valor") or ""),
            )
            say("  ajuste: %s" % msg if ok else "  ajuste recusado (%s)" % msg)
        elif op == "reboot":
            if perguntar("Gemini pediu reinício. Faço?", True, True if sim else None):
                reiniciar_esperar(adb)
        elif op == "disable":
            say("  ignorei pedido de desativar durante o reparo da loja.")
        else:
            say("  operação desconhecida, ignorei: %s" % op)


def api_key():
    return (
        os.environ.get("SPEEDTV_API_KEY", "").strip()
        or os.environ.get("NEXO_API_KEY", "").strip()
        or API_KEY_PADRAO
    )


def dispositivo():
    return (
        os.environ.get("SPEEDTV_DEVICE", "").strip()
        or os.environ.get("NEXO_DEVICE", "").strip()
        or DISPOSITIVO_PADRAO
    )


def gemini_texto(prompt):
    chave = api_key()
    if not chave:
        return None
    erros = []
    for modelo in MODELOS_RESERVA:
        url_i = "https://generativelanguage.googleapis.com/v1beta/interactions"
        corpo_i = {"model": modelo, "input": prompt, "generation_config": {"thinking_level": "low"}}
        texto, err = _post_json(url_i, corpo_i, chave)
        if texto:
            achado = _texto_resposta(texto)
            if achado:
                return achado
        elif err:
            erros.append(modelo + " interactions: " + err)
        url_g = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % modelo
        corpo_g = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
        }
        texto, err = _post_json(url_g, corpo_g, chave)
        if texto:
            achado = _texto_resposta(texto)
            if achado:
                return achado
        elif err:
            erros.append(modelo + " generate: " + err)
    if erros:
        say("Gemini indisponível: " + erros[-1][:240])
    return None


def _post_json(url, corpo, chave, timeout=70):
    data = json.dumps(corpo).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "x-goog-api-key": chave},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace"), None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        return None, "HTTP %s %s" % (exc.code, body)
    except Exception as exc:
        return None, str(exc)[:240]


def _texto_resposta(raw):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:4000]
    if isinstance(data, dict):
        for chave in ("output_text", "outputText"):
            if isinstance(data.get(chave), str) and data[chave].strip():
                return data[chave]
        inter = data.get("interaction") or data.get("output")
        if isinstance(inter, dict):
            for chave in ("output_text", "outputText", "text"):
                if isinstance(inter.get(chave), str) and inter[chave].strip():
                    return inter[chave]
        outputs = data.get("outputs") or data.get("steps")
        if isinstance(outputs, list):
            pedacos = []
            for item in outputs:
                if isinstance(item, dict):
                    if isinstance(item.get("text"), str):
                        pedacos.append(item["text"])
                    content = item.get("content")
                    if isinstance(content, str):
                        pedacos.append(content)
            if pedacos:
                return "\n".join(pedacos)
        cand = data.get("candidates") or []
        if cand and isinstance(cand, list):
            content = (cand[0] or {}).get("content") or {}
            if isinstance(content, list):
                parts = content
            else:
                parts = content.get("parts") or []
            textos = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")]
            if textos:
                return "\n".join(textos)
    return None


def gemini_play(contexto):
    prompt = (
        "Você repara Google Play Store em TV Box Android depois de debloat. "
        "Responda APENAS JSON com as chaves diagnostico (string curta em português), "
        "confianca (alta|media|baixa) e acoes (lista). "
        "Cada ação tem op em: enable, unhide, unsuspend, install_existing, clear_cache, "
        "clear_data, uninstall_updates, setting, reboot. "
        "pacote só pode ser da pilha: %s. "
        "clear_data só em com.android.vending. uninstall_updates só em vending ou webview ou trichrome. "
        "setting só com namespace global|secure|system e chave desta lista: %s. "
        "Nunca peça disable, uninstall, pm clear de gms, nem pacote fora da lista. "
        "Se o log não der para agir, devolva acoes vazias.\n\n"
        "CONTEXTO:\n%s"
    ) % (", ".join(dict.fromkeys(PLAY_STACK)), ", ".join(sorted(SETTING_OK)), json.dumps(contexto, ensure_ascii=False)[:14000])
    texto = gemini_texto(prompt)
    if not texto:
        return None
    try:
        data = extrair_json(texto)
    except Exception:
        say("Gemini não devolveu JSON. Trecho: " + texto[:300])
        return None
    if not isinstance(data, dict):
        return None
    return data


def perguntar_gemini(adb, pergunta):
    titulo("Gemini com o contexto desta TV Box")
    conectar_ou_explicar(adb)
    rel_path = garantir_dados() / "auditoria-ultima.json"
    if rel_path.is_file():
        ctx = rel_path.read_text(encoding="utf-8")[:12000]
    else:
        say("Sem auditoria salva. Fazendo uma agora, em leitura.")
        ctx = json.dumps(auditar(adb, falar=False), ensure_ascii=False)[:12000]
    prompt = (
        "Você é o técnico do SpeedTV Box, agente de TV Box. Responda em português, direto, "
        "sem desinstalar sistema e sem sugerir pm uninstall. Disable-user só se for "
        "bloat óbvio e nunca em gms, vending, systemui, launcher, webview, tvinput, hdmi, katniss. "
        "A pessoa perguntou:\n%s\n\nAuditoria JSON:\n%s" % (pergunta, ctx)
    )
    texto = gemini_texto(prompt)
    if not texto:
        say("Não consegui falar com o Gemini 3.8. O resto do agente funciona sem ele.")
        return
    say(texto)


def conectar_ou_explicar(adb):
    say("Conectando em %s …" % adb.serial)
    out = adb.connect()
    estado = adb.state()
    if estado == "device":
        adb.refresh_user()
        say("Conectado. Usuário Android atual: %s" % adb.user)
        return
    say(out)
    say("Estado: %s" % (estado or "sem resposta"))
    if "unauthorized" in (out + estado).lower():
        say("A TV está pedindo autorização. Olhe a tela e aceite 'Permitir depuração USB'.")
        say("Marque 'sempre deste computador'. Quando aceitar, rode de novo.")
        raise SystemExit(2)
    sdk = ""
    try:
        sdk = adb._prop("ro.build.version.sdk")
    except Exception:
        sdk = ""
    say("")
    say("Não entrei. Na TV Box: Configurações → Sobre → clicar 7 vezes em Compilação,")
    say("depois Opções do desenvolvedor → Depuração USB. Em Android 11 ou mais novo")
    say("também existe 'Depuração sem fio': parear com código e só então a porta 5555 abre.")
    if perguntar("Tentar parear agora (código na tela da TV)?", False, False):
        try:
            alvo = input("IP:porta de pareamento (não é a 5555): ").strip()
            code = input("Código: ").strip()
        except EOFError:
            raise SystemExit(2)
        if not re.match(r"^[\d.]+:\d+$", alvo) or not re.match(r"^\d{4,8}$", code):
            say("Formato inválido. Esperava algo como 192.168.1.88:37123 e um código numérico.")
            raise SystemExit(2)
        say(adb.pair(alvo, code))
        say(adb.connect())
        if adb.state() == "device":
            adb.refresh_user()
            say("Pareado e conectado.")
            return
    if sdk:
        say("SDK lido mesmo assim: %s" % sdk)
    raise SystemExit(2)


def comparar():
    titulo("Antes e depois")
    path = garantir_dados() / "metricas.jsonl"
    if not path.is_file():
        say("Ainda não há medidas. Rode a auditoria ou o debloat.")
        return
    linhas = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for ln in linhas[-30:]:
        try:
            item = json.loads(ln)
        except json.JSONDecodeError:
            continue
        say("%s  %s" % (item.get("quando", ""), linha_metrica(item)))
    if len(linhas) >= 2:
        try:
            primeiro = json.loads(linhas[0])
            ultimo = json.loads(linhas[-1])
            say("")
            say("Da primeira medida até a última: RAM livre %s → %s, processos %s → %s." % (
                kb_mb(primeiro.get("mem_available_kb")),
                kb_mb(ultimo.get("mem_available_kb")),
                primeiro.get("processos"),
                ultimo.get("processos"),
            ))
        except json.JSONDecodeError:
            pass


def status_ram(adb):
    titulo("RAM agora")
    conectar_ou_explicar(adb)
    m = coletar_metricas(adb, "agora")
    say(linha_metrica(m))
    topo = adb.shell("dumpsys meminfo | head -n 18", 20)
    apps = parse_rss(topo)
    if apps:
        say("Quem está comendo memória:")
        for app in apps[:5]:
            uso = "aberto na tela" if app["aberto"] else "segundo plano"
            say("  %s — %d MB (%s)" % (app["nome"], app["kb"] // 1024, uso))
        say("Play Store, GMS e SystemUI pesam e ficam. App de terceiro em segundo plano dá para fechar no exame de boot.")
    else:
        say(topo)
    log = anexar_log("ram", topo, linha_metrica(m))
    dizer_onde(log)


def abrir_cmd(adb, nome):
    titulo("Abrir " + nome)
    conectar_ou_explicar(adb)
    if not validar_pacote(nome):
        say("Pacote inválido.")
        return
    res = iniciar_pacote(adb, nome)
    say("Ficou em pé: %s" % ("sim" if res.get("aberto") else "não"))
    say("Foco: %s" % (res.get("foco") or "—").strip()[:300])
    say("Processo: %s" % (res.get("processo") or "—"))
    for s in res.get("saidas") or []:
        say(s.strip()[:300])
    path = anexar_log("abrir-" + nome.replace(".", "_"), res.get("log") or "", "abrir %s ficou=%s" % (nome, "sim" if res.get("aberto") else "não"))
    dizer_onde(path)
    tags = classificar_log(res.get("log") or "")
    if tags:
        say("Pistas: %s" % ", ".join(tags))


def pasta_visivel():
    """Pasta que a pessoa abre no app Arquivos: Download/SpeedTV."""
    home = os.environ.get("HOME") or ""
    destinos = []
    if home:
        destinos.append(Path(home) / "storage" / "downloads" / "SpeedTV")
        destinos.append(Path(home) / "storage" / "shared" / "Download" / "SpeedTV")
        destinos.append(Path(home) / "storage" / "shared" / "Downloads" / "SpeedTV")
    destinos.append(Path("/storage/emulated/0/Download/SpeedTV"))
    destinos.append(Path("/sdcard/Download/SpeedTV"))
    for pasta in destinos:
        try:
            pasta.mkdir(parents=True, exist_ok=True)
            prova = pasta / ".ok"
            prova.write_text("1", encoding="utf-8")
            prova.unlink()
            return pasta
        except Exception:
            continue
    return None


def publicar_relatorio(path):
    """Copia para Download/SpeedTV, a pasta que abre no app Arquivos."""
    nome = Path(path).name
    pasta = pasta_visivel()
    if not pasta:
        return None
    try:
        destino = pasta / nome
        shutil.copy2(path, destino)
        return destino
    except Exception:
        return None


OEM_RE = re.compile(
    r"^/(vendor|system|odm|product|system_ext)(/[\w.\-]+)*/liboemcrypto\.so(\.(?:nexo|speedtv)-bak)?$"
)


def caminho_oem_ok(path):
    return bool(path) and bool(OEM_RE.match(path))


def particao_de(path):
    for prefixo in ("/vendor", "/odm", "/product", "/system_ext", "/system"):
        if path.startswith(prefixo + "/"):
            return prefixo
    return "/system"


def listar_oemcrypto(adb):
    cmd = (
        "for f in "
        "/vendor/lib/liboemcrypto.so /vendor/lib64/liboemcrypto.so "
        "/vendor/lib/mediadrm/liboemcrypto.so /vendor/lib64/mediadrm/liboemcrypto.so "
        "/system/lib/liboemcrypto.so /system/lib64/liboemcrypto.so "
        "/system/vendor/lib/liboemcrypto.so /system/vendor/lib64/liboemcrypto.so "
        "/odm/lib/liboemcrypto.so /odm/lib64/liboemcrypto.so "
        "/product/lib/liboemcrypto.so /product/lib64/liboemcrypto.so "
        "/vendor/lib/liboemcrypto.so.nexo-bak /vendor/lib64/liboemcrypto.so.nexo-bak "
        "/vendor/lib/liboemcrypto.so.speedtv-bak /vendor/lib64/liboemcrypto.so.speedtv-bak "
        "/system/lib/liboemcrypto.so.nexo-bak /system/lib64/liboemcrypto.so.nexo-bak "
        "/system/lib/liboemcrypto.so.speedtv-bak /system/lib64/liboemcrypto.so.speedtv-bak "
        "/odm/lib/liboemcrypto.so.nexo-bak /odm/lib64/liboemcrypto.so.nexo-bak "
        "/odm/lib/liboemcrypto.so.speedtv-bak /odm/lib64/liboemcrypto.so.speedtv-bak "
        "; do [ -e \"$f\" ] && echo \"$f\"; done"
    )
    out = adb.shell(cmd, 20)
    paths = []
    for ln in out.splitlines():
        ln = ln.strip()
        if caminho_oem_ok(ln) and ln not in paths:
            paths.append(ln)
    return paths


def esconder_oem(adb, root, journal, ativos):
    feitos = []
    for origem in ativos:
        if not caminho_oem_ok(origem) or origem.endswith(".nexo-bak") or origem.endswith(".speedtv-bak"):
            continue
        backup = origem + ".speedtv-bak"
        part = particao_de(origem)
        adb.shell("%s -c 'mount -o rw,remount %s'" % (root, part), 15)
        out = adb.shell(
            "%s -c 'mv %s %s && echo NEXO_OK'" % (root, origem, backup),
            20,
        )
        if "NEXO_OK" in out:
            feitos.append({"origem": origem, "backup": backup})
            say("  escondi %s" % origem)
        else:
            say("  não movi %s" % origem)
            say("  " + " ".join(out.split())[:220])
    if not feitos:
        return "não escondi nada. A partição pode estar travada (dm-verity) ou o su recusou."
    journal.setdefault("oemcrypto", [])
    journal["oemcrypto"].extend(feitos)
    salvar_journal(journal)
    return "escondi %d biblioteca(s). Depois do reboot o nível honesto tende a ser L3, e o vídeo protegido toca em SD." % len(feitos)


def restaurar_oem(adb, root, journal):
    itens = list(journal.get("oemcrypto") or [])
    if not itens:
        return "não há biblioteca escondida no journal."
    if not root:
        return "tem backup do Widevine, mas sem root não consigo devolver o arquivo."
    ainda = []
    for item in itens:
        origem = item.get("origem") or ""
        backup = item.get("backup") or ""
        if not caminho_oem_ok(origem) or not caminho_oem_ok(backup):
            continue
        part = particao_de(backup)
        adb.shell("%s -c 'mount -o rw,remount %s'" % (root, part), 15)
        out = adb.shell(
            "%s -c 'if [ -e %s ]; then mv %s %s && echo NEXO_OK; else echo NEXO_SUMIU; fi'"
            % (root, backup, backup, origem),
            20,
        )
        if "NEXO_OK" in out or "NEXO_SUMIU" in out:
            say("  restaurei %s" % origem)
        else:
            ainda.append(item)
            say("  não devolvi %s" % origem)
            say("  " + " ".join(out.split())[:220])
    journal["oemcrypto"] = ainda
    salvar_journal(journal)
    if ainda:
        return "algumas bibliotecas continuam escondidas."
    return "biblioteca OEM de volta. O L1 da TV Box, verdadeiro ou falso, volta depois do reboot."


def widevine(adb, sim=False):
    titulo("Widevine")
    say("Não existe jeito honesto de transformar L3 em L1. Quem promete 4K")
    say("numa TV Box genérica está mentindo o certificado.")
    say("O que dá para fazer: se o L1 é falso, a biblioteca OEM quebra o app")
    say("(tela preta). Esconder liboemcrypto.so faz o Android usar o Widevine")
    say("de software e assumir L3 de verdade. Netflix e similares tocam em SD.")
    say("A cópia fica ao lado do arquivo. Reverter coloca de volta. Precisa de root.")
    conectar_ou_explicar(adb)
    rel = auditar(adb, falar=False)
    say("")
    say(rel.get("widevine") or "sem leitura")
    if rel.get("widevine", "").startswith("Widevine L1"):
        say("Se esta TV Box é Aquaris, MXQ ou outra genérica, trate L1 como vitrine")
        say("até um app protegido tocar de verdade.")
    paths = listar_oemcrypto(adb)
    say("")
    if not paths:
        say("Não achei liboemcrypto.so nos caminhos comuns.")
        say("Ou já é L3 de software, ou a biblioteca está noutro sítio.")
    else:
        say("Bibliotecas:")
        for p in paths:
            say("  " + p)
    root = tem_root(adb)
    say("Root: %s." % ("sim" if root else "não"))
    journal = carregar_journal()
    ativos = [p for p in paths if p.endswith("liboemcrypto.so")]
    backups = [p for p in paths if p.endswith(".nexo-bak") or p.endswith(".speedtv-bak")]
    if backups and not ativos:
        say("A biblioteca OEM já está escondida. Falta reiniciar, se ainda não reiniciou.")
    if ativos and perguntar(
        "Esconder a biblioteca OEM e cair para L3 de verdade?",
        False,
        False if sim else None,
    ):
        if not root:
            say("Sem root não movo arquivo de /vendor. O resto do agente não precisa disso.")
        else:
            say(esconder_oem(adb, root, journal, ativos))
            if journal.get("oemcrypto") and perguntar(
                "Reiniciar para o DRM reler a biblioteca?", True, True if sim else None
            ):
                reiniciar_esperar(adb)
    elif backups and perguntar(
        "Restaurar a biblioteca OEM agora?",
        False,
        False if sim else None,
    ):
        say(restaurar_oem(adb, root, journal))


def nomes_de_risco(rel):
    return [r for r in (rel.get("ruins") or []) if "removido" not in r and validar_pacote(r)]


def seguranca(adb, sim=False):
    titulo("Segurança")
    say("Em novembro de 2026 o Google descreveu o backdoor XCPE em mais de")
    say("um milhão de TV boxes. O pacote é com.oemservice (às vezes x.cpe).")
    say("Ele volta da partição /oem se for apagado. disable-user impede o")
    say("boot de subir o serviço. Isto não é antivírus e não limpa a firmware.")
    say("Se o pacote estiver ativo, tire a TV Box da internet até desativar.")
    conectar_ou_explicar(adb)
    rel = auditar(adb, falar=False)
    ruins = nomes_de_risco(rel)
    if not ruins:
        say("Nenhum nome da lista (Adups, XCPE, OTA silenciosa da placa, miner).")
    else:
        say("Encontrados:")
        for nome in ruins:
            extra = ""
            if nome in ("com.oemservice", "x.cpe"):
                extra = "  ← backdoor de firmware. Não confie no reset sozinho."
            say("  %s%s" % (nome, extra))
    verifier = setting_get(adb, "global", "package_verifier_enable")
    say("Play Protect (package_verifier_enable): %s" % (verifier or "padrão"))
    if not ruins and verifier == "1":
        say("Nada para desativar. O verificador da loja já está ligado.")
        return
    if ruins and perguntar("Desativar estes nomes (reversível, não apaga o APK)?", False, False if sim else None):
        gate = Gate(coletar_dinamicos(adb))
        journal = carregar_journal()
        desativar(adb, gate, journal, ruins, "virus")
        say("Se com.oemservice estava na lista, reinicie e rode o diagnóstico de novo.")
        say("Se ele voltar ligado sozinho, a firmware reinstala. Aí a TV Box não é confiável na sua rede.")
    if verifier != "1" and perguntar("Ligar o verificador de apps da Play Store?", True, True if sim else None):
        journal = carregar_journal()
        ok, msg = setting_put(adb, journal, "global", "package_verifier_enable", "1")
        say("verificador: %s" % (msg if ok else "não apliquei — " + msg))


def diagnostico(adb):
    rel = auditar(adb, falar=True)
    titulo("Leitura extra")
    paths = listar_oemcrypto(adb)
    if paths:
        say("liboemcrypto: " + ", ".join(paths))
    else:
        say("liboemcrypto: não achei nos caminhos comuns.")
    ruins = nomes_de_risco(rel)
    if ruins:
        say("Risco: " + ", ".join(ruins))
        say("Opção Segurança desativa. Não apaga, porque a firmware pode repor.")
    else:
        say("Risco: nenhum nome da lista conhecida.")
    say("Para o detalhe de boot e RAM por app, a opção Ferramentas ainda tem o boot.")
    return rel


def afinar(adb, sim=False):
    titulo("Afinar")
    say("Junta ajustes reversíveis: animações, recomendações, cache e permanência")
    say("ligada na tomada. Não força DNS, Bluetooth, Wi-Fi nem resolução de vídeo.")
    say("Não desativa aplicativo. Reverter desfaz os ajustes.")
    conectar_ou_explicar(adb)
    if not perguntar("Aplicar o conjunto?", True, True if sim else None):
        return
    journal = carregar_journal()
    rel = auditar(adb, falar=False)
    say(limpar_cache_silencioso(adb))
    onda_ajustes(adb, journal, rel.get("ram_real_mb"), video=False)
    root = tem_root(adb)
    if root:
        limpar_zram(adb, sim=sim)
    else:
        say("Sem root: ZRAM fica como está. Cache e kill-all já foram pedidos.")
    say("Feito.")


def limpar_cache_silencioso(adb):
    antes = coletar_metricas(adb, "cache-antes")
    adb.shell("pm trim-caches 999999999K", 40)
    adb.shell("am kill-all", 20)
    depois = coletar_metricas(adb, "cache-depois")
    return linha_metrica(antes) + "\n" + linha_metrica(depois)


def achar_lixo(nomes):
    tem = set(nomes or [])
    return [(pkg, rotulo) for pkg, rotulo in LIXO_FABRICA if pkg in tem]


def linha_android(r):
    et = r.get("release") or "?"
    sdk = r.get("sdk") or "?"
    ker = r.get("kernel") or "?"
    if (r.get("android") or {}).get("mentira"):
        return (
            "A etiqueta diz Android %s (SDK %s). O kernel %s não sustenta essa versão. É firmware remarcado."
            % (et, sdk, ker)
        )
    return "Android %s (SDK %s), kernel %s. Etiqueta e kernel não se contradizem." % (et, sdk, ker)


def linha_ram(r):
    real = r.get("ram_real_mb")
    fonte = r.get("ram_fonte") or "meminfo"
    base = "RAM física estimada: %s, lida em %s. MemFree: %s. Disponível para apps (MemAvailable ou livre + cache): %s." % (
        ("%d MB" % real) if real else "não medida",
        fonte,
        kb_mb(r.get("ram_livre_kb")),
        kb_mb(r.get("ram_usavel_kb") or r.get("ram_disponivel_kb")),
    )
    if r.get("ram_mentira"):
        vitrine = ", ".join("%s MB" % a["mb"] for a in r["ram_mentira"] if a.get("mb"))
        return base + " A vitrine diz %s. Ignore a vitrine." % vitrine
    return base + " Não achei anúncio maior do que a medida."


def linha_wide(r):
    return "Widevine: %s." % (r.get("widevine") or "sem leitura")


def mostrar_leitura(r, lixo):
    titulo("O que esta TV Box é")
    say("%s %s" % (r.get("marca") or "?", r.get("modelo") or "?"))
    say(linha_android(r))
    say(linha_ram(r))
    say("Root: %s." % ("sim. Dá para tirar script de boot." if r.get("root") else "não. Dá para desligar app, mas script de boot fica."))
    say(linha_wide(r))
    say(
        "Aplicativos: %s no total, %s do sistema, %s instalados por alguém."
        % (r.get("pacotes"), r.get("sistema"), r.get("terceiros"))
    )
    pesados = r.get("pesados") or []
    if pesados:
        say("Quem mais usa RAM:")
        for item in pesados[:6]:
            destino = "fica, é necessário" if item.get("protegido") else "pode sair na limpeza"
            say("  %s  %s  (%s)" % (kb_mb(item.get("kb")), item.get("pacote"), destino))
    ruins = nomes_de_risco(r)
    if ruins:
        say("Risco: %s." % ", ".join(ruins))
        say("Desligar impede de subir. Não apaga o arquivo da firmware.")
    else:
        say("Risco: nenhum nome da lista (Adups, XCPE, miner).")
    scripts = r.get("boot_scripts") or []
    if scripts:
        say("Script de boot suspeito (pode recriar vírus toda vez que liga):")
        for item in scripts:
            say("  %s" % item.get("arquivo"))
    else:
        say("Nenhum script de boot com nome de vírus.")
    if lixo:
        say("Veio de fábrica e não é sistema: %s." % ", ".join("%s (%s)" % (rot, pkg) for pkg, rot in lixo))
    else:
        say("Não achei Netflix, Kodi, Prime ou Disney pré-instalados.")
    say("Não mexo em Play Store, serviços do Google, WebView, launcher, teclado, HDMI nem no vídeo do sistema.")
    say("Calendário, telefone, mapa e impressão podem sair. Não são codec.")



def gerar_relatorio_visual(antes, depois, desligados, lixo):
    """Gera um relatório HTML offline e JSON com inventário e métricas por etapa."""
    pasta = garantir_dados()
    metricas = []
    arquivo_metricas = pasta / "metricas.jsonl"
    if arquivo_metricas.is_file():
        try:
            for linha in arquivo_metricas.read_text(encoding="utf-8").splitlines():
                try:
                    item = json.loads(linha)
                    if isinstance(item, dict):
                        metricas.append(item)
                except Exception:
                    continue
        except Exception:
            pass
    # O relatório representa a execução mais recente, não mistura medições antigas.
    inicios = [i for i, item in enumerate(metricas) if item.get("etiqueta") == "antes"]
    if inicios:
        metricas = metricas[inicios[-1]:]

    dados = {
        "gerado_em": agora_iso(),
        "dispositivo": {
            "marca": antes.get("marca"), "modelo": antes.get("modelo"),
            "plataforma": antes.get("plataforma"), "abi": antes.get("abi"),
            "android": antes.get("release"), "sdk": antes.get("sdk"),
            "kernel": antes.get("kernel"),
        },
        "antes": antes,
        "depois": depois,
        "desativados_nesta_sessao": desligados or [],
        "apps_de_fabrica_detectados": [
            {"pacote": pkg, "nome": nome} for pkg, nome in (lixo or [])
        ],
        "metricas_por_etapa": metricas,
    }
    json_path = pasta / "relatorio.json"
    json_path.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")

    def esc(valor):
        return html.escape(str(valor if valor is not None else "—"))

    def card(rotulo, valor, detalhe=""):
        return '<article class="card"><small>%s</small><strong>%s</strong><span>%s</span></article>' % (
            esc(rotulo), esc(valor), esc(detalhe)
        )

    def grafico(titulo_grafico, chave, unidade=""):
        valores = []
        for item in metricas:
            valor = item.get(chave)
            if isinstance(valor, (int, float)):
                valores.append((item.get("etiqueta") or "etapa", valor))
        if not valores:
            return '<section class="panel"><h2>%s</h2><p>Sem amostras suficientes.</p></section>' % esc(titulo_grafico)
        maximo = max([v for _, v in valores] + [1])
        barras = []
        for nome, valor in valores:
            largura = max(2, min(100, int((valor / maximo) * 100)))
            barras.append(
                '<div class="barrow"><label>%s</label><div class="track"><i style="width:%d%%"></i></div><b>%s%s</b></div>'
                % (esc(nome), largura, esc(round(valor, 1)), esc(unidade))
            )
        return '<section class="panel"><h2>%s</h2>%s</section>' % (esc(titulo_grafico), "".join(barras))

    linhas = []
    for item in metricas:
        linhas.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            esc(item.get("etiqueta")),
            esc(kb_mb(item.get("mem_available_kb"))),
            esc(item.get("processos")),
            esc(item.get("desativados")),
            esc(kb_mb(item.get("data_livre_kb"))),
        ))
    if not linhas:
        linhas.append("<tr><td colspan='5'>Sem métricas coletadas.</td></tr>")
    pacotes = "".join("<li>%s</li>" % esc(pkg) for pkg in (desligados or []))
    if not pacotes:
        pacotes = "<li>Nenhum pacote desativado nesta sessão.</li>"

    dispositivo = "%s %s · %s · Android %s (SDK %s) · kernel %s" % (
        antes.get("marca") or "Marca não identificada",
        antes.get("modelo") or "",
        antes.get("plataforma") or "SoC não identificado",
        antes.get("release") or "?",
        antes.get("sdk") or "?",
        antes.get("kernel") or "?",
    )
    ram_antes = kb_mb(antes.get("ram_usavel_kb") or antes.get("ram_disponivel_kb"))
    ram_depois = kb_mb((depois or {}).get("ram_usavel_kb") or (depois or {}).get("ram_disponivel_kb"))
    html_doc = """<!doctype html>
<html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SpeedTV Box — Relatório</title>
<style>
:root{color-scheme:dark;--bg:#07101f;--panel:#101d31;--line:#263852;--text:#eef5ff;--muted:#a8b8cf;--accent:#65d8f2}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 10% 0,#152b48,var(--bg) 45%);color:var(--text);font:15px system-ui,sans-serif;padding:24px}
main{max-width:1100px;margin:auto}header{padding:28px 0;border-bottom:1px solid var(--line)}h1{font-size:clamp(2rem,5vw,3.5rem);margin:5px 0}h2{font-size:1.15rem;margin:0 0 18px}p,small,span{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:20px 0}
.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px}.card small,.card strong,.card span{display:block}.card strong{font-size:1.65rem;margin:8px 0;color:var(--text)}.columns{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin:14px 0}.barrow{display:grid;grid-template-columns:120px 1fr 70px;gap:10px;align-items:center;margin:12px 0;font-size:.85rem}.track{height:10px;background:#24354d;border-radius:99px;overflow:hidden}.track i{display:block;height:100%;background:linear-gradient(90deg,#3d9edb,var(--accent));border-radius:99px}.barrow b{text-align:right}.panel{margin:14px 0;overflow:auto}table{width:100%;border-collapse:collapse;font-size:.88rem}td,th{text-align:left;padding:10px;border-bottom:1px solid var(--line)}th{color:var(--accent)}ul{columns:2;overflow-wrap:anywhere}footer{padding:24px 0;color:var(--muted);font-size:.8rem}@media(max-width:600px){body{padding:14px}.barrow{grid-template-columns:90px 1fr 55px}ul{columns:1}}
</style><main>
<header><small>SPEEDTV BOX · AUDITORIA E DEBLOAT</small><h1>Relatório da TV Box</h1><p>Gerado em __DATE__</p><p>__DEVICE__</p></header>
<div class="grid">__CARDS__</div>
<div class="columns">__RAM_CHART____PROCESS_CHART__</div>
<section class="panel"><h2>Métricas por etapa</h2><table><thead><tr><th>Etapa</th><th>RAM disponível</th><th>Processos</th><th>Desativados</th><th>Armazenamento livre</th></tr></thead><tbody>__ROWS__</tbody></table></section>
<section class="panel"><h2>Pacotes desativados nesta sessão</h2><ul>__PACKAGES__</ul></section>
<section class="panel"><h2>Como interpretar</h2><p>MemAvailable (ou livre + cache nos kernels antigos) é a referência de RAM disponível; MemFree isolado não representa a memória utilizável. Variações dependem do tempo desde o boot, cache e aplicativos abertos.</p><p>A contagem de processos é aproximada e não mede desempenho por si só.</p><p>Esta auditoria procura indicadores conhecidos e não certifica que o firmware está livre de malware.</p><p>Widevine informado pelo sistema não comprova certificação de streaming; só a reprodução protegida confirma o comportamento real.</p></section>
<footer>SpeedTV Box · relatório local, sem bibliotecas ou serviços externos.</footer></main></html>"""
    html_doc = (html_doc
        .replace("__DATE__", esc(agora_iso()))
        .replace("__DEVICE__", esc(dispositivo))
        .replace("__CARDS__", (
            card("RAM física estimada", (str(antes.get("ram_real_mb")) + " MB") if antes.get("ram_real_mb") else "Não medida", antes.get("ram_fonte"))
            + card("Pacotes instalados", antes.get("pacotes"), "antes")
            + card("Pacotes instalados", (depois or {}).get("pacotes"), "depois" if depois else "sem leitura final")
            + card("Desativados nesta sessão", len(desligados or []), "ações registradas")
            + card("RAM disponível", ram_antes, "antes")
            + card("RAM disponível", ram_depois, "depois")
        ))
        .replace("__RAM_CHART__", grafico("RAM disponível ao longo das ondas", "mem_available_kb", " kB"))
        .replace("__PROCESS_CHART__", grafico("Processos por etapa", "processos"))
        .replace("__ROWS__", "".join(linhas))
        .replace("__PACKAGES__", pacotes)
    )
    html_path = pasta / "relatorio.html"
    html_path.write_text(html_doc, encoding="utf-8")
    return {
        "html": publicar_relatorio(html_path) or html_path,
        "json": publicar_relatorio(json_path) or json_path,
    }


def montar_relatorio_final(antes, depois, desligados, lixo):
    fim = depois or antes
    linhas = [
        "SPEEDTV BOX — RELATÓRIO",
        "TV Box: %s %s" % (antes.get("marca") or "?", antes.get("modelo") or "?"),
        "Quando: %s" % (fim.get("quando") or ""),
        "ADB: %s" % (antes.get("serial") or ""),
        "",
        "ANDROID",
        "  Antes: " + linha_android(antes),
    ]
    if depois:
        linhas.append("  Depois: " + linha_android(depois))
    linhas += ["", "MEMÓRIA", "  Antes: " + linha_ram(antes)]
    if depois:
        linhas.append("  Depois: " + linha_ram(depois))
    linhas += [
        "",
        "WIDEVINE",
        "  " + linha_wide(antes),
        "  L1 de TV Box genérica só vale se um filme protegido tocar em HD.",
        "  Sem root o nível não muda. Com root, a opção Widevine esconde a biblioteca falsa",
        "  e o Android assume L3 de verdade, em SD.",
        "",
        "APLICATIVOS",
        "  Antes: %s pacotes, %s de sistema, %s de terceiros."
        % (antes.get("pacotes"), antes.get("sistema"), antes.get("terceiros")),
    ]
    if depois:
        linhas.append(
            "  Depois: %s pacotes, %s desativados no sistema."
            % (depois.get("pacotes"), len(depois.get("desativados") or []))
        )
    if desligados:
        linhas.append("  O SpeedTV Box desativou %d nesta sessão:" % len(desligados))
        linhas.extend("    " + pkg for pkg in desligados)
    else:
        linhas.append("  Nenhum pacote foi desativado nesta sessão.")
    if lixo:
        linhas.append("  Lixo de fábrica visto na leitura:")
        linhas.extend("    %s — %s" % (rot, pkg) for pkg, rot in lixo)
    ruins = nomes_de_risco(antes)
    linhas += [
        "",
        "O QUE NÃO FOI MEXIDO",
        "  Play Store, Play Services, WebView, launcher, teclado, HDMI e pacotes de vídeo do sistema.",
        "  Calendário e app de telefone entram na limpeza. Codec, não.",
        "",
        "RISCO",
    ]
    if ruins:
        linhas.append("  Encontrado: " + ", ".join(ruins))
        linhas.append("  Se o nome voltar ligado sozinho depois de reiniciar, a firmware recolocou.")
        linhas.append("  Aí a TV Box não é confiável na sua rede.")
    else:
        linhas.append("  Nenhum nome da lista conhecida.")
    linhas += [
        "",
        "COMO LER",
        "  A RAM que vale é a do kernel, não a da etiqueta.",
        "  O Android que vale é o que o kernel aguenta, não o número da tela Sobre.",
        "  Desativado para o usuário volta no reset de fábrica. Nada foi apagado de /system.",
    ]
    return "\n".join(linhas)


def primeira_vez(adb, sim=False, sem_onda3=False):
    titulo("Começar")
    say("Quatro passos. Você só responde sim ou não.")
    say("1. Ler a TV Box, sem desligar nada.")
    say("2. Se houver vírus, backdoor ou script de boot, tirar.")
    say("3. Limpar em ondas. Se a imagem não voltar, a onda é desfeita.")
    say("4. Salvar o relatório em Download/SpeedTV.")
    say("")
    say("Não é necessário resetar a TV Box. Faça backup do que importa e deixe a depuração ligada.")
    if not perguntar("Começar?", True, True if sim else None):
        say("Nada foi feito.")
        return
    conectar_ou_explicar(adb)
    antes = auditar(adb, falar=False)
    lixo = achar_lixo(adb.installed_map())
    mostrar_leitura(antes, lixo)
    (garantir_dados() / "antes.json").write_text(
        json.dumps(antes, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    journal = carregar_journal()
    ja = set(journal.get("disabled") or [])

    ruins = nomes_de_risco(antes)
    if ruins:
        say("")
        if perguntar("Desativar o risco agora (%s)?" % ", ".join(ruins), True, True if sim else None):
            desativar(adb, Gate(coletar_dinamicos(adb)), journal, ruins, "virus")
        else:
            say("Deixei o risco ligado. Se for o XCPE, tire a TV Box da internet.")
    else:
        say("Passo 2: sem nome de vírus na lista.")

    scripts = [s for s in (antes.get("boot_scripts") or []) if not s.get("protegido")]
    if scripts:
        say("")
        say("Estes scripts sobem junto com a TV Box. É assim que o vírus volta depois do reset.")
        if perguntar("Tirar do boot? Fica uma cópia para desfazer.", True, True if sim else None):
            afastar_scripts(adb, journal, scripts)
        else:
            say("Deixei os scripts. Se for vírus, ele volta na próxima vez que ligar.")

    if lixo:
        say("")
        say("Isto não é codec nem a loja. Desativar não apaga. O reset liga de novo.")
        rotulos = ", ".join(sorted({rot for _, rot in lixo}))
        if perguntar("Desativar o que veio de fábrica (%s)?" % rotulos, True, True if sim else None):
            desativar(adb, Gate(coletar_dinamicos(adb)), journal, [pkg for pkg, _ in lixo], "fabrica")

    say("")
    say("Passo 3 é a limpeza em ondas. Ela pergunta de novo antes de reiniciar.")
    executar_ondas(adb, sim=sim, sem_onda3=sem_onda3)

    say("")
    say("Passo 4: lendo de novo para o relatório.")
    depois = None
    try:
        if adb.state() == "device" or adb.connect():
            if adb.state() == "device":
                depois = auditar(adb, falar=False)
    except (DeviceOffline, SystemExit, Exception):
        depois = None
    journal = carregar_journal()
    desligados = [pkg for pkg in (journal.get("disabled") or []) if pkg not in ja]
    texto = montar_relatorio_final(antes, depois, desligados, lixo)
    log = anexar_log("relatorio", texto, texto)
    visual = gerar_relatorio_visual(antes, depois, desligados, lixo)
    titulo("Relatório")
    say(texto)
    dizer_onde(log)
    if visual:
        say("Relatório visual offline: %s" % visual.get("html"))
        say("Dados estruturados: %s" % visual.get("json"))




# Instalações oficiais. O agente baixa apenas APKs de hosts/repositórios definidos.
def origem_https_permitida(url, hosts):
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in hosts


def _ler_json_https(url, hosts):
    parsed = urlparse(url)
    if not origem_https_permitida(url, hosts):
        raise ValueError("Origem de atualização não autorizada: %s" % (parsed.hostname or "?"))
    req = urllib.request.Request(url, headers={"User-Agent": "SpeedTVBox/9"})
    with urllib.request.urlopen(req, timeout=35) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname not in hosts:
            raise ValueError("O servidor redirecionou para uma origem não autorizada.")
        bruto = response.read(2 * 1024 * 1024 + 1)
    if len(bruto) > 2 * 1024 * 1024:
        raise ValueError("Resposta de atualização grande demais.")
    return json.loads(bruto.decode("utf-8"))


def _asset_apk(api_url, hosts):
    dados = _ler_json_https(api_url, hosts)
    assets = dados.get("assets") or []
    for asset in assets:
        nome = str(asset.get("name") or "")
        url = asset.get("browser_download_url") or asset.get("url")
        if nome.lower().endswith(".apk") and url:
            return nome, url
    raise RuntimeError("O lançamento oficial não publicou um APK reconhecível.")


def _baixar_apk(url, destino, hosts):
    parsed = urlparse(url)
    if not origem_https_permitida(url, hosts):
        raise ValueError("Download bloqueado: origem não autorizada.")
    req = urllib.request.Request(url, headers={"User-Agent": "SpeedTVBox/9"})
    with urllib.request.urlopen(req, timeout=90) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname not in hosts:
            raise ValueError("O APK foi redirecionado para um host não autorizado.")
        limite = 60 * 1024 * 1024
        partes = []
        total = 0
        while True:
            bloco = response.read(1024 * 1024)
            if not bloco:
                break
            total += len(bloco)
            if total > limite:
                raise ValueError("APK maior que o limite de 60 MB.")
            partes.append(bloco)
    bruto = b"".join(partes)
    if len(bruto) < 40 * 1024 or not bruto.startswith(b"PK\x03\x04"):
        raise ValueError("O arquivo recebido não parece ser um APK válido.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(bruto)
    return len(bruto)


def _instalar_apk_oficial(adb, nome, api_url, hosts, pacote, arquivo):
    conectar_ou_explicar(adb)
    titulo("Instalando " + nome)
    say("Buscando o lançamento oficial. O agente não usa sites de APK de terceiros.")
    try:
        nome_asset, url = _asset_apk(api_url, hosts)
        destino = garantir_dados() / "apks" / arquivo
        tamanho = _baixar_apk(url, destino, hosts)
    except Exception as exc:
        say("Não consegui obter o APK oficial: %s" % exc)
        return False
    say("Download concluído: %s (%s MB)." % (nome_asset, "%.2f" % (tamanho / 1048576.0)))
    say("Instalando no usuário Android %s…" % adb.user)
    codigo, saida = adb._exec(["-s", adb.serial, "install", "-r", str(destino)], 180)
    if codigo != 0 or "success" not in saida.lower():
        say("A instalação não foi confirmada pelo Android:")
        say(saida[:700] or "sem resposta")
        say("O APK ficou guardado em: %s" % destino)
        return False
    if not adb.existe(pacote):
        say("O instalador terminou, mas o pacote esperado não apareceu. Não alterei a tela inicial.")
        return False
    say("%s instalado e confirmado (%s)." % (nome, pacote))
    say("APK guardado em: %s" % destino)
    return True


def _definir_launcher(adb, pacote):
    consulta = adb.shell(
        "cmd package resolve-activity --brief -a android.intent.action.MAIN "
        "-c android.intent.category.HOME -p " + pacote, 20
    )
    componente = ""
    for linha in reversed(consulta.splitlines()):
        m = re.search(r"([A-Za-z0-9_.]+/[A-Za-z0-9_.$]+)", linha.strip())
        if m and m.group(1).split("/", 1)[0] == pacote:
            componente = m.group(1)
            break
    if not componente:
        return False, "O Android não anunciou uma atividade HOME para este launcher."
    tentativas = [
        "cmd package set-home-activity --user %s %s" % (adb.user, componente),
        "pm set-home-activity --user %s %s" % (adb.user, componente),
    ]
    for comando in tentativas:
        try:
            adb.shell(comando, 20)
        except Exception:
            pass
        if home_package(adb) == pacote:
            return True, componente
    return home_package(adb) == pacote, componente


def _desativar_launcher_antigo(adb, antigo, novo):
    if not antigo or antigo == novo:
        say("Não há launcher antigo diferente para desativar.")
        return
    if not perguntar(
        "A nova tela inicial foi confirmada. Desativar o launcher antigo (%s)? "
        "Ele ficará guardado e poderá ser restaurado." % antigo,
        True,
    ):
        say("Mantive o launcher antigo habilitado como alternativa.")
        return
    journal = carregar_journal()
    code = adb.enabled_code(antigo)
    if code not in (0, 1):
        say("Não consegui confirmar o estado anterior de %s. Não vou mexer nele." % antigo)
        return
    journal.setdefault("package_states", {}).setdefault(antigo, {
        "enabled": code, "removido_para_usuario": False, "quando": agora_iso(),
    })
    saida = adb.shell("pm disable-user --user %s %s" % (adb.user, antigo), 20)
    if "new state: disabled" not in saida.lower():
        say("O Android não confirmou a desativação: %s" % saida[:250])
        return
    if antigo not in journal.setdefault("disabled", []):
        journal["disabled"].append(antigo)
    journal.setdefault("launcher", {})["antigo_desativado"] = antigo
    journal["launcher"]["novo"] = novo
    salvar_journal(journal)
    escrever_rollback(adb.serial, adb.binary, journal["disabled"], journal.get("package_states"))
    if home_package(adb) != novo:
        say("A verificação falhou. Reativando o launcher antigo automaticamente.")
        reativar(adb, [antigo], journal.get("package_states"))
        journal["disabled"] = [p for p in journal["disabled"] if p != antigo]
        journal.get("package_states", {}).pop(antigo, None)
        journal["launcher"].pop("antigo_desativado", None)
        salvar_journal(journal)
        return
    say("Launcher antigo desativado. A nova tela inicial continua sendo a HOME.")
    say("Para desfazer: menu principal → Recuperar alterações.")


def instalar_launcher(adb, escolha):
    catalogo = {
        "glass": {
            "nome": "Glass Launcher",
            "api": "https://git.namillis.me/api/v1/repos/namillis/GlassLauncherTV/releases/latest",
            "hosts": {"git.namillis.me"},
            "pacote": "tv.glass.launcher",
            "arquivo": "GlassLauncher.apk",
        },
        "projectivy": {
            "nome": "Projectivy Launcher",
            "api": "https://api.github.com/repos/spocky/miproja1/releases/latest",
            "hosts": {"api.github.com", "github.com", "release-assets.githubusercontent.com"},
            "pacote": "com.spocky.projengmenu",
            "arquivo": "ProjectivyLauncher.apk",
        },
    }
    item = catalogo.get(escolha)
    if not item:
        say("Escolha de launcher desconhecida.")
        return
    antigo = home_package(adb)
    if antigo == item["pacote"]:
        say("%s já é a tela inicial padrão." % item["nome"])
        return
    if not _instalar_apk_oficial(
        adb, item["nome"], item["api"], item["hosts"], item["pacote"], item["arquivo"]
    ):
        return
    try:
        adb.shell("monkey -p %s 1" % item["pacote"], 20)
    except Exception:
        pass
    ok, detalhe = _definir_launcher(adb, item["pacote"])
    if not ok:
        say("O aplicativo foi instalado, mas o Android não confirmou a troca automática.")
        say("Na TV Box, abra o novo launcher e escolha 'Sempre' quando o Android perguntar.")
        say("Também pode selecionar em Configurações → Apps → Apps padrão → App de início.")
        say("Não desativei nem removi o launcher antigo.")
        return
    say("Android agora aponta HOME para %s." % item["nome"])
    say("Teste o botão HOME do controle remoto.")
    if perguntar("A nova tela inicial apareceu corretamente ao apertar HOME?", True):
        _desativar_launcher_antigo(adb, antigo, item["pacote"])
    else:
        say("Mantive o launcher antigo. A troca não foi considerada concluída.")
        say("Você pode abrir o novo launcher manualmente e escolher 'Sempre' na tela do Android.")


def abrir_ou_instalar_downloader(adb):
    conectar_ou_explicar(adb)
    pacote = "com.esaba.downloader"
    if adb.existe(pacote) and adb.enabled_code(pacote) in (0, 1, None):
        say("Downloader já está instalado. Abrindo…")
        say(adb.shell("monkey -p %s 1" % pacote, 20))
        return
    say("O Downloader é distribuído pelo Google Play. Vou abrir a página oficial da loja.")
    say("Na TV, selecione Instalar. O agente não baixa cópias de APK de sites terceiros.")
    saida = adb.shell(
        "am start -a android.intent.action.VIEW "
        "-d 'market://details?id=com.esaba.downloader'", 25
    )
    if "error" in saida.lower() or "unable" in saida.lower() or "not found" in saida.lower():
        saida = adb.shell(
            "am start -a android.intent.action.VIEW "
            "-d 'https://play.google.com/store/apps/details?id=com.esaba.downloader'", 25
        )
    say(saida or "Página da loja solicitada na TV Box.")
    say("Depois da instalação, volte aqui e escolha Downloader novamente para abrir.")


def menu_instalacoes(adb):
    while True:
        titulo("Instalar aplicativos")
        say("Escolha o que quer colocar na TV Box:")
        say("  1  Downloader — navegador e instalador de APKs")
        say("  2  Glass Launcher — tela inicial leve")
        say("  3  Projectivy Launcher — tela inicial personalizável")
        say("  0  Voltar")
        try:
            escolha = input("\nO que vamos instalar? ").strip()
        except EOFError:
            return
        if escolha == "1":
            abrir_ou_instalar_downloader(adb)
        elif escolha == "2":
            instalar_launcher(adb, "glass")
        elif escolha == "3":
            instalar_launcher(adb, "projectivy")
        elif escolha in ("0", ""):
            return
        else:
            say("Não reconheci essa opção. Escolha 1, 2, 3 ou 0.")


def liberar_ram(adb):
    titulo("Liberar RAM")
    conectar_ou_explicar(adb)
    instalados = set(adb.installed_map())
    sistema = adb.system_names()
    gate = Gate(coletar_dinamicos(adb))
    bruto = adb.shell("dumpsys meminfo", 35)
    pesados = processos_pesados(bruto, instalados, gate)
    candidatos = [
        p for p in pesados
        if validar_pacote(p.get("pacote"))
        and p["pacote"] not in sistema
        and not p.get("protegido")
        and (p.get("kb") or 0) >= 25000
    ]
    if not candidatos:
        say("Não encontrei aplicativos de usuário em segundo plano com consumo relevante.")
        say("O Android já administra a RAM livre; não vou encerrar serviços do sistema à força.")
        return
    say("Estes aplicativos instalados pelo usuário estão entre os que mais consomem RAM:")
    escolhidos = []
    for p in candidatos[:12]:
        say("  %s — %s" % (p.get("pacote"), kb_mb(p.get("kb"))))
        if perguntar("Fechar este aplicativo agora? Ele poderá abrir normalmente depois.", False):
            escolhidos.append(p["pacote"])
    if not escolhidos:
        say("Nenhum aplicativo foi fechado.")
        return
    for pkg in escolhidos:
        out = adb.shell("am force-stop --user %s %s" % (adb.user, pkg), 20)
        say("  fechado %s — %s" % (pkg, out or "comando enviado"))
    depois = coletar_metricas(adb, "depois-fechar-apps")
    say("Medição depois: " + linha_metrica(depois))
    say("Isso libera memória temporariamente; o Android pode reabrir apps quando necessário.")


def limpar_armazenamento(adb):
    titulo("Liberar armazenamento")
    conectar_ou_explicar(adb)
    antes = parse_df_data(adb.shell("df -k /data 2>/dev/null || df /data", 20))
    say("Antes: %s livres em /data." % kb_mb(antes.get("livre_kb")))
    say("Vou pedir ao Android para remover somente caches que ele considera descartáveis.")
    say("Fotos, vídeos, contas, configurações e dados dos aplicativos não serão apagados.")
    if not perguntar("Executar a limpeza segura de cache?", True):
        say("Cancelado.")
        return
    saida = adb.shell("pm trim-caches 999999999K", 90)
    say(saida or "Solicitação de limpeza enviada ao Package Manager.")
    depois = parse_df_data(adb.shell("df -k /data 2>/dev/null || df /data", 20))
    a, b = antes.get("livre_kb"), depois.get("livre_kb")
    if a is not None and b is not None:
        delta = b - a
        say("Depois: %s livres. Variação: %s." % (
            kb_mb(b), ("+" if delta >= 0 else "") + kb_mb(delta)
        ))
    else:
        say("Depois: %s livres." % kb_mb(b))
    say("Não apague manualmente pastas /data/app, /data/data ou /system.")


def menu(adb, sim=False, sem_onda3=False):
    while True:
        titulo("SpeedTV Box %s — Assistente" % VERSAO)
        say("TV Box configurada: %s" % adb.serial)
        say("")
        say("O que você quer fazer?")
        say("  1  Começar — auditoria completa e otimização guiada")
        say("  2  Diagnosticar — só examinar, sem alterar nada")
        say("  3  Liberar espaço e memória")
        say("  4  Instalar aplicativos ou trocar a tela inicial")
        say("  5  Corrigir a Play Store")
        say("  6  Investigar vírus e segurança")
        say("  7  Recuperar alterações / desfazer")
        say("  8  Mais ferramentas e relatórios")
        say("  0  Sair")
        try:
            escolha = input("\nDigite o número da tarefa: ").strip()
        except EOFError:
            return
        try:
            if escolha == "1":
                primeira_vez(adb, sim=sim, sem_onda3=sem_onda3)
            elif escolha == "2":
                conectar_ou_explicar(adb)
                diagnostico(adb)
            elif escolha == "3":
                titulo("Memória e armazenamento")
                say("  1  Fechar apps de usuário que estão pesando na RAM")
                say("  2  Limpar caches descartáveis para liberar armazenamento")
                say("  3  Ver RAM e armazenamento sem alterar nada")
                say("  0  Voltar")
                sub = input("\nEscolha: ").strip()
                if sub == "1":
                    liberar_ram(adb)
                elif sub == "2":
                    limpar_armazenamento(adb)
                elif sub == "3":
                    status_ram(adb)
            elif escolha == "4":
                menu_instalacoes(adb)
            elif escolha == "5":
                playstore(adb, sim=sim)
            elif escolha == "6":
                seguranca(adb, sim=sim)
            elif escolha == "7":
                reverter(adb, sim=sim)
            elif escolha == "8":
                submenu(adb, sim)
            elif escolha == "0":
                return
            else:
                say("Não reconheci essa opção. Tente novamente.")
        except DeviceOffline as exc:
            say("A TV Box saiu do ADB: %s" % exc)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            say("\nInterrompido. Nenhuma etapa nova será iniciada.")
            return
        except Exception as exc:
            say("Ocorreu um erro nesta tarefa: %s" % exc)
        try:
            input("\nPressione Enter para voltar ao menu principal…")
        except EOFError:
            return


def submenu(adb, sim=False):
    while True:
        titulo("Ferramentas")
        say("  1  Comparar antes e depois")
        say("  2  Analisar inicialização (boot)")
        say("  3  Ver RAM e aplicativos pesados")
        say("  4  Limpar cache para liberar armazenamento")
        say("  5  Perguntar ao Gemini sobre esta TV Box")
        say("  6  Reiniciar a TV Box")
        say("  0  Voltar")
        try:
            escolha = input("\nQual ferramenta? ").strip()
        except EOFError:
            return
        if escolha == "1":
            comparar()
        elif escolha == "2":
            analisar_boot(adb)
        elif escolha == "3":
            status_ram(adb)
        elif escolha == "4":
            limpar_armazenamento(adb)
        elif escolha == "5":
            try:
                q = input("O que você quer entender ou corrigir? ").strip()
            except EOFError:
                return
            if q:
                conectar_ou_explicar(adb)
                perguntar_gemini(adb, q)
        elif escolha == "6":
            conectar_ou_explicar(adb)
            if perguntar("Reiniciar agora?", False):
                ok = reiniciar_esperar(adb)
                say("A TV Box voltou." if ok else "Ainda não voltou. Espere e tente o diagnóstico.")
        elif escolha in ("0", ""):
            return
        else:
            say("Não reconheci essa opção.")

def selftest():
    assert VERSAO == "9"
    assert origem_https_permitida("https://api.github.com/repos/a/b", {"api.github.com"})
    assert not origem_https_permitida("http://api.github.com/repos/a/b", {"api.github.com"})
    assert not origem_https_permitida("https://api.github.com.evil.invalid/a", {"api.github.com"})
    assert validar_pacote("com.android.vending")
    assert not validar_pacote("com.foo;rm")
    assert not validar_pacote("rm -rf")
    g = Gate({"com.custom.launcher"})
    assert g.motivo("com.google.android.gms")
    assert g.motivo("com.google.android.gms.location.history")
    assert g.motivo("com.android.systemui")
    assert g.motivo("com.foo.tvinput.service")
    assert g.motivo("com.vendor.hdmi.service")
    assert g.motivo("com.google.android.webview")
    assert g.motivo("com.custom.launcher") == "está em uso agora (home, teclado, acessibilidade ou entrada de vídeo)"
    assert g.motivo("com.google.android.feedback") is None
    assert g.motivo("com.oemservice") is None
    assert "com.oemservice" in BAD_EXACT
    assert "com.abc.nexus" in BAD_EXACT
    assert "com.android.system.ntp" in BAD_EXACT
    assert candidatos_onda2({"com.vendor.otaupdate", "com.abc.nexus"}) == ["com.abc.nexus"]
    assert caminho_oem_ok("/vendor/lib/liboemcrypto.so")
    assert caminho_oem_ok("/vendor/lib64/liboemcrypto.so.nexo-bak")
    assert caminho_oem_ok("/vendor/lib64/liboemcrypto.so.speedtv-bak")
    assert not caminho_oem_ok("/vendor/lib/liboemcrypto.so;rm")
    assert particao_de("/odm/lib/liboemcrypto.so") == "/odm"
    assert g.motivo("com.google.android.tvrecommendations") is None
    mem = parse_meminfo("MemTotal:        1030340 kB\nMemAvailable:     340000 kB\nSwapTotal:        511996 kB\n")
    assert mem["MemTotal"] == 1030340
    assert parse_iomem_mb("80000000-bfffffff : System RAM\n") == 1024
    ver = avaliar_android(34, "14", (4, 4))
    assert ver["mentira"] is True
    ver2 = avaliar_android(28, "9", (4, 9))
    assert ver2["mentira"] is False
    assert parse_kernel("Linux version 4.9.113 (builder@box)") == (4, 9)
    wide = parse_widevine("plugin widevine\nsecurityLevel: L3\n")
    assert "L3" in wide
    texto = montar_relatorio_final(
        {
            "marca": "Box", "modelo": "Link", "release": "14", "sdk": 34, "kernel": "4.9",
            "android": {"mentira": True}, "ram_real_mb": 1024, "ram_disponivel_kb": 700000,
            "ram_mentira": [{"mb": 4096}], "widevine": "Widevine L3",
            "pacotes": 200, "sistema": 180, "terceiros": 20, "quando": "t", "serial": "s",
            "ruins": ["com.oemservice"],
        },
        {
            "android": {"mentira": True}, "release": "14", "sdk": 34, "kernel": "4.9",
            "ram_real_mb": 1024, "ram_disponivel_kb": 800000, "pacotes": 200,
            "desativados": ["com.android.calendar"], "quando": "t2",
        },
        ["com.android.calendar"],
        [("org.xbmc.kodi", "Kodi")],
    )
    assert "1024 MB" in texto
    assert "Kodi" in texto
    assert "com.oemservice" in texto
    assert "com.android.calendar" in texto
    assert achar_lixo(["org.xbmc.kodi", "com.android.vending"]) == [("org.xbmc.kodi", "Kodi")]
    assert escolher_ram(4096, 1024, 4096, None, 4096) == (1024, "zoneinfo", True)
    assert escolher_ram(1024, None, None, None, None) == (1024, "meminfo", False)
    amostra = "com.android.tv.settings/com.android.tv.settings.MainSettings\n"
    assert re.findall(r"([A-Za-z][\w.]*)/", amostra) == ["com.android.tv.settings"]
    pesados = processos_pesados(
        "    80,000K: com.android.calendar (pid 1)\n    90,000K: system_server (pid 2)\n",
        {"com.android.calendar"},
        Gate(),
    )
    assert pesados and pesados[0]["pacote"] == "com.android.calendar"
    assert ram_usavel_kb({"MemFree": 40000, "Cached": 700000, "Buffers": 10000}) == 750000
    assert candidatos_profundos(
        ["com.rockchips.mediacenter", "com.droidlogic.mboxlauncher", "com.android.vending"], Gate(),
    ) == []
    data = extrair_json("```json\n{\"diagnostico\": \"webview\", \"acoes\": []}\n```")
    assert data["diagnostico"] == "webview"
    nomes = parse_pm_names("package:com.android.vending\npackage:/system/app/X.apk=com.foo.bar\n")
    assert "com.android.vending" in nomes
    paths = parse_pm_paths("package:/system/priv-app/Gms/Gms.apk=com.google.android.gms\n")
    assert paths["com.google.android.gms"].endswith("Gms.apk")
    portas, estranhas = varredura_portas(
        "0: 0B00007F:15B3 00000000:0000 0A\n"
        "1: 0B00007F:C350 0100007F:01BB 01\n"
    )
    assert 5555 in portas
    assert 50000 not in portas
    assert not estranhas
    assert not init_e_suspeito("bootanim.rc")
    assert init_e_suspeito("adups_fota.rc")
    rss = parse_rss("    80,000K: com.spotify.tv.android (pid 1 / activities)\n")
    assert rss[0]["nome"] == "com.spotify.tv.android" and rss[0]["aberto"] is True
    assert numero_mb("4GB") == 4096
    assert numero_mb("2048") == 2048
    df = parse_df_data("Filesystem 1K-blocks Used Available Use% Mounted on\n/dev/data 900000 100000 700000 20% /data\n")
    assert df["livre_kb"] == 700000
    assert classificar_log("FATAL EXCEPTION MissingWebViewPackageException")[0] == "webview"
    assert validar_valor("dns.google")
    assert not validar_valor("a;rm")
    global _DADOS
    dados_anteriores = _DADOS
    try:
        with tempfile.TemporaryDirectory(prefix="speedtv-selftest-") as tmp:
            _DADOS = Path(tmp)
            (Path(tmp) / "metricas.jsonl").write_text(
                json.dumps({"etiqueta": "antes", "mem_available_kb": 500000, "processos": 42, "desativados": 0, "data_livre_kb": 900000}) + "\n"
                + json.dumps({"etiqueta": "fim", "mem_available_kb": 650000, "processos": 30, "desativados": 3, "data_livre_kb": 910000}) + "\n",
                encoding="utf-8",
            )
            visual = gerar_relatorio_visual(
                {"marca": "<Marca>", "modelo": "Teste", "plataforma": "amlogic", "abi": "arm64", "release": "11", "sdk": 30, "kernel": "4.9", "ram_real_mb": 2048, "ram_fonte": "zoneinfo", "ram_usavel_kb": 500000, "pacotes": 120, "pacotes_instalados": ["com.android.vending"]},
                {"pacotes": 117, "ram_usavel_kb": 650000},
                ["com.example.disabled"],
                [],
            )
            html_report = Path(visual["html"]).read_text(encoding="utf-8")
            json_report = json.loads(Path(visual["json"]).read_text(encoding="utf-8"))
            assert "<!doctype html>" in html_report.lower()
            assert "&lt;Marca&gt;" in html_report
            assert "RAM disponível ao longo das ondas" in html_report
            assert json_report["desativados_nesta_sessao"] == ["com.example.disabled"]
    finally:
        _DADOS = dados_anteriores
    say("selftest ok")


def main(argv=None):
    setup_stdio()
    parser = argparse.ArgumentParser(
        prog="speedtvbox.py",
        description="SpeedTV Box — auditoria, debloat em ondas e reparo da Play Store em TV Box.",
    )
    parser.add_argument(
        "comando",
        nargs="?",
        default="menu",
        choices=[
            "menu", "auditoria", "diagnostico", "debloat", "playstore", "comparar",
            "cache", "zram", "rede", "video", "boot", "virus", "seguranca",
            "widevine", "afinar", "abrir", "reiniciar", "ram", "reverter",
            "perguntar", "selftest", "primeira",
        ],
    )
    parser.add_argument("extra", nargs="*", help="pacote, ou o texto da pergunta")
    parser.add_argument("--sim", action="store_true", help="não pergunta; ondas 1, 2, 3 e 4")
    parser.add_argument("--sem-onda3", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--dispositivo", default=None)
    args = parser.parse_args(argv)
    if args.selftest or args.comando == "selftest":
        selftest()
        return 0
    iniciar_sessao()
    binary = find_adb()
    if not binary:
        say("Não achei o adb.")
        say("No Termux: pkg install android-tools python")
        say("No computador: Platform-Tools no PATH, ou a pasta platform-tools ao lado deste arquivo.")
        return 1
    serial = args.dispositivo or dispositivo()
    if not re.match(r"^[\w.:\-]+$", serial):
        say("Dispositivo inválido.")
        return 1
    adb = Adb(serial, binary)
    try:
        if args.comando == "menu":
            menu(adb, sim=args.sim, sem_onda3=args.sem_onda3)
        elif args.comando == "primeira":
            primeira_vez(adb, sim=args.sim, sem_onda3=args.sem_onda3)
        elif args.comando in ("auditoria", "diagnostico"):
            conectar_ou_explicar(adb)
            diagnostico(adb)
        elif args.comando == "debloat":
            executar_ondas(adb, sim=args.sim, sem_onda3=args.sem_onda3)
        elif args.comando == "playstore":
            playstore(adb, sim=args.sim)
        elif args.comando == "comparar":
            comparar()
        elif args.comando == "cache":
            limpar_cache(adb)
        elif args.comando == "zram":
            limpar_zram(adb, sim=args.sim)
        elif args.comando == "rede":
            ajustar_rede(adb, sim=args.sim)
        elif args.comando == "video":
            forcar_1080(adb, sim=args.sim)
        elif args.comando == "boot":
            analisar_boot(adb)
        elif args.comando in ("virus", "seguranca"):
            seguranca(adb, sim=args.sim)
        elif args.comando == "widevine":
            widevine(adb, sim=args.sim)
        elif args.comando == "afinar":
            afinar(adb, sim=args.sim)
        elif args.comando == "abrir":
            if not args.extra:
                say("Uso: python speedtvbox.py abrir com.android.vending")
                return 1
            abrir_cmd(adb, args.extra[0])
        elif args.comando == "reiniciar":
            conectar_ou_explicar(adb)
            ok = reiniciar_esperar(adb)
            say("Voltou." if ok else "Não voltou no prazo.")
        elif args.comando == "ram":
            status_ram(adb)
        elif args.comando == "reverter":
            reverter(adb, sim=args.sim)
        elif args.comando == "perguntar":
            texto = " ".join(args.extra).strip() or input("Pergunta: ").strip()
            perguntar_gemini(adb, texto)
    except DeviceOffline as exc:
        say("A TV Box saiu do ADB: %s" % exc)
        return 3
    except KeyboardInterrupt:
        say("\nInterrompido.")
        return 130
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        raise
    except Exception as exc:
        say("Falha inesperada: %s" % exc)
        code = 1
    if os.name == "nt" and sys.stdin.isatty() and len(sys.argv) <= 1:
        try:
            input("\nEnter para fechar…")
        except EOFError:
            pass
    raise SystemExit(code)
