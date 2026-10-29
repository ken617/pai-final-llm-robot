import os
from glob import glob
from setuptools import setup

package_name = "llm_nav"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
        (os.path.join("share", package_name, "worlds"), glob("worlds/*.sdf")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    description="LLM-based natural language navigation for a diff-drive robot in Gazebo",
    license="MIT",
    entry_points={
        "console_scripts": [
            "llm_commander = llm_nav.llm_commander:main",
            "plan_executor = llm_nav.plan_executor:main",
            "say = llm_nav.say:main",
        ],
    },
)
