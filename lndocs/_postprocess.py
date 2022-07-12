from pathlib import Path


def replace_index_targets(filepath, project_slug):
    with open(filepath) as f:
        content = f.read()
    content = content.replace("/index", "")
    with open(filepath, "w") as f:
        f.write(content)


def replace_image_targets(filepath, project_slug):
    with open(filepath) as f:
        content = f.read()
    content = content.replace("_images/", f"{project_slug}/_images/")
    with open(filepath, "w") as f:
        f.write(content)


def update_index_file(filepath):

    with open(filepath) as f:
        content = f.read()

    Path(filepath).unlink()

    # fmt: off
    content = content\
        .replace("](", f"]({filepath.parent.stem}/")\
        .replace("}`", "}" + f"`{filepath.parent.stem}/")
    # fmt: on
    # revert for all http links
    content = content.replace(f"]({filepath.parent.stem}/http", "](http")

    # parse out indexed file list
    if "```{toctree}" in content:
        toctree = content.split("```{toctree}")[1]
        toctree = toctree.split("\n\n")[1]
        toctree = toctree.split("```")[0]

        toctree = toctree.strip("\n")

        toctree_split = toctree.split("\n")
        toctree_new = "\n".join(
            [f"{filepath.parent.stem}/{file}" for file in toctree_split]
        )

        content = content.replace(toctree, toctree_new)

    with open(f"{filepath.parent}.md", "w") as f:
        f.write(content)
