#!/bin/zsh

if [ "$1" = '--help' ]; then
  echo "Install all plugins from the 'local' directory."
  exit 0
fi

for plugin in local/*(N); do  # this is a nullglob
  echo "installing $plugin"

  cd $plugin
  python setup.py develop
  cd -
done
