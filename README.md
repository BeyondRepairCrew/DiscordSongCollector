# Discord Song Collector
Dont know if anyone is actually going to read this, but the purpose of this bot is to check every message in the stream-requests channel on discord to a soundcloud playlist. Well if the posted link is a soundcloud link of course. 
To run this bot you will need
- python, cuz its a python bot duh
- discord-api wrapper installed (use 'pip install -U discord.py')
- to create a bot token yourself over at [discords dev portal](https://discord.com/developers/applications) , sorry not planning on sharing mine :D
- chrome
- proper Selenium driver installed


Yeah i know that you think... "why tf do i need selenium". Thing is, soundcloud shut down their API quite a few years ago. If i could have used their api: EZPZ lemon squeezy. 


But no.
I had to find a way to somehow overcome the nonexistence of a usable API. So i built a solution using selenium. Problem is: soundcloud uses some good bot protection when it comes to the login-process. I just couldnt get my automated login to work, BUT i could get it to work when i used my cached usersession. This way i dont have to login everytime i want to add a track to my playlist. 

Pain in the ass, but it works. For me, at least. You would have to change the xpath's to one of your own playlists, as you cannot add anything to a playlist belonging to someone else.

Hit me up if you have any questions.
