from setuptools import setup, find_packages


setup(
    name="boneless",
    version="0.1",
    author="whitequark",
    author_email="whitequark@whitequark.org",
    description="Resource-efficient 16-bit CPU architecture for FPGA control plane",
    #long_description="""TODO""",
    license="0-clause BSD License",
    install_requires=["nmigen", "parse>=1.12"],
    packages=find_packages(),
    project_urls={
        #"Documentation": "https://glasgow.readthedocs.io/",
        "Source Code": "https://github.com/whitequark/Boneless-CPU",
        "Bug Tracker": "https://github.com/whitequark/Boneless-CPU/issues",
    },
    entry_points={
        "console_scripts": [
            "boneless-as = boneless.cli:as_main",
            "boneless-dis = boneless.cli:dis_main",
        ]
    }
)
