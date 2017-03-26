import aiohttp, asyncio, argparse, os
from tkinter import *

def get_usernames(inputfile):
    #Gets usernames to check from a file
    try:
        with open(inputfile, "r") as f:
            usernames = f.read().split("\n")
            return usernames
    except:
        sys.exit(str(inputfile) + ' does not exists')

async def download_file(username, url, session, sem, loop=None):
    #Downloads and saves photos/videos
    async with sem:
        async with session.get(url) as resp:
            out = await resp.read()
            filename = url.split('/')[-1]
            path = username + '/' + filename

            if not os.path.exists(username):
                os.makedirs(username)

            with open(path, 'wb') as f:
                f.write(out)

async def getJSON(url, session):
    #Gets json response which contains photo/video urls
    async with session.get(url) as resp:
        data = await resp.json()
        return data

async def login(username, password, session):
    #Logs into Instagram
    loginurl = 'https://www.instagram.com/accounts/login/ajax/'
    url = 'https://www.instagram.com/'

    async with session.get(url) as response:
        csrftoken = await response.text()

    csrftoken = csrftoken.split('csrf_token": "')[1].split('"')[0]

    async with session.post(
            loginurl,
                headers={
                    'x-csrftoken': csrftoken, 'x-instagram-ajax':'1',
                    'x-requested-with': 'XMLHttpRequest',
                    'Origin': url, 'Referer': url
                    },
                data={
                    'username':username, 'password':password
                }
            ) as response:

            text = await response.json()
            if 'authenticated' in text:
                pass
            else:
                sys.exit('Login Failed')

async def start(usernames, igname, igpass, conns=50, loop=None):
    #Puts each url in a list for each username
    async with aiohttp.ClientSession(loop=loop) as session:
        if igname != None and igpass != None:
            await login(igname, igpass, session)
        else:
            print('Username and/or password not entered, will not be able to access private profiles.')
        for username in usernames:
            sem = asyncio.BoundedSemaphore(conns)
            url = 'http://instagram.com/' + username + '/media/?max_id='
            urls = []
            max_id = ''
            moreDataToFetch = True
            while(moreDataToFetch):
                nextUrl = url + max_id
                jsonData = await getJSON(nextUrl, session)
                moreDataToFetch = jsonData['more_available']
                for item in jsonData['items']:
                    imgUrl = None
                    max_id = item['id']
                    if item['type'] == 'image':
                        imgUrl = item['images']['standard_resolution']['url']
                    elif item['type'] == 'video':
                        imgUrl = item['videos']['standard_resolution']['url']
                    urls.append(imgUrl)

            tasks = [download_file(username, url, session, sem, loop=loop) for url in urls]
            await asyncio.gather(*tasks)

def main():
    #Starts the loop
    usernames = get_usernames(file_entry.get())
    igname = username_entry.get()
    igpass = password_entry.get()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start(usernames, igname, igpass))
    finally:
        loop.close()

if __name__ == "__main__":
    master = Tk()

    username_label = Label(master, text='Username', relief='sunken', width=15)
    password_label = Label(master, text='Password', relief='sunken', width=15)
    file_label = Label(master, text='File to check', relief='sunken', width=15)

    username_entry = Entry(master)
    password_entry = Entry(master)
    file_entry = Entry(master)

    start_button = Button(master, text="Start", command=lambda: main(), width=15)

    username_label.grid(row=0,column=0)
    password_label.grid(row=1,column=0)
    file_label.grid(row=2,column=0)

    username_entry.grid(row=0,column=1)
    password_entry.grid(row=1,column=1)
    file_entry.grid(row=2,column=1)

    start_button.grid(row=3, column=0)

    mainloop()