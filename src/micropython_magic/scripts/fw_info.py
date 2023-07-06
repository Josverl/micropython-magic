# %%micropython
import os
import sys


def _build(s):
    # extract a build nr from a string
    if not s:
        return ""
    if " on " in s:
        s = s.split(" on ", 1)[0]
    return s.split("-")[1] if "-" in s else ""


def _info():  # type:() -> dict[str, str]
    # sourcery skip: use-contextlib-suppress, use-fstring-for-formatting, use-named-expression
    info = dict(
        {
            "family": sys.implementation.name,
            "version": "",
            "build": "",
            "ver": "",
            "port": "stm32" if sys.platform.startswith("pyb") else sys.platform,  # port: esp32 / win32 / linux / stm32
            "board": "GENERIC",
            "cpu": "",
            "mpy": "",
            "arch": "",
        }
    )
    try:
        info["version"] = ".".join([str(n) for n in sys.implementation.version])
    except AttributeError:
        pass
    try:
        machine = sys.implementation._machine if "_machine" in dir(sys.implementation) else os.uname().machine
        info["board"] = machine.strip()
        info["cpu"] = machine.split("with")[1].strip()
        info["mpy"] = (
            sys.implementation._mpy
            if "_mpy" in dir(sys.implementation)
            else sys.implementation.mpy
            if "mpy" in dir(sys.implementation)
            else ""
        )
    except (AttributeError, IndexError):
        pass

    try:
        # extract build from uname().version if available
        info["build"] = _build(os.uname()[3])
        if not info["build"]:
            # extract build from uname().release if available
            info["build"] = _build(os.uname()[2])
        if not info["build"] and ";" in sys.version:
            # extract build from uname().release if available
            info["build"] = _build(sys.version.split(";")[1])
    except (AttributeError, IndexError):
        pass
    # avoid  build hashes
    if info["build"] and len(info["build"]) > 5:
        info["build"] = ""

    if info["version"] == "" and sys.platform not in ("unix", "win32"):
        try:
            u = os.uname()
            info["version"] = u.release
        except (IndexError, AttributeError, TypeError):
            pass
    # detect families
    for fam_name, mod_name, mod_thing in [
        ("pycopy", "pycopy", "const"),
        ("pycom", "pycom", "FAT"),
        ("ev3-pybricks", "pybricks.hubs", "EV3Brick"),
    ]:
        try:
            _t = __import__(mod_name, None, None, (mod_thing))
            info["family"] = fam_name
            del _t
            break
        except (ImportError, KeyError):
            pass

    if info["family"] == "ev3-pybricks":
        info["release"] = "2.0.0"

    if info["family"] == "micropython":
        if (
            info["version"]
            and info["version"].endswith(".0")
            and info["version"] >= "1.10.0"  # versions from 1.10.0 to 1.20.0 do not have a micro .0
            and info["version"] <= "1.19.9"
        ):
            # drop the .0 for newer releases
            info["version"] = info["version"][:-2]

    # spell-checker: disable
    if "mpy" in info and info["mpy"]:  # mpy on some v1.11+ builds
        sys_mpy = int(info["mpy"])
        # .mpy architecture
        arch = [
            None,
            "x86",
            "x64",
            "armv6",
            "armv6m",
            "armv7m",
            "armv7em",
            "armv7emsp",
            "armv7emdp",
            "xtensa",
            "xtensawin",
        ][sys_mpy >> 10]
        if arch:
            info["arch"] = arch
        # .mpy version.minor
        info["mpy"] = "v{}.{}".format(sys_mpy & 0xFF, sys_mpy >> 8 & 3)
    # simple to use version[-build] string
    info["ver"] = f"v{info['version']}-{info['build']}" if info["build"] else f"v{info['version']}"

    return info


print(_info())
del _info, _build
