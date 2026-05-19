import tomli


def dependency_names(pyproject_text: str) -> list[str]:
    data = tomli.loads(pyproject_text)
    dependencies = data.get("project", {}).get("dependencies", [])
    if not dependencies:
        return []
    return dependencies[0]

