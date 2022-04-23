# Fansly Downloader

This tool can be used for retrieving content from subscribed accounts on [fansly.com](https://fansly.com).\
However I don't advise you to use it!

## Instructions

Here are some instructions on how you can use this project.

### Claim the authorization token for the API
When you log in, the local storage for the site in the browser will contain a key called session_active_session.
You have to copy the token value of this key and put it in the config.json file.

### Install requirements
I suggest everybody to create a virtualenv for any Python project, including this one.
However, in this case the only extra requirement is the requests package, which is usually included in the global Pyhton environment, so you might just run main.py.

### Enjoy
When you run main.py and the token is correct, the content is soon be downloaded.

## Quich fetch
In the config.json file, there is a quich_fetch variable. When enabled, the fetching process will stop when it reaches a file that is already been downloaded. 

When you first download content from an author, you might want this to be disabled.
Sometimes there are collisions in the uploaded content, so when going deeper, there is a minor chance that at some point the downloading process consider itself completed, although not every piece of media is fetched.
