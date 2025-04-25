from setuptools import setup

setup(
    name="latex-to-llm",
    version="0.1.0",
    py_modules=["latex-to-llm"],
    install_requires=[
        "PyYAML>=5.3.1",
    ],
    entry_points={
        "console_scripts": [
            "latex-to-llm=latex-to-llm:main",
        ],
    },
    author="Marius Trovik",
    description="Export only the actively used LaTeX files into text dumps for LLM consumption.",
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
)
