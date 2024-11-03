from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="jupyter_whisper",
    version="0.1.0-beta.1",
    author="Maxime Rivest",
    author_email="mrive052@gmail.com",
    description="AI-Powered Chat Interface for Jupyter Notebooks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MaximeRivest/jupyter_whisper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: Jupyter",
        "Framework :: Jupyter :: JupyterLab",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="jupyter, chat, claude, ai, notebook, assistant",
    python_requires=">=3.7",
    install_requires=requirements,
    include_package_data=True,
    project_urls={
        "Bug Reports": "https://github.com/MaximeRivest/jupyter_whisper/issues",
        "Source": "https://github.com/MaximeRivest/jupyter_whisper",
    },
    package_data={
        'jupyter_whisper': ['static/*.js'],
    },
)
