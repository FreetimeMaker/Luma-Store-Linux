project('luma-store-linux', version: '0.1.0')

python = import('python').find_installation('python3')

install_data(
  'src/main.py',
  install_dir: get_option('bindir'),
  rename: 'luma-store'
)

install_data(
  'data/com.freetime.lumastore.desktop',
  install_dir: join_paths(get_option('datadir'), 'applications')
)
