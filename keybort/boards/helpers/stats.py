from collections import Counter

from .. import const


def stat_rows(values):
    labels = {}
    counts = Counter()
    for value in values:
        value = (value or '').strip()
        if value:
            key = value.casefold()
            labels.setdefault(key, value)
            counts[key] += 1
    return sorted(
        ({'label': labels[key], 'count': count} for key, count in counts.items()),
        key=lambda row: (-row['count'], row['label'].casefold()),
    )


def stat_leader(values):
    rows = stat_rows(values)
    if not rows:
        return None
    return {
        **rows[0],
        'tied': sum(row['count'] == rows[0]['count'] for row in rows[1:]),
    }


def stat_breakdown(title, values):
    values = list(values)
    all_rows = stat_rows(values)
    rows = all_rows[: const.STATS_BREAKDOWN_ROWS]
    other = sum(row['count'] for row in all_rows[const.STATS_BREAKDOWN_ROWS :])
    not_set = len(values) - sum(row['count'] for row in all_rows)
    if other:
        rows.append({'label': 'Other', 'count': other, 'muted': True})
    if not_set:
        rows.append({'label': 'Not set', 'count': not_set, 'muted': True})
    for row in rows:
        row['percent'] = round(100 * row['count'] / len(values))
    return {'title': title, 'rows': rows, 'total': len(values)}


def typing_sparkline(results):
    width = const.TYPING_SPARKLINE_WIDTH
    height = const.TYPING_SPARKLINE_HEIGHT
    inset = const.TYPING_SPARKLINE_INSET
    values = [result.wpm for result in results]
    low, high = min(values), max(values)
    wpm_range = max(high - low, const.TYPING_SPARKLINE_MIN_WPM_RANGE)
    bottom = (low + high - wpm_range) / 2
    x_step = (width - 2 * inset) / max(len(values) - 1, 1)
    y_step = (height - 2 * inset) / wpm_range
    points = [
        {
            'x': round(inset + index * x_step, 1),
            'y': round(height - inset - (value - bottom) * y_step, 1),
            'label': f'{value:.0f} WPM',
        }
        for index, value in enumerate(values)
    ]
    return {
        'width': width,
        'height': height,
        'points': points,
        'line': ' '.join(f'{point["x"]},{point["y"]}' for point in points),
        'last': points[-1],
    }
