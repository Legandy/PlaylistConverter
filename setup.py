from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="PlaylistConverter",
    version="1.0.0",
    author="Legandy",
    description="Sync and convert playlists between PC and Android",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/PlaylistConverter",  # Update with your repo
    py_modules=["main", "config", "conversion", "gui", "scheduler", "tray"],
    install_requires=[
        "requests",
        "pystray>=0.19.0",
        "Pillow>=8.0.0",
        "watchdog>=2.0.0"
    ],
    extras_require={
        "dev": ["pytest", "black", "flake8"]
    },
    entry_points={
        "console_scripts": [
            "playlistconverter=main:main",
            "playlist-converter=main:main"
        ]
    },
    include_package_data=True,
    package_data={
        "": ["*.ico", "*.md", "*.txt", "LICENSE.txt"]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: System :: Filesystems",
    ],
    python_requires=">=3.7",
)