from setuptools import setup, find_packages


def read_file(filename):
    with open(filename) as f:
        return f.read()


setup(
    python_requires="~=3.7",
    name="krogon",
    version=read_file("./krogon/VERSION").strip(),
    description="Tool for generating and executing K8s templates",
    long_description=read_file("README.md"),
    author="Kirmanie L Ravariere",
    author_email="enamrik@gmail.com",
    url="https://github.com/enamrik/krogon",
    license=read_file("LICENSE"),
    packages=find_packages(exclude=("tests", "outputs")),
    package_data={"krogon": ["URL", "VERSION", "*.txt", "*.yml", "*.template", "**/*.sh", "*.ini", "bin/**/*"]},
    include_package_data=True,
    install_requires=[
        'google-api-python-client==1.7.7',
        'ruamel.yaml==0.15.87',
        'click==7.0',
        'bcrypt==3.1.6',
        'requests==2.31.0'
    ],
    extras_require={
        'dev': [
            'pytest',
            'dictdiffer==0.7.1',
            'python-mock@git+ssh://git@github.com/enamrik/python-mock.git'
        ]
    },
    entry_points={
        "console_scripts": [
            "krogon=krogon.krogon_cli:main",
        ],
    },
)
