
from setuptools import setup, find_packages

setup(
    name='jupyterchat',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'jupyterchat.static': ['*.js'],
        'jupyterchat.config': ['*.yaml'],
    },
    install_requires=[
        'ipython>=7.0.0',
        'jupyter>=1.0.0',
        'ipylab>=0.5.0',
        'fastapi>=0.68.0',
        'uvicorn>=0.15.0',
        'pyyaml>=5.4.1',
        'requests>=2.26.0',
        'psutil>=5.8.0',
        'nest-asyncio>=1.5.1',
        'openai>=1.0.0',
        'anthropic>=0.3.0',
        'python-multipart>=0.0.5',
    ],
    python_requires='>=3.7',
)
