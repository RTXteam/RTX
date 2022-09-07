

def get_package_name(package_with_version: str) -> str:
    return package_with_version.split("=")[0].replace(">", "").replace("<", "")


old_requirements = tuple(open("requirements.txt", 'r'))
new_freeze = tuple(open("freeze-new.txt", 'r'))
packages_dict = dict()

for old_requirement in old_requirements:
    package = get_package_name(old_requirement)
    packages_dict[package] = None

for new_requirement in new_freeze:
    package = get_package_name(new_requirement)
    if package in packages_dict:
        version_str = new_requirement.replace(package, "")
        packages_dict[package] = version_str
        print(f"New version for {package} is {version_str}")

with open(f"requirements.txt", "w+") as requirements_file:
    for package, version_str in packages_dict.items():
        requirements_file.write(f"{package}{version_str}")
