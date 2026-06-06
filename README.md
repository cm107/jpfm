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

## Things That Need To Be Added To WORKING_PROGRESS.md
* Right now I can't find any informative logs being created under `storeage/logs/` that reflect the events that were fired during a `python main.py` session. We need to add more informative logs to the app and also separate logs execution timestamps.
* Right now we can add words to the word list manually, and also import words from the browser history. However, we still need to implement the following functionality:
  * A progress bar for the "Import History" process. Right now the user has no idea how much longer to wait until the process finishes.
  * Manually removing existing words from the word list via word item's X button.
  * Automatically 'pruning' words from the word list that don't follow a list of conditions specified by the user, such as prohibited characters (e.g. ```any([symbol in word for symbol in ['*', '?']])```, prohibited strings (e.g. ```any([_str for _str in ['#kanji', '#sentence']])```).
  * Excluding 'already learned' words defined in a different list.
  * Showing the metadata associated with each word in the word list, such as:
    * where it came from (manual add or imported from browser history)
    * timestamp when added
    * timestamp in browser history (browser history imported word only)
    * number of hits (browser history imported word only)
    * first timestamp ~ last timestamp spanned (browser history imported word only, when there are multiple hits only)
* Right now we don't have any way to initiate a parsing task from the GUI.
  * There needs to be a "Start Parsing" button in the GUI as well as a progress bar to show the user how many words have been parsed so far.
  * There needs to be a flow for deciding how to handle failed parsing cases, and also for extracting information from the failed cases that can help us update our unit tests.
  * There needs to be logic for handling search result 'exact match collisions'. For example, if we search for "https://jisho.org/search/真", it will yield search both "真 (しん)" and "真 (まこと)". We need to allow the user to define which result to prioritize, such as results that have the "common word" tag, "jlpt n?" tag, "wanikani level ??" tag, or a combination of these. Furthermore, if no defined criteria applies to the colliding entries, we need a fallback rule for selecting which entry to use (e.g. picking the entry that came first), and we also need a way to log cases that required a fallback so that the user can be aware of which words may require more specific criteria.
  * There needs to be logic for handling search result 'non-exact match collisions'. For example, if we search for "https://jisho.org/search/真", there will be a lot of results, but none of them are an exact match for the `writing` field, which is the primary field used for matching. However, there are multiple entries that are matching for the `reading` field, which is the secondary field used for matching. In such cases, we need to allow the user to define which result to prioritize, just like for 'exact match collisions', as well as a fallback rule.
  * There needs to be logic for handling search results that have 'no matches'. This could either be search results that didn't yield any dictionary entry matches with the primary `writing` field nor with the secondary `reading` field, or it could be search results that didn't yield any dictionary entries at all. We need to be able to distinguish between these two cases and inform the user which words in their word list didn't yield any matches.
  * There needs to be a way for the user to view the data that parsed for each word in their word list.
  * There needs to be a way for the user to sort their word list based on user-defined criteria, including criteria that references field that are only populated after being parsed from jisho/kotobank/koohii. For example, the user may want to order their words by jlpt level or wanikani level before importing them into their anki deck. Furthermore, the user may also want to simply position the words in their list with the "common word" tag before the words that don't have the "common word" tag.