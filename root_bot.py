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

TOKEN = str(open("../data.txt", "r").read())

client = discord.Client()
stream_requests_channel = "stream-requests"


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
    sleep(3)
    list_item_div = driver.find_element(
        By.XPATH, '''//a[@title="Root DNB's stream requests"]/..''')
    song_already_added = False
    try:
        list_item_div.find_element_by_xpath('.//button[text()="Hinzugefügt"]')
        song_already_added = True
    except:
        print('Song is already added')

    if not song_already_added:
        try:
            list_item_div.find_element_by_xpath(
                './/button[text()="Zu Playlist hinzufügen"]').click()
            driver.quit()
            return 'ADD_SUCCESS'
        except:
            driver.quit()
            return 'Sorry mate, something went wrong. Tell Pyro420 and he will try to find out what happened.'
    else:
        driver.quit()
        return 'Sorry mate, the song is already in the playlist'


@client.event
async def on_ready():
    #dont know what to do with this funtion yet
    pass

def get_track_data(url):
    req = urllib2.urlopen(url)
    soup = BeautifulSoup(req,features="lxml")
    title = str(soup.title.string).replace("Stream ","",1).replace(" | Listen online for free on SoundCloud","",1)
    is_soundcloud_link= "soundcloud.com" in req.geturl()
    is_soundcloud_playlist= "/sets/" in req.geturl()
    return title,is_soundcloud_link, is_soundcloud_playlist

def download_with_scdl(link):
    path = "mp3"
    Path(path).mkdir(parents=True, exist_ok=True)
    stream = os.popen('scdl -l ' + link + ' --path ' + path)
    output = stream.read()
    print(output)

def get_latest_file():
    list_of_files = glob.glob('mp3/*')
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file

def remove_download_flag_from_message(message):
    command = " -download"
    for i in range(len(command)):
        message = message.rstrip(message[-1])
    return message

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if str(message.channel).strip() == stream_requests_channel:
        try:
            download_requested = message.content.strip().endswith(" -download")
            link = message.content.strip()
            if download_requested:
                print("[",message.content,"] ends with download")
                link = remove_download_flag_from_message(link) 
                print("stripped url:",link)
                print("is url: ",validators.url(link))
            if validators.url(link):
                track_title, is_soundcloud_link, is_playlist = get_track_data(link)
                if is_soundcloud_link:
                    if is_playlist:
                        await message.channel.send("Sorry, but adding a playlist to a playlist doesnt really make much sense, does it?")
                        return
                    await message.channel.send("Now adding "+str(track_title))
                    timestamp1 = time()
                    result = add_to_soundcloud_playlist(link)
                    timestamp2 = time()
                    if result == "ADD_SUCCESS":
                        response = "Yes mate, "
                        response += str(track_title)
                        response += " has been added to the playlist "
                        response += "(This took %.2f seconds)" % (timestamp2-timestamp1)
                        await message.channel.send(response)
                    if download_requested:
                        download_with_scdl(link)
                        file_name = get_latest_file()
                        await message.channel.send(file=discord.File(file_name, os.path.basename(file_name)))
                        os.remove(file_name)
                    else:
                        await message.channel.send(result)
                else:
                    await message.channel.send("This doesnt seem to be leading me to soundcloud... hm but if you want Pyro420 to add another functionality, hit him up!")
            else:
                #await message.channel.send("Not a url "+link)
                pass
        except Exception as e :
            print(e)
            pass

if __name__ == '__main__':
    client.run(TOKEN)