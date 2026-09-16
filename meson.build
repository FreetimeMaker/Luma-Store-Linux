project('luma-store', 'c', version: '0.1.0', default_options: ['warning_level=2', 'c_std=c11'])

gtk = dependency('gtk+-3.0', version: '>=3.24')

executable(
  'luma-store',
  'src/main.c',
  dependencies: gtk,
  install: true,
)

install_data(
  'data/com.freetime.LumaStore.desktop',
  install_dir: join_paths(get_option('datadir'), 'applications')
)
