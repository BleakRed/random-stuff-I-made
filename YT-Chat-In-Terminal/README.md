# This is a Live Youtube Stream Chat for the Terminal

REQUIRMENTS:
- python
  - google-auth 
  - google-auth-oauthlib 
  - google-auth-httplib2 
  - google-api-python-client
  - pickle
  - os 
  - time 
- Google OAuth2 credits json file
  - You would have to add your gmail to the test users
  - Enable Youtube Api V3

Place your credentials file on the same folder as the python script and rename it to "credentials.json"

Youtube Id is the "https://www.youtube.com/watch?v=abcdEFGHijk"
the charectors in the 'abcdEFGijk' for this example

token.json gets automaticly created after login



I wanted to create this after finding streamlink to watch live stream and videos from youtube and I wanted to add the ability to read and chat from the terminal.
At the moment it refreshes every 5 sec but you can change it how ever you want


Things to do:
- make it so that I can just use the @userid/live to get into chat and stream. (Don't know if this will work or not)
