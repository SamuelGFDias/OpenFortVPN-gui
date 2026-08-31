import re

PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
KNOWN_KEYS = {"host", "port", "username", "password"}


def sanitize_profile_filename(name: str) -> str:
    name = name.strip()
    if not name.endswith(".conf"):
        name += ".conf"
    return name


def validate_new_profile(
    name: str,
    host: str,
    port: str,
    existing_profiles: list[str] | None = None,
    editing_name: str | None = None,
) -> str | None:
    name = name.strip()
    if not name:
        return "Informe um nome para o perfil"
    if not PROFILE_NAME_RE.match(name):
        return "Nome do perfil deve conter apenas letras, números, '.', '_' e '-'"
    if not host.strip():
        return "Informe o host do servidor VPN"
    port = port.strip()
    if port and not port.isdigit():
        return "Porta deve ser um número"
    sanitized = sanitize_profile_filename(name)
    if existing_profiles is not None and sanitized in existing_profiles and sanitized != editing_name:
        return "Já existe um perfil com esse nome"
    return None


def build_profile_config(
    host: str, port: str, username: str, password: str, extra: dict[str, str] | None = None
) -> str:
    lines = [f"host = {host.strip()}"]
    port = port.strip() or "443"
    lines.append(f"port = {port}")
    if username.strip():
        lines.append(f"username = {username.strip()}")
    if password:
        lines.append(f"password = {password}")
    if extra:
        for key, value in extra.items():
            if key not in KNOWN_KEYS:
                lines.append(f"{key} = {value}")
    return "\n".join(lines) + "\n"


def parse_profile_config(content: str) -> dict[str, str]:
    # Round-trip genérico: preserva qualquer campo do formato openfortivpn (ex.:
    # trusted-cert, otp) que a UI não edite diretamente, para não perdê-los ao
    # reescrever um perfil editado pela GUI.
    fields: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        fields[key.strip()] = value.strip()
    return fields
