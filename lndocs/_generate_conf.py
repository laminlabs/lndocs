from pathlib import Path

import jinja2
import yaml  # type: ignore


def generate_conf(directory):
    HERE = Path(__file__).parent
    templateLoader = jinja2.FileSystemLoader(searchpath=HERE)
    templateEnv = jinja2.Environment(loader=templateLoader)
    TEMPLATE_FILE = "_template_conf.py"
    template = templateEnv.get_template(TEMPLATE_FILE)

    with open("./lamin-project.yaml") as f:
        try:
            variables = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(exc)
            quit()

    # see the cookiecutter.json!
    if "project_slug" not in variables:
        variables["project_slug"] = variables["project_name"].lower().replace(" ", "-")
    if "package_name" not in variables:
        variables["package_name"] = variables["project_slug"].lower().replace("-", "_")

    # prefix with `lamin_`
    variables_template = {}
    for key, value in variables.items():
        variables_template["lamin_" + key] = variables[key]

    outputText = template.render(variables_template)

    with open(Path(directory) / "conf.py", "w") as f:
        f.write(outputText)

    return outputText
