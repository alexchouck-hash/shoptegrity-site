"""Citation checks shared by the routers and web views.

A named company's ownership is shown only when a published evidence row for that
entity carries a source URL. Anything else is withheld (see the sourced-or-withheld
policy in methodology.html).
"""


# A parent name is a claim about the link between a brand and its parent company. The
# only record that establishes that link is a "parent_link" row. An entity's own filing
# (for example, its public listing) says nothing about which brands it owns.
PARENT_LINK_DIMENSION = "parent_link"


def has_cited_ownership(entity) -> bool:
    """True when a published parent_link record with a source URL ties this brand to its parent."""
    return any(
        ev.dimension == PARENT_LINK_DIMENSION and ev.status == "published" and bool(ev.source_url)
        for ev in entity.evidence_items
    )


def cited_ownership_name(entity):
    """The entity name when its ownership is cited, otherwise None."""
    return entity.name if has_cited_ownership(entity) else None


def cited_ownership_type(entity):
    """The raw ownership_type when its ownership is cited, otherwise None."""
    return entity.ownership_type if has_cited_ownership(entity) else None
