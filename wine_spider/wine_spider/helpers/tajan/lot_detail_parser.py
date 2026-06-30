from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class TajanLotDetailParseResult:
    raw_detail_text: str
    description: str
    producer_candidates: tuple[str, ...]
    vintages: tuple[str, ...]
    match_text: str


class TajanLotDetailParser:
    """Parse producer and vintage hints from Tajan lot detail descriptions."""

    _leading_quantity_re = re.compile(
        r"^\s*(?:\d+|un|une|deux|trois|quatre|cinq|six|douze)\s+"
        r"(?:bouteille|bouteilles|btlle|btlles|btle|btles|btl|btls|magnum|magnums|flacon|flacons|caisse|caisses|lot|lots)\s+",
        re.IGNORECASE,
    )
    _producer_prefix_re = re.compile(
        r"^(?:ch[aâ]teau|domaine|maison|hospices|comte|comtes|marquis)\b",
        re.IGNORECASE,
    )
    _vintage_re = re.compile(r"\b(?:18|19|20)\d{2}\b")
    _noise_re = re.compile(r"\b(?:cb|cave\s*\d+)\b", re.IGNORECASE)
    _mixed_lot_intro_re = re.compile(
        r"^\s*(?:ensemble|lot)\s+de\s+(?:\d+|un|une|deux|trois|quatre|cinq|six|douze)\s+",
        re.IGNORECASE,
    )
    _embedded_producer_prefix_re = re.compile(
        _producer_prefix_re.pattern.removeprefix("^"),
        re.IGNORECASE,
    )
    _commercial_footer_re = re.compile(
        r"\b(?:payment\s*&\s*shipping|accepted\s+forms\s+of\s+payment)\b.*$",
        re.IGNORECASE,
    )

    _appellation_only_names = {
        "alsace",
        "batard montrachet",
        "batard-montrachet",
        "beaune",
        "bourgogne",
        "chambertin",
        "chambolle musigny",
        "chambolle-musigny",
        "clos de beze",
        "clos-de-beze",
        "corton",
        "meursault",
        "montrachet",
        "nuits saint georges",
        "nuits-saint-georges",
        "pomerol",
        "puligny montrachet",
        "puligny-montrachet",
        "sauternes",
        "volnay",
        "vosne romanee",
        "vosne-romanee",
    }

    def parse_detail_text(self, text: str | None) -> TajanLotDetailParseResult:
        raw_text = self._clean_space(text or "")
        raw_text = re.sub(r"^Additional Details\s+", "", raw_text, flags=re.IGNORECASE)
        description = self._strip_commercial_footer(raw_text).split("|", 1)[0].strip(" ,;")
        vintages = self._unique(self._vintage_re.findall(description))

        parts = self._description_parts(description)
        producer, producer_index = self._find_producer(parts)
        producer_candidates = (producer,) if producer else ()
        match_text = self._build_match_text(parts, producer, producer_index, vintages)

        return TajanLotDetailParseResult(
            raw_detail_text=raw_text,
            description=description,
            producer_candidates=producer_candidates,
            vintages=vintages,
            match_text=match_text,
        )

    def _description_parts(self, description: str) -> list[str]:
        text = self._leading_quantity_re.sub("", description)
        text = self._vintage_re.sub(" ", text)
        text = self._noise_re.sub(" ", text)
        text = self._clean_space(text).strip(" ,;")
        parts = [part.strip(" ,;") for part in text.split(",") if part.strip(" ,;")]
        return self._split_embedded_producer_parts(parts)

    def _strip_commercial_footer(self, text: str) -> str:
        return self._commercial_footer_re.sub("", text).strip(" ,;")

    def _split_embedded_producer_parts(self, parts: list[str]) -> list[str]:
        split_parts: list[str] = []
        for part in parts:
            match = self._embedded_producer_prefix_re.search(part)
            if match and match.start() > 0:
                prefix = part[: match.start()].strip(" ,;")
                producer = part[match.start() :].strip(" ,;")
                if prefix:
                    split_parts.append(prefix)
                if producer:
                    split_parts.append(producer)
            else:
                split_parts.append(part)

        return split_parts

    def _find_producer(self, parts: list[str]) -> tuple[str | None, int | None]:
        if parts and self._is_mixed_lot_description(parts[0]):
            return None, None

        for index, part in enumerate(parts[1:], start=1):
            if self._producer_prefix_re.search(part):
                return self._display_name(part), index

        if not parts:
            return None, None

        first_part = parts[0]
        if self._is_appellation_only(first_part):
            return None, None

        return self._display_name(first_part), 0

    def _is_mixed_lot_description(self, text: str) -> bool:
        return bool(self._mixed_lot_intro_re.search(text))

    def _build_match_text(
        self,
        parts: list[str],
        producer: str | None,
        producer_index: int | None,
        vintages: tuple[str, ...],
    ) -> str:
        if producer and producer_index is not None:
            context_parts = [
                part
                for index, part in enumerate(parts)
                if index != producer_index
            ]
            tokens = [producer, *context_parts, *vintages]
        else:
            tokens = [*parts, *vintages]

        return self._clean_space(" ".join(token for token in tokens if token))

    def _is_appellation_only(self, text: str) -> bool:
        return self._normalize_key(text) in self._appellation_only_names

    def _display_name(self, text: str) -> str:
        return self._clean_space(text).title()

    def _normalize_key(self, text: str) -> str:
        decomposed = unicodedata.normalize("NFKD", text)
        without_accents = "".join(
            char for char in decomposed if not unicodedata.combining(char)
        )
        normalized = re.sub(r"[^a-z0-9]+", " ", without_accents.lower())
        return self._clean_space(normalized).replace(" ", "-")

    def _clean_space(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _unique(self, values: list[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(values))
