from setuptools import setup

APP = ['launcher.py']
OPTIONS = {
    'argv_emulation': False,
    'packages': ['pygame', 'macimu'],
    'resources': ['angle_app.py'],
    'plist': {
        'CFBundleName': 'Screen Tilt',
        'CFBundleDisplayName': 'Screen Tilt',
        'CFBundleVersion': '1.0',
        'NSHighResolutionCapable': True,
    }
}
setup(app=APP, options={'py2app': OPTIONS}, setup_requires=['py2app'])
