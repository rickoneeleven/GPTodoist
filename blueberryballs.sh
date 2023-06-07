#!/bin/bash
git config --global user.email "pinescore@outlook.com"
git config --global user.name "Ryan Alexander Partington"

git pull
#https://github.com/psf/black
black ./

git add .

git status
read -n 1 -p "Continue? (y/n) " cont
if [ "$cont" != "y" ]; then exit 1; fi

echo
echo

git diff --cached -U0
read -n 1 -p "Continue? (y/n) " cont
if [ "$cont" != "y" ]; then exit 1; fi

#pytest --cov=main --cov-report term-missing --cov-fail-under=50
#read -n 1 -p "Continue? (y/n) " cont
#if [ "$cont" != "y" ]; then exit 1; fi

echo
echo
read -p "Commit message: " message
git commit -m "$message"
echo
echo
git push
echo
echo
git status
