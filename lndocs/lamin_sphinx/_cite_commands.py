# -------------------------------------------------------------------------------------
# cite commands

from types import MappingProxyType  # noqa
from typing import Any, Mapping, NamedTuple, Sequence  # noqa

from docutils import nodes  # type:ignore # noqa
from docutils.parsers.rst.directives import class_option  # type:ignore # noqa
from docutils.parsers.rst.states import Inliner  # type:ignore # noqa
from sphinx.application import Sphinx  # noqa
from sphinx.config import Config  # noqa


class AutoLink(NamedTuple):
    class_name: str
    url_template: str
    title_template: str = "{}"  # noqa
    options: Mapping[str, Any] = MappingProxyType({"class": class_option})  # noqa

    def __call__(  # noqa
        self,
        name: str,
        rawtext: str,
        text: str,
        lineno: int,
        inliner: Inliner,
        options: Mapping[str, Any] = MappingProxyType({}),
        content: Sequence[str] = (),
    ):
        url = self.url_template.format(text)
        title = self.title_template.format(text)
        options = {**dict(classes=[self.class_name]), **options}
        node = nodes.reference(rawtext, title, refuri=url, **options)
        return [node], []


def register_cite(app: Sphinx, config: Config):
    # This follows the convention of natbib's \citet (Text) and \citep (Parantheses/Brackets)  # noqa
    app.add_role("ct", AutoLink("ct", "#{}", "{}"))
    app.add_role("cp", AutoLink("cp", "#{}", "[{}]"))
