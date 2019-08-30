from django.template.defaultfilters import register


@register.filter(name="paginate_loop")
def translate_document_category(page_obj, context=5):
    items = [1, page_obj.number, page_obj.paginator.num_pages]
    for i in range(context):
        items.append(max(1, page_obj.number - i))
        items.append(min(page_obj.number + i, page_obj.paginator.num_pages))

    last = 0
    for item in sorted(set(items)):
        if not last + 1 == item:
            yield None
        yield item
        last = item
