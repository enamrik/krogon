from setuptools import setup, find_packages


def read_file(filename):
    with open(filename) as f:
        return f.read()


setup(
    python_requires="~=3.7",
    name="krogon",
    version=read_file("./krogon/VERSION").strip(),
    description="Network Infrastructure for TVE Services on GCP",
    long_description=read_file("README.md"),
    author="NBCUniversalTech Devs",
    author_email="tve.devs@nbcuni.com",
    url="https://github.com/nbcu-DigitalDistribution/krogon",
    license=read_file("LICENSE"),
    packages=find_packages(exclude=("tests", "outputs")),
    package_data={"krogon": ["VERSION", "*.txt", "*.yml", "*.template", "*.ini", "bin/**/*"]},
    include_package_data=True,
    install_requires=[
        # https://github.com/pypa/pipenv/issues/1263#issuecomment-362600555
        'google-api-python-client==1.7.7',
        'ruamel.yaml==0.15.87',
        'click==7.0'
    ],
    extras_require={
        'dev': ['pytest', 'dictdiffer==0.7.1']
    },
    entry_points = {
        "console_scripts": [
            "krogon=krogon.krogon_cli:main",
        ],
    },
)
