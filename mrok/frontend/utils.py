import re

from mrok.conf import get_settings


def parse_accept_header(accept: str | None) -> list[str]:
    if not accept:
        return ["*/*"]

    result: list[tuple[str, float, int]] = []

    for index, item in enumerate(accept.split(",")):
        item = item.strip()
        if not item:
            continue

        parts = [p.strip() for p in item.split(";")]
        media_type = parts[0].lower()

        q = 1.0
        for param in parts[1:]:
            if param.startswith("q="):
                try:
                    q = float(param[2:])
                except ValueError:
                    q = 0.0

        result.append((media_type, q, index))

    # Sort by:
    # 1) q value (desc)
    # 2) specificity (more specific first)
    # 3) original order (stable)
    result.sort(
        key=lambda x: (
            -x[1],
            -_media_type_specificity(x[0]),
            x[2],
        )
    )

    return [media_type for media_type, _, _ in result]


def _media_type_specificity(media_type: str) -> int:
    if media_type == "*/*":
        return 0
    if media_type.endswith("/*"):
        return 1
    return 2


def get_frontend_domain():
    settings = get_settings()
    return (
        settings.frontend.domain
        if settings.frontend.domain[0] == "."
        else f".{settings.frontend.domain}"
    )


def _get_target_from_header(headers: dict[str, str], name: str) -> str | None:
    domain_name = get_frontend_domain()
    header_value = headers.get(name, "")
    if domain_name in header_value:
        if ":" in header_value:
            header_value, _ = header_value.split(":", 1)
        return header_value[: -len(domain_name)]


def get_target_name(headers: dict[str, str]) -> str | None:
    settings = get_settings()

    target = _get_target_from_header(headers, "x-forwarded-host")
    if not target:
        target = _get_target_from_header(headers, "host")

    if target and (
        re.fullmatch(settings.identifiers.extension.regex, target)
        or re.fullmatch(settings.identifiers.instance.regex, target)
    ):
        return target
    return None
