from django import template

from core.html_utils import safe_html as render_safe_html

register = template.Library()


@register.filter(name="safe_html")
def safe_html_filter(value):
    return render_safe_html(value)
