"""Stable rank sorting for achievement and profile views.

Sort only the displayed rows; never change SQLite row order or achievement IDs.
"""


def sort_achievements(rows, direction='asc', rank_index=1):
    """Return a new list ordered by star count, preserving ties' input order."""
    if direction not in ('asc', 'desc'):
        raise ValueError('direction must be asc or desc')
    def rank(row):
        value = row[rank_index]
        if isinstance(value, int):
            return value
        return str(value).count('★')
    return sorted(rows, key=rank, reverse=(direction == 'desc'))
