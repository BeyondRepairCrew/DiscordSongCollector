import discord
import glob
import os
import urllib.request as urllib2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from time import sleep, time
from bs4 import BeautifulSoup
from pathlib import Path
import validators
import asyncio
from peewee import *
import responses
from random import randint
import re
import configparser
#import postgresql
import psycopg2
from pytube import YouTube
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client import tools
from pytube import YouTube
import requests 
import httplib2
import sys

CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN = str(open("../data.txt", "r").read())

YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

config = configparser.ConfigParser()
config.read("config.ini")

client = discord.Client()
stream_requests_channel = "stream-requests"

semaphore = asyncio.Semaphore()

database_proxy = DatabaseProxy()
db = SqliteDatabase('requesters.db')

class Requester(Model):
    discord_id = IntegerField()
    name = CharField()
    requests_count = IntegerField()
    class Meta:
        database = database_proxy


def init_db():
    #db.connect()
    database_proxy.initialize(db)

    db.create_tables([Requester])

def add_to_soundcloud_playlist(url):
    chrome_options = Options()
    chrome_options.add_argument(
        r'--user-data-dir=/home/pi/.config/chromium'
    )
    driver = webdriver.Chrome(chrome_options=chrome_options)
    
    driver.get(url)
    
    sleep(5)
    menu = driver.find_element(By.CSS_SELECTOR,'#content > div > div.l-listen-wrapper > div.l-about-main > div > div:nth-child(1) > div > div > div.listenEngagement__footer.sc-py-1x.sc-px-2x > div > div:nth-child(1) > button.sc-button-more.sc-button-secondary.sc-button.sc-button-medium.sc-button-responsive'
    )
    menu.send_keys("\n")
    sleep(6)
    driver.find_element(By.XPATH,
                        '//button[text()="Zu Playlist hinzufügen"]').click()
    sleep(7)
    list_item_a_tag = driver.find_element(
        By.XPATH, '''//a[@href="/luce-raspe/sets/root-dnbs-stream-requests"]/..''')
    song_already_added = False 
    try:
        list_item_a_tag.find_element_by_xpath('.//button[text()="Hinzugefügt"]')
        song_already_added = True
    except:
        print('Song is already added')

    if not song_already_added:
        try:
            list_item_a_tag.find_element_by_xpath(
                './/button[text()="Zu Playlist hinzufügen"]').click()
            driver.quit()
            return 'ADD_SUCCESS'
        except Exception as e:
            raise(e)
            driver.quit()
            return 'Sorry mate, something went wrong. Tell Pyro420 and he will try to find out what happened.'
    else:
        driver.quit()
        return 'Sorry mate, the song is already in the playlist'

def copy_local_db_to_postgres():
    print("Backing up requests database")
    global config
    try:
        req_dict = {}
        db = SqliteDatabase('requesters.db')
        database_proxy.initialize(db)
        all_requesters =  Requester.select().order_by(Requester.requests_count.desc()).limit(100)
        for requester in all_requesters:
            req_dict[requester.discord_id] = {
                "name": requester.name,
                "requests_count": requester.requests_count
            }
        db.close()
        db_pg = PostgresqlDatabase(config["DATABASE_STUFF"]["db_name"], 
            user=config["DATABASE_STUFF"]["user"], 
            password=config["DATABASE_STUFF"]["pw"],
            host=config["DATABASE_STUFF"]["host"], 
            port=int(config["DATABASE_STUFF"]["port"])
        )
        database_proxy.initialize(db_pg)
        for r_id in req_dict:
        #requester = Requester.select().where(Requester.discord_id==r_id)
            try: 
                requester = Requester.get(Requester.discord_id==r_id)
            except DoesNotExist:
                requester = None
            if not requester:
                #print(req_dict[r_id]["name"], " doesnt exist and will be created")
                requester = Requester(name=req_dict[r_id]["name"], discord_id=r_id, requests_count=req_dict[r_id]["requests_count"])
                print(requester.save())
            else:
                #print(req_dict[r_id]["name"], "exists and only the values will be changed")
                requester.name=req_dict[r_id]["name"]
                requester.requests_count = req_dict[r_id]["requests_count"]
                requester.save()
    except Exception as e:
        print("Backing up requests database failed | error message:")
        print(e)

def increment_requests_counter_for_discord_id(discord_id, user_name):
    db = SqliteDatabase('requesters.db')
    database_proxy.initialize(db)
    requester = None
    try:
        requester = Requester.get(Requester.discord_id==discord_id)
        requester.name = user_name #this is in order to keep the username updated
        requester.requests_count+=1
        requester.save()
        print("Incremented count of ",requester.name," to ", str(requester.requests_count))
    except:
        requester = Requester(name=user_name, discord_id=discord_id, requests_count=1)
        requester.save()
        print("New requester (", user_name,") added")
    db.close()
    return requester.requests_count

def get_requests_count_for_discord_id(discord_id):
    db = SqliteDatabase('requesters.db')
    database_proxy.initialize(db)
    try:
        requester = Requester.get(Requester.discord_id==discord_id)
        return int(requester.requests_count)
    except:
        return 0

def get_top_requester(count):
    db = SqliteDatabase('requesters.db')
    database_proxy.initialize(db)
    return Requester.select().order_by(Requester.requests_count.desc()).limit(count)

def get_individual_response(id):
    if id in responses.individual_responses:
        length = len(responses.individual_responses[id]["responses"])-1
        return responses.individual_responses[id]["responses"][randint(0,length)]
    return None

def get_random_mafa_response():
    bitten = randint(1,5) == 1 
    length = len(responses.mafa)-1
    mafa_quote = responses.mafa[randint(0,length)]
    return mafa_quote, bitten 

@client.event
async def on_ready():
    #dont know what to do with this funtion yet
    pass
       
def get_hybrid_track_data(url):
    result = {
        "type": "",
        "title": "",
        "link_specific_data": {}
    }
    try: 
        req = requests.get(url)
        soup = BeautifulSoup(req.text, features="lxml")
        if "soundcloud.com" in req.url:
            result["type"] = "soundcloud"
            result["title"] = str(soup.title.string).replace("Stream ","",1).replace(" | Listen online for free on SoundCloud","",1)
            result["link_specific_data"]["is_soundcloud_playlist"] = "/sets/" in req.url
            return result
        elif "youtube.com" in req.url:
            result["type"] = "youtube"
            result["link_specific_data"]["is_private"] = '{"simpleText":"Privates Video"}' in req.text
            result["title"] = str(soup.title.string).replace("- YouTube", "",1).strip()
            result["link_specific_data"]["is_youtube_playlist"] = "/playlist?" in req.url
            result["link_specific_data"]["is_youtube_channel"] = "/channel/" in req.url
            result["link_specific_data"]["url"] = req.url
            
            return result
    except Exception as e:
        print(e)
        result["type"] = "error"
        return result 

def add_video_to_playlist(youtube,videoID,playlistID):
    print("[ADD_VIDEO_TO_PLAYLIST]", videoID)
    add_video_request=youtube.playlistItems().insert(
        part="snippet",
        body={
            'snippet': {
            'playlistId': playlistID, 
              'resourceId': {
                      'kind': 'youtube#video',
                  'videoId': videoID
                }
            }
        }).execute()
    
def download_with_scdl(link):
    path = "mp3"
    Path(path).mkdir(parents=True, exist_ok=True)
    stream = os.popen('scdl -l ' + link + ' --path ' + path)
    output = stream.read()
    print(output)

def get_latest_file():
    try:
        list_of_files = glob.glob('mp3/*')
        latest_file = max(list_of_files, key=os.path.getctime)
    except ValueError:
        latest_file = "error"
    return latest_file

def remove_download_flag_from_message(message):
    command = " -download"
    #for i in range(len(command)):
    #    message = message.rstrip(message[-1])
    message = message.split(" ")[0].strip()
    return message

def get_stats_scoreboard(number_of_requesters):
    response = responses.stats_all % number_of_requesters
    place = 1
    for requester in get_top_requester(number_of_requesters):
        response+="\n"+str(place)+". "+requester.name+" with a request count of: "+str(requester.requests_count)
        place+=1
    return response

def get_authenticated_service():
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE, scope=YOUTUBE_SCOPE,
    message="MISSING_CLIENT_SECRETS_MESSAGE")

    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = tools.run_flow(flow, storage)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()))

def download_video(video_url):    
    yt = YouTube(video_url)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path="mp3")
    base, ext = os.path.splitext(out_file)
    new_file = base + ".mp3"
    os.rename(out_file, new_file)

@client.event
async def on_message(message):
    global semaphore
    await semaphore.acquire()
    if message.author == client.user:
        semaphore.release()
        return
    timestamp1 = time()

    if re.search("inter[a-z]*lu+de",str(message.content).strip().lower()):
        await message.channel.send(responses.interlude)

    if message.content.strip() == "!petcat":
        mafa_quote, bitten = get_random_mafa_response()
        response = "Mafa the cat says: "+ mafa_quote 
        await message.channel.send(response)
        if bitten:
            await message.reply("Ouchies, looks like you got bitten by the OG Mafa!", mention_author=True)
    if message.content.strip() == "!stats":
        await message.reply(responses.stats_me, mention_author=True)
        count = get_requests_count_for_discord_id(int(message.author.id))
        if count == 0:
            await message.reply("Hmm i dont seem to have any records of you. Increase your stats by requesting new tracks!",mention_author=True)
        elif count==1:
            await message.reply(responses.stats_me_one, mention_author=True)
        else:
            response = responses.stats_me_more_than_one % count
            await message.reply(response, mention_author = True)
    if message.content.strip()== "!statsall":
        await message.channel.send(get_stats_scoreboard(3)) 


    if str(message.channel).strip() == stream_requests_channel:
        if message.content.strip() == "!help":
            await message.channel.send(responses.help)
            semaphore.release()
            return

        download_requested = message.content.strip().endswith(" -download")
        download_only = message.content.strip().endswith(" -downloadonly")
        if download_only:
            download_requested = True
        link = message.content.strip()
        if download_requested:
            link = remove_download_flag_from_message(link) 
        #link = link.split("?")[0]
        if validators.url(link):
            individual_response = get_individual_response(int(message.author.id))
            if individual_response:
                await message.channel.send(individual_response)
            
            track_data = get_hybrid_track_data(link)

            if track_data["type"]=="error":
                await message.channel.send("Something about this link is weird :thinking: check the url and try again :mechanical_arm:")
                semaphore.release()
                return

            track_title = track_data["title"]
            is_soundcloud_link = track_data["type"]=="soundcloud"
            #track_title, is_soundcloud_link, is_playlist = get_track_data(link)
            if track_title==r"SoundCloud - Hear the world’s sounds":
                await message.channel.send("This track doesnt exist")
                semaphore.release()
                return
            if is_soundcloud_link:
                is_playlist = track_data["link_specific_data"]["is_soundcloud_playlist"]               
                if is_playlist:
                    await message.channel.send("Sorry, but adding a playlist to a playlist doesnt really make much sense, does it?")
                    semaphore.release()
                    return
                if not download_only:
                    await message.channel.send("Now adding "+str(track_title))
                    timestamp1 = time()
                    try:
                        result = add_to_soundcloud_playlist(link)
                    except Exception as e:
                        print("[EXCEPTION] occured while downloading",link, "| stacktrace:")
                        print(e)
                        await message.channel.send('Sorry mate, something went wrong. Tell Pyro420 and he will try to find out what happened.')
                        semaphore.release()
                        return
                    timestamp2 = time()
                    if result == "ADD_SUCCESS":
                        response = "Yes mate, "
                        response += str(track_title)
                        response += " has been added to the playlist "
                        response += "(This took %.2f seconds)" % (timestamp2-timestamp1)
                        increment_requests_counter_for_discord_id(int(message.author.id), str(message.author.name))
                        copy_local_db_to_postgres()
                        await message.channel.send(response)
                    else:
                        await message.channel.send(result)
                if download_requested:
                    if download_only:
                        response = "Downloading "+track_title
                        await message.channel.send(response)
                    download_with_scdl(link)
                    file_name = get_latest_file()
                    if file_name=="error":
                        response = "Something went wrong while downloading "
                        response += track_title
                        response += " ... please make sure that its a valid url ok? :)"
                        await message.channel.send(response)
                    try:
                        if not file_name=="error":
                            await message.channel.send(file=discord.File(file_name, os.path.basename(file_name)))
                    except Exception:
                        await message.channel.send("Oof, that file is too heavy for discord, maximal file size is 8mb")    
                    if not file_name=="error":
                        os.remove(file_name)
                semaphore.release()
                return
            #handle youtube stuff
            link = message.content
            if link.endswith(" -download") or link.endswith(" -downloadonly"):
                link = link.split(" ")[0]
            print(track_data)
            #title, is_youtube_link, is_youtube_playlist, url, is_youtube_channel = get_yt_track_data(link)
            title = track_data["title"]
            is_youtube_link = track_data["type"]=="youtube"
            is_youtube_playlist = track_data["link_specific_data"]["is_youtube_playlist"]
            url = track_data["link_specific_data"]["url"]
            is_private = track_data["link_specific_data"]["is_private"]
            is_youtube_channel = track_data["link_specific_data"]["is_youtube_channel"] 
            if is_youtube_playlist:
                await message.channel.send("Umm this is a playlist. Don't try to add playlists to playlists. Where would we be if playlists could be added to playlists? Would that mean a playlist could contain itself? Why would you do that? Are you trying to kill us all by wrecking the space-time-continuum? Don't do that please, at least not here.")
                semaphore.release()
                return
            if is_youtube_channel:
                await message.channel.send("Hm how exactly am i supposed to add a channel to a playlist?")
                await message.channel.send("https://tenor.com/view/wtf-what-do-you-mean-obama-huh-what-gif-12344531")
                semaphore.release()
                return
            if is_private:
                await message.channel.send("I'm pretty sure this video is private. Therefore i couldn't add it to the playlist, even if i wanted. And i don't lmao.")
                semaphore.release()
                return
            if is_youtube_link:
                if not download_only:
                    await message.channel.send("Now adding "+str(title))
                    try:
                        video_id = str(url).split("&")[0].split("?v=")[1]
                        youtube = get_authenticated_service()
                        add_video_to_playlist(youtube,video_id,"PLiKkZD8QkOII-z_Jf_FS3rXJ0wZF5uWM1")
                        timestamp2 = time()
                        response = "Yes mate, "
                        response += str(title)
                        response += " has been added to the playlist "
                        response += "(This took %.2f seconds)" % (timestamp2-timestamp1)
                        increment_requests_counter_for_discord_id(int(message.author.id), str(message.author.name))
                        copy_local_db_to_postgres()
                        await message.channel.send(response)
                    except Exception as e:
                        print("[EXCEPTION] occured adding youtube link to playlist",link, "| stacktrace:")
                        print(e)
                        await message.channel.send('Sorry mate, something went wrong. Tell Pyro420 and he will try to find out what happened.')
                if download_requested:
                    response = "Downloading " +str(title) + ", please give me a sec, this can sometimes take a while"
                    await message.channel.send(response)
                    download_video(url)
                    file_name = get_latest_file()
                    if file_name=="error":
                        response = "Something went wrong while downloading "
                        response += track_title
                        response += " ... please make sure that its a valid url ok? :)"
                        await message.channel.send(response)
                    try:
                        if not file_name=="error":
                            await message.channel.send(file=discord.File(file_name, os.path.basename(file_name)))
                    except Exception:
                        await message.channel.send("Oof, that file is too heavy for discord, maximal file size is 8mb")    
                    if not file_name=="error":
                        os.remove(file_name)
                  
            else:
                await message.channel.send("This doesnt seem to be leading me to soundcloud or youtube... hm but if you want Pyro420 to add another functionality, hit him up!")
        else:
            #await message.channel.send("Not a url "+link)
            pass
    semaphore.release()
        
if __name__ == '__main__':
    init_db()
    copy_local_db_to_postgres()
    while(True):
        try:
            client.run(TOKEN)
        except Exception as e:
            print(e)
            client = discord.Client()
            sleep(5)