
from setuptools import find_packages, setup

from dcs5.__init__ import VERSION

setup(
    name="dcs5",
    version=VERSION,
    author="JeromeJGuay,",
    author_email="jerome.guay@dfo-mpo.gc.ca",
    description="""BigFin Dcs5 Board Controller Board.""",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={"": ["*.json"]},
    include_package_data=True,
    classifiers=["Programming Language :: Python :: 3"],
    python_requires="~=3.8",
    entry_points={"console_scripts": ["dcs5=dcs5.main:main", ]},
)
