# lndocs: Lamin static site generator

This is a command line documentation tool (currently) only meant for Lamin-related projects: If unaffiliated with Lamin, we recommend to not rely on lndocs.

- Given our small team with limited bandwidth, we cannot offer support for documenting projects that are not related to Lamin.
- We will likely make drastic changes to this package that are not going to be backward compatible without any warnings.
- We _might_ develop the package into a general-purpose docs builder longer into the future.

Install via:

```
pip install git+https://github.com/laminlabs/lndocs.git
```

Build the docs by running `lndocs` in the root of your project repository:

```
lndocs
```

Useful flags:

- `--strict`: fail on warnings
- `--blog`: enable blog layout overrides (loads `blog.css` on top of `custom.css`)
- `--format text`: export text output (`llms.txt`) instead of HTML

Acknowledgements:

`lndocs` builds on docutils, Sphinx, Bootstrap, `pydata-sphinx-theme`, and several other open-source tools.
