import os
from django import template
import markdown2

register = template.Library()
 
@register.filter
def md(text):
    return markdown2.markdown(text, extras=["markdown-in-html","nl2br","tables","wiki-tables"])
    #return markdown2.markdown(text, extras=["extra"])
 
    #Use it like this in your template
    #{{var|md}}

register.filter('md', md)

@register.filter
def ext(text):
    name, extension = os.path.splitext(text)
    return extension

register.filter('ext', ext)
