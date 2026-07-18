#!/bin/zsh

echo "=============================="
echo "Running verification..."
echo "=============================="

python -m pytest -q || exit 1

echo
echo "=============================="
echo "Task diff"
echo "=============================="

git --no-pager diff HEAD

echo
echo "=============================="
echo "Diff check"
echo "=============================="

git --no-pager diff --check
