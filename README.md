# Japanese Flashcard Manager

## Purpose
This app is meant to be used for managing Japanese flashcards to be imported into Anki.

## Motivation
This is an attempt at redoing my implementation of my jp_dict repository, which suffered from the following problems:
* The code was very unorganized, making it hard to manage.
* Development rules and conventions were not clearly defined, making the project difficult to maintain after scaling it up.
* User interaction was highly CLI based, making it very important to understand which scripts do what. However, since documentation was not created, it was easy to forget the projects structure after being inactive for long periods of time.
* There was several attempts to create a GUI interface for interacting with the app, but this ended up being abandoned each time after long periods of inactivity.

This project is an attempt to redo the jp_dict project from scratch. This time, we will enforce proper coding guidelines, directory structure, unit tests, and documentation. The hope is that this will enable a consistent development pipeline that can be maintained even after long periods of inactivity.