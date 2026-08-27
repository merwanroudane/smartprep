"""Canonical entity graph for geographic reference data (AD-008).

A static ``country -> [city]`` mapping is not sufficient. During baseline
verification such a map under-reported country/city conflicts (24 instead of 26)
purely because ``Marrakesh`` and ``Marrakech`` were treated as different places.

Every reference entity therefore carries its aliases, transliterations and
language variants, and resolution reports *how* it matched so that downstream
confidence can reflect the match quality.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from ..core.enums import MatchKind

__all__ = ["CanonicalEntity", "EntityPack", "Resolution", "fold", "WORLD"]


def fold(value: str) -> str:
    """Normalise a surface form for comparison.

    Drops combining marks, case-folds and collapses whitespace, so ``Algérie``
    and ``Algerie`` compare equal.

    It deliberately does **not** encode to ASCII. Doing so erases non-Latin
    scripts entirely -- every Arabic name would fold to the empty string and
    collide with every other -- which is a silent, total loss of meaning rather
    than the accent-insensitivity that was wanted.

    This is a *comparison* key only. It is never written back to the data.
    """
    decomposed = unicodedata.normalize("NFKD", value)
    unmarked = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", unmarked).strip().casefold()


@dataclass(frozen=True)
class CanonicalEntity:
    """One real-world place, with every surface form that denotes it."""

    id: str
    canonical_name: str
    kind: str  # "country" | "city"
    parent: str | None = None
    aliases: tuple[str, ...] = ()
    transliterations: tuple[str, ...] = ()
    language_variants: tuple[str, ...] = ()
    historical_names: tuple[str, ...] = ()

    def surface_forms(self) -> dict[str, MatchKind]:
        forms: dict[str, MatchKind] = {fold(self.canonical_name): MatchKind.EXACT}
        for group, kind in (
            (self.aliases, MatchKind.ALIAS),
            (self.transliterations, MatchKind.TRANSLITERATION),
            (self.language_variants, MatchKind.LANGUAGE_VARIANT),
            (self.historical_names, MatchKind.HISTORICAL),
        ):
            for form in group:
                forms.setdefault(fold(form), kind)
        return forms


@dataclass(frozen=True)
class Resolution:
    """Outcome of resolving a surface form against a pack."""

    entity: CanonicalEntity | None
    match_kind: MatchKind
    confidence: float

    @property
    def resolved(self) -> bool:
        return self.entity is not None


_UNRESOLVED = Resolution(None, MatchKind.UNRESOLVED, 0.0)

_MATCH_CONFIDENCE = {
    MatchKind.EXACT: 1.0,
    MatchKind.ALIAS: 0.99,
    MatchKind.TRANSLITERATION: 0.97,
    MatchKind.LANGUAGE_VARIANT: 0.96,
    MatchKind.HISTORICAL: 0.90,
    MatchKind.FUZZY: 0.70,
}


@dataclass
class EntityPack:
    """A versioned, pluggable collection of canonical entities."""

    name: str
    version: str
    entities: tuple[CanonicalEntity, ...] = ()
    _index: dict[tuple[str, str], tuple[CanonicalEntity, MatchKind]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        for entity in self.entities:
            for form, kind in entity.surface_forms().items():
                key = (entity.kind, form)
                if key in self._index and self._index[key][0].id != entity.id:
                    raise ValueError(
                        f"ambiguous surface form {form!r} for kind {entity.kind!r}: "
                        f"claimed by both {self._index[key][0].id} and {entity.id}"
                    )
                self._index.setdefault(key, (entity, kind))

    def resolve(self, value: object, kind: str) -> Resolution:
        """Resolve a raw cell value to a canonical entity.

        An unknown value returns an unresolved result. It is never silently
        treated as consistent -- callers must surface it as ``UNKNOWN_ENTITY``.
        """
        if not isinstance(value, str) or not value.strip():
            return _UNRESOLVED
        hit = self._index.get((kind, fold(value)))
        if hit is None:
            return _UNRESOLVED
        entity, match_kind = hit
        return Resolution(entity, match_kind, _MATCH_CONFIDENCE[match_kind])

    def get(self, entity_id: str) -> CanonicalEntity:
        return next(e for e in self.entities if e.id == entity_id)


def _country(
    eid: str,
    name: str,
    *,
    aliases: tuple[str, ...] = (),
    transliterations: tuple[str, ...] = (),
    language_variants: tuple[str, ...] = (),
    historical_names: tuple[str, ...] = (),
) -> CanonicalEntity:
    return CanonicalEntity(
        id=eid,
        canonical_name=name,
        kind="country",
        aliases=aliases,
        transliterations=transliterations,
        language_variants=language_variants,
        historical_names=historical_names,
    )


def _city(
    eid: str,
    name: str,
    parent: str,
    *,
    aliases: tuple[str, ...] = (),
    transliterations: tuple[str, ...] = (),
    language_variants: tuple[str, ...] = (),
    historical_names: tuple[str, ...] = (),
) -> CanonicalEntity:
    return CanonicalEntity(
        id=eid,
        canonical_name=name,
        kind="city",
        parent=parent,
        aliases=aliases,
        transliterations=transliterations,
        language_variants=language_variants,
        historical_names=historical_names,
    )


#: Reference pack covering the entities present in the stress fixture.
#: Deliberately small -- a full gazetteer belongs in an installable geo plugin.
WORLD = EntityPack(
    name="smartprep.geo.minimal",
    version="0.1.0",
    entities=(
        _country("DZ", "Algeria", aliases=("Algerie", "Algeria"), language_variants=("الجزائر",)),
        _country("MA", "Morocco", aliases=("Maroc",), language_variants=("المغرب",)),
        _country("TN", "Tunisia", aliases=("Tunisie",), language_variants=("تونس",)),
        _country("EG", "Egypt", aliases=("Egypte",), language_variants=("مصر",)),
        _country("FR", "France", language_variants=("فرنسا",)),
        # Algeria
        _city(
            "DZ.ALG",
            "Algiers",
            "DZ",
            transliterations=("Alger",),
            language_variants=("الجزائر",),
        ),
        _city("DZ.ORN", "Oran", "DZ", language_variants=("وهران",)),
        _city("DZ.CST", "Constantine", "DZ", language_variants=("قسنطينة",)),
        _city("DZ.ANB", "Annaba", "DZ", historical_names=("Bone",)),
        _city("DZ.SET", "Setif", "DZ", transliterations=("Setif", "Sétif")),
        _city("DZ.TLM", "Tlemcen", "DZ"),
        # Morocco -- the alias pair that the flat map missed
        _city("MA.CAS", "Casablanca", "MA", historical_names=("Anfa",)),
        _city("MA.RAB", "Rabat", "MA"),
        _city("MA.FES", "Fes", "MA", transliterations=("Fez", "Fès")),
        _city("MA.MRK", "Marrakech", "MA", transliterations=("Marrakesh", "Marrakech")),
        _city("MA.TNG", "Tangier", "MA", transliterations=("Tanger", "Tangiers")),
        # Tunisia
        _city("TN.TUN", "Tunis", "TN"),
        _city("TN.SFX", "Sfax", "TN"),
        _city("TN.SOU", "Sousse", "TN"),
        _city("TN.BIZ", "Bizerte", "TN", transliterations=("Bizerta",)),
        # Egypt
        _city("EG.CAI", "Cairo", "EG", transliterations=("Al Qahirah",)),
        _city("EG.ALX", "Alexandria", "EG", transliterations=("Iskandariyah",)),
        _city("EG.GIZ", "Giza", "EG", transliterations=("Gizeh",)),
        _city("EG.MAN", "Mansoura", "EG", transliterations=("El Mansura",)),
        # France
        _city("FR.PAR", "Paris", "FR"),
        _city("FR.LYO", "Lyon", "FR", transliterations=("Lyons",)),
        _city("FR.MRS", "Marseille", "FR", transliterations=("Marseilles",)),
        _city("FR.LIL", "Lille", "FR"),
        _city("FR.TLS", "Toulouse", "FR"),
    ),
)

#: Expected domestic currency per country. A mismatch is *contextual*, never a
#: hard error -- foreign-currency invoicing is legitimate (AD-009).
EXPECTED_CURRENCY = {"DZ": "DZD", "MA": "MAD", "TN": "TND", "EG": "EGP", "FR": "EUR"}
