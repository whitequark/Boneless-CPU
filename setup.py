from setuptools import setup, find_packages

setup(
    name="boneless_sim",
    version="0.1.0",
    description="Simulator for the Boneless CPU",
    long_description=open("README.md").read(),
    url="https://github.com/cr1901/boneless-sim",
    author="William D. Jones",
    author_email="thor0505@comcast.net",
    license="0-clause BSD License",
    packages=find_packages(exclude=["tests"]),
    platforms=["Any"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Topic :: System :: Emulators",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7"
    ],
)
