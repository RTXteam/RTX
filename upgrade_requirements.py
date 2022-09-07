

def get_package_name(package_with_version: str) -> str:
    return package_with_version.split("=")[0].replace(">", "").replace("<", "")


with open(f"requirements.txt") as old_requirements_file:
    old_requirements = tuple(old_requirements_file)
with open(f"requirements-newfreeze.txt") as new_freeze_file:
    new_requirements = tuple(new_freeze_file)
packages_dict = dict()

index_line = old_requirements[0]
for old_requirement in old_requirements[1:]:  # Skip the --index line
    old_requirement.replace("\n", "")
    package = get_package_name(old_requirement)
    old_version_str = old_requirement.replace(package, "")
    packages_dict[package] = old_version_str

for new_requirement in new_requirements:
    package = get_package_name(new_requirement)
    if package in packages_dict:
        version_str = new_requirement.replace(package, "")
        packages_dict[package] = version_str

with open(f"requirements_new.txt", "w+") as requirements_file:
    requirements_file.write(index_line)
    for package, version_str in packages_dict.items():
        requirements_file.write(f"{package}{version_str}")
