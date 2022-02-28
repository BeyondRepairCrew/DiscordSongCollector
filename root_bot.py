from asyncore import write
import discord
import validators
from validators import ValidationFailure
from selenium import webdriver
from selenium.webdriver.common.by import By

from selenium.webdriver.chrome.options import Options
from time import sleep

#TODO implement buffered downloading
#TODO add message which track was added
#TODO check url if its redirecting to soundcloud (maybe by using requests package?)
#TODO add more exception handling and retries if adding fails

#TODO add youtube playlist adding?

TOKEN = "[BOT_TOKEN_SECRET]"

client = discord.Client()
stream_requests_channel = "stream-requests"


def add_to_soundcloud_playlist(url):
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument(
        r'--user-data-dir=C:\Users\Lenovo\AppData\Local\Google\Chrome\User Data'
    )
    chrome_options.add_experimental_option("excludeSwitches",
                                           ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(chrome_options=chrome_options,
                              executable_path="C:\\selenium\\chromedriver.exe")
    driver.execute_cdp_cmd(
        'Network.setUserAgentOverride', {
            "userAgent":
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'
        })
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    driver.get(url)
    driver.maximize_window()

    sleep(1)
    menu = driver.find_element_by_xpath(
        '//*[@id="content"]/div/div[3]/div[1]/div/div[1]/div/div/div[2]/div/div[1]/button[5]'
    ).click()
    sleep(1)
    driver.find_element(By.XPATH,
                        '//button[text()="Zu Playlist hinzufügen"]').click()
    sleep(1)
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
            return 'Yes mate, song has been added to the playlist'
        except:
            driver.quit()
            return 'Sorry mate, something went wrong. Tell Pyro420 and he will try to find out what happened.'
    else:
        driver.quit()
        return 'Sorry mate, the song is already in the playlist'


@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == GUILD:
            break

    print(f'{client.user} is connected to the following guild:\n'
          f'{guild.name}(id: {guild.id})\n')

    members = '\n - '.join([member.name for member in guild.members])
    print(f'Guild Members:\n - {members}')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if str(message.channel).strip() == stream_requests_channel:
        try:
            if validators.url(message.content):
                await message.channel.send("Yep this is a url")
                result = add_to_soundcloud_playlist(message.content)

                await message.channel.send(result)

            else:
                await message.channel.send("Not a url")
        except ValidationFailure:
            pass


if __name__ == '__main__':
    client.run(TOKEN)