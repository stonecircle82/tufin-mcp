from setuptools import setup, find_packages

setup(
    name="tufin_mcp_client",
    version="0.1.0", # Read from __init__.py later?
    author="Your Name", # Replace
    author_email="your.email@example.com", # Replace
    description="Client library for the Tufin MCP Server API",
    long_description=open('README.md').read() if os.path.exists('README.md') else '',
    long_description_content_type="text/markdown",
    url="<your_repo_url>", # Replace
    packages=find_packages(where="."), # Find packages in the current directory
    install_requires=[
        "httpx>=0.20",
        # Add pydantic if returning models later
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License", # Choose your license
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
) 