from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need
# fine tuning.
buildOptions = dict(packages=[], excludes=[])

base = 'Console'

executables = [
    Executable('MEGAabuse.py', base=base)
]

setup(name='MEGAabuse',
      version='1.0',
      description='For uploading files to mega in bulk',
      options=dict(build_exe=buildOptions),
      executables=executables)
