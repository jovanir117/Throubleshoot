from __future__ import annotations

import ipaddress
import re


CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
COMMAND_META_CHARS = re.compile(r'[&|<>^"`]')
MODEL_CHARS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,49}$")


def clean_text(value: str, max_len: int) -> str:
    cleaned = " ".join(value.strip().split())
    if CONTROL_CHARS.search(cleaned):
        raise ValueError("El texto contiene caracteres de control.")
    if len(cleaned) > max_len:
        raise ValueError(f"El texto excede {max_len} caracteres.")
    return cleaned


def clean_optional_text(value: str, max_len: int) -> str | None:
    cleaned = clean_text(value, max_len)
    return cleaned or None


def validate_model(value: str) -> str | None:
    cleaned = clean_optional_text(value, 50)
    if cleaned and not MODEL_CHARS.fullmatch(cleaned):
        raise ValueError("Modelo invalido. Usa letras, numeros, espacios, punto, guion o guion bajo.")
    return cleaned


def validate_ip(value: str) -> str | None:
    cleaned = clean_optional_text(value, 45)
    if not cleaned:
        return None
    try:
        return str(ipaddress.ip_address(cleaned))
    except ValueError as exc:
        raise ValueError("IP invalida.") from exc


def validate_printer_system_name(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = clean_text(value, 200)
    if COMMAND_META_CHARS.search(cleaned):
        raise ValueError("Nombre de impresora contiene caracteres no permitidos.")
    return cleaned
