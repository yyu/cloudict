import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cloudict",
    version="0.0.3",

    install_requires=[
    ],

    author="Yuan \"Forrest\" Yu",
    author_email="yy@yuyuan.org",

    description="a dict backed by cloud",
    long_description=long_description,
    long_description_content_type="text/markdown",

    url="https://github.com/yyu/cloudict",

    packages=setuptools.find_packages(),

    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
