# The class AutoLink and the register_cite function are based on the
# the Scanpy repository:
# https://github.com/scverse/scanpy/blob/536ed15bc73ab5d1131c0d530dd9d4f2dc9aee36/docs/extensions/github_links.py
# It's BSD3 licensed as follows:
#
# BSD 3-Clause License

# Copyright (c) 2017 F. Alexander Wolf, P. Angerer, Theis Lab
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.

# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.

# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


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
