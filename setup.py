from setuptools import setup

setup(
    name="PlaylistConverter",
    version="1.0.0",
    author="Legandy",
    description="Sync and convert playlists between PC and Android",
    py_modules=["PlaylistConverter"],
    install_requires=[
        "requests",
        "pystray",
        "Pillow",
        "watchdog"
    ],
    entry_points={
        "console_scripts": [
            "playlistconverter=PlaylistConverter:main"
        ]
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent"
    ],
)