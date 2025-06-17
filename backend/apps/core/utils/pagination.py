from django.db.models import Count


def pagination(queryset, serializer, page, size=15):
    page = page or 1
    offset = (page - 1) * size
    limit = offset + size
    serializer.instance = queryset[offset:limit]

    result = {'count': queryset.count(), 'results': serializer.data, 'page': page, 'size': size}

    return result


def nested_data_pagination(queryset, serializer, page, size=15):
    page = page or 1
    offset = (page - 1) * size
    limit = offset + size
    serializer.instance = queryset[offset:limit]
    total = 0
    for p in queryset.annotate(le_count=Count('replies')):
        total += p.le_count
    total += queryset.count()
    return {'count': total, 'results': serializer.data, 'page': page, 'size': size}
