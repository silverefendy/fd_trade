from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="fd_trade",
    version="0.0.1",
    description="Personal trading journal & risk management for IDX",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Efendy (silverefendy)",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
